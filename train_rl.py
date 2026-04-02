from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

os.environ.setdefault("TRL_EXPERIMENTAL_SILENCE", "1")

import torch
import torch.nn.functional as F
from peft import LoraConfig
from transformers import AutoTokenizer
from trl.experimental.ppo.modeling_value_head import AutoModelForCausalLMWithValueHead

from memory import MemoryRecord, VectorMemoryStore
from model import ModelConfig, load_model_and_tokenizer
from rl.dataset import build_demo_dataset
from rl.logging_utils import build_writer, configure_logger, log_json_line
from rl.reward import RewardFunction
from rl.state import StatePreprocessor


@dataclass
class TrainingConfig:
    model_name: str = "distilgpt2"
    epochs: int = 1
    max_prompt_length: int = 128
    max_new_tokens: int = 48
    learning_rate: float = 1.0e-5
    clip_epsilon: float = 0.2
    value_coef: float = 0.1
    entropy_coef: float = 0.01
    gamma: float = 0.99
    log_dir: str = "logs"


def get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def build_models(model_name: str, device: str):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["c_attn", "c_proj"],
    )
    policy_model = AutoModelForCausalLMWithValueHead.from_pretrained(model_name, peft_config=lora_config)
    reference_model = AutoModelForCausalLMWithValueHead.from_pretrained(model_name)
    policy_model.to(device)
    reference_model.to(device)
    reference_model.eval()
    return policy_model, reference_model, tokenizer


def build_prompt(sample, state, memory_hits) -> str:
    context_lines = [f"Memory: {record.text}" for record in memory_hits]
    return (
        "You are a conversational assistant fine-tuned with reinforcement learning.\n"
        f"User input: {sample.user_input}\n"
        f"Emotional state: {state.emotional_state_vector}\n"
        f"User profile: {state.user_profile_features}\n"
        f"Conversation history: {state.conversation_history}\n"
        f"Retrieved context: {context_lines}\n"
        "Assistant:"
    )


def safe_generate(model, tokenizer, prompt: str, device: str, max_new_tokens: int) -> Tuple[str, torch.Tensor]:
    try:
        encoded = tokenizer(prompt, return_tensors="pt", truncation=True).to(device)
        generated = model.pretrained_model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            top_p=0.9,
            temperature=0.8,
            pad_token_id=tokenizer.eos_token_id,
        )
        response_tokens = generated[:, encoded["input_ids"].shape[1] :]
        response_text = tokenizer.decode(response_tokens[0], skip_special_tokens=True).strip()
        if not response_text:
            response_text = "I understand. Let me help with that."
        return response_text, generated
    except Exception:
        fallback = "I understand. Let me help with that."
        encoded = tokenizer(prompt + " " + fallback, return_tensors="pt", truncation=True).to(device)
        return fallback, encoded["input_ids"]


def derive_reward_metrics(user_input: str, response_text: str, emotional_state: List[float]) -> Dict[str, float]:
    engagement_score = min(1.0, len(response_text.split()) / 24.0)
    task_success = 1.0 if any(token in response_text.lower() for token in ["plan", "step", "help", "next"]) else 0.3
    sentiment_improvement = 0.4 if emotional_state[2] > 0.5 and any(token in response_text.lower() for token in ["calm", "step", "together"]) else 0.1
    emotional_alignment = 0.8 if emotional_state[2] > 0.5 and "together" in response_text.lower() else 0.4
    return {
        "engagement_score": engagement_score,
        "sentiment_improvement": sentiment_improvement,
        "task_success": task_success,
        "emotional_alignment": emotional_alignment,
    }


def compute_logprob_and_value(model, input_ids: torch.Tensor, prompt_length: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    logits, _, values = model(input_ids=input_ids)
    log_probs = F.log_softmax(logits[:, :-1, :], dim=-1)
    target_tokens = input_ids[:, 1:]
    token_log_probs = log_probs.gather(-1, target_tokens.unsqueeze(-1)).squeeze(-1)
    response_log_probs = token_log_probs[:, prompt_length - 1 :]
    response_values = values[:, prompt_length - 1 : -1]
    return response_log_probs, response_values, logits


def ppo_update(
    policy_model,
    reference_model,
    optimizer,
    full_sequence: torch.Tensor,
    prompt_length: int,
    reward_value: float,
    config: TrainingConfig,
):
    with torch.no_grad():
        old_log_probs, old_values, _ = compute_logprob_and_value(policy_model, full_sequence, prompt_length)
        ref_log_probs, _, _ = compute_logprob_and_value(reference_model, full_sequence, prompt_length)

    new_log_probs, new_values, logits = compute_logprob_and_value(policy_model, full_sequence, prompt_length)
    sequence_reward = torch.full_like(new_values, reward_value)
    advantage = sequence_reward - old_values.detach()

    ratio = torch.exp(new_log_probs - old_log_probs.detach())
    unclipped = ratio * advantage
    clipped = torch.clamp(ratio, 1 - config.clip_epsilon, 1 + config.clip_epsilon) * advantage
    policy_loss = -torch.min(unclipped, clipped).mean()

    value_loss = F.mse_loss(new_values, sequence_reward)
    probs = F.softmax(logits[:, :-1, :], dim=-1)
    entropy = -(probs * F.log_softmax(logits[:, :-1, :], dim=-1)).sum(dim=-1).mean()
    kl_term = (new_log_probs - ref_log_probs.detach()).mean()

    total_loss = policy_loss + config.value_coef * value_loss - config.entropy_coef * entropy + 0.05 * kl_term

    optimizer.zero_grad()
    total_loss.backward()
    optimizer.step()

    return {
        "ppo/loss/policy": float(policy_loss.detach().cpu()),
        "ppo/loss/value": float(value_loss.detach().cpu()),
        "ppo/loss/total": float(total_loss.detach().cpu()),
        "ppo/policy/entropy": float(entropy.detach().cpu()),
        "ppo/policy/kl": float(kl_term.detach().cpu()),
        "ppo/advantage/mean": float(advantage.mean().detach().cpu()),
    }


def run_training(config: TrainingConfig) -> None:
    logger = configure_logger(config.log_dir)
    writer = build_writer(f"{config.log_dir}/tensorboard")
    device = get_device()

    _, _, base_metadata = load_model_and_tokenizer(ModelConfig(model_name=config.model_name))
    logger.info("Base model loaded: %s", base_metadata)

    policy_model, reference_model, tokenizer = build_models(config.model_name, device)
    optimizer = torch.optim.AdamW(policy_model.parameters(), lr=config.learning_rate)

    reward_function = RewardFunction()
    state_preprocessor = StatePreprocessor()
    memory_store = VectorMemoryStore()
    dataset = build_demo_dataset()

    step_index = 0
    for epoch in range(config.epochs):
        for sample in dataset:
            state = state_preprocessor.preprocess(
                user_input=sample.user_input,
                emotional_state_vector=sample.emotional_state_vector,
                conversation_history=sample.history,
                user_profile_features=sample.profile,
            )
            memory_hits = memory_store.search(sample.user_input, top_k=2)
            prompt = build_prompt(sample, state, memory_hits)
            prompt_tokens = tokenizer(prompt, return_tensors="pt", truncation=True).to(device)
            prompt_length = int(prompt_tokens["input_ids"].shape[1])

            response_text, full_sequence = safe_generate(policy_model, tokenizer, prompt, device, config.max_new_tokens)
            if full_sequence.dim() == 1:
                full_sequence = full_sequence.unsqueeze(0)
            full_sequence = full_sequence.to(device)

            reward_metrics = derive_reward_metrics(
                user_input=sample.user_input,
                response_text=response_text,
                emotional_state=state.emotional_state_vector,
            )
            reward = reward_function.compute(response_text=response_text, metrics=reward_metrics)

            logger.info("state=%s", state.to_dict())
            logger.info("action=%s", response_text)
            logger.info("reward=%s", reward.to_dict())
            log_json_line(
                f"{config.log_dir}/debug.jsonl",
                {
                    "epoch": epoch,
                    "step": step_index,
                    "state": state.to_dict(),
                    "action": response_text,
                    "reward": reward.to_dict(),
                },
            )

            try:
                stats = ppo_update(
                    policy_model=policy_model,
                    reference_model=reference_model,
                    optimizer=optimizer,
                    full_sequence=full_sequence,
                    prompt_length=prompt_length,
                    reward_value=reward.total,
                    config=config,
                )
            except Exception as error:
                logger.exception("PPO update failed at step %s: %s", step_index, error)
                stats = {"ppo/loss/total": 0.0, "ppo/error": str(error)}

            writer.add_scalar("reward/total", reward.total, step_index)
            writer.add_scalar("reward/engagement", reward.engagement_score, step_index)
            writer.add_scalar("training/loss_total", float(stats.get("ppo/loss/total", 0.0)), step_index)

            memory_store.add(
                MemoryRecord(
                    text=sample.user_input,
                    emotional_pattern=state.emotional_state_vector,
                    metadata={"response": response_text, "reward": reward.total},
                )
            )
            step_index += 1

    memory_store.save()
    writer.close()


def parse_args() -> TrainingConfig:
    parser = argparse.ArgumentParser(description="Run PPO fine-tuning for a conversational model.")
    parser.add_argument("--model-name", default="distilgpt2")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--log-dir", default="logs")
    args = parser.parse_args()
    return TrainingConfig(
        model_name=args.model_name,
        epochs=args.epochs,
        log_dir=args.log_dir,
    )


if __name__ == "__main__":
    run_training(parse_args())
