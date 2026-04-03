from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from rl.state import StatePreprocessor

from .auth import require_api_token
from .config import get_settings
from .rate_limit import rate_limit_dependency
from .schemas import FeedbackRequest, FeedbackResponse, PersonalityProfile, StatusResponse, TrainingRunRequest, TrainingRunResponse, ChatRequest
from .services.model_service import AdaptiveInferenceService
from .services.profile_adapter import infer_profile_from_message, update_profile_from_feedback
from .services.repository import SupabaseRepository
from .services.retrieval_service import RetrievalService
from .services.reward_service import feedback_reward
from .services.training_service import OfflineRLHFService

logger = logging.getLogger(__name__)

settings = get_settings()
repository = SupabaseRepository(settings)
model_service = AdaptiveInferenceService(settings)
retrieval_service = RetrievalService(repository)
training_service = OfflineRLHFService(repository, model_service, settings.adapter_root)
embedding_preprocessor = StatePreprocessor()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AuthDep = Annotated[str, Depends(require_api_token)]
RateDep = Annotated[None, Depends(rate_limit_dependency)]


@app.get("/")
async def root():
    return {"message": "HELIX V1 API is online.", "docs": "/docs"}


@app.get("/api/status", response_model=StatusResponse)
async def status(_: AuthDep, __: RateDep) -> StatusResponse:
    return StatusResponse(status="online", model_version=model_service.active_version, supabase_connected=repository.connected)


@app.get("/api/users/{user_id}/profile", response_model=PersonalityProfile)
async def get_profile(user_id: str, _: AuthDep, __: RateDep) -> PersonalityProfile:
    profile = repository.get_user_profile(user_id)
    return repository.upsert_user_profile(profile)


@app.put("/api/users/{user_id}/profile", response_model=PersonalityProfile)
async def update_profile(user_id: str, payload: PersonalityProfile, _: AuthDep, __: RateDep) -> PersonalityProfile:
    updated = payload.model_copy(update={"user_id": user_id})
    return repository.upsert_user_profile(updated)


@app.get("/api/users/{user_id}/history")
async def get_history(user_id: str, _: AuthDep, __: RateDep):
    return {"items": [record.model_dump() for record in repository.list_recent_interactions(user_id)]}


@app.post("/api/chat")
async def chat(request: ChatRequest, _: AuthDep, __: RateDep):
    # Always use server-side profile — no manual overrides from frontend
    profile = repository.get_user_profile(request.user_id)

    # Auto-infer profile adjustments from the current message
    profile = infer_profile_from_message(profile, request.message)
    profile = repository.upsert_user_profile(profile)

    versions = repository.list_model_versions()
    retrieved = retrieval_service.retrieve_successful_examples(request.user_id, request.message)
    response_text, metadata, _ = await model_service.stream_response(
        user_id=request.user_id,
        message=request.message,
        profile=profile,
        history=request.history,
        retrieved_examples=retrieved,
        versions=versions,
        personality=request.personality,
    )
    interaction = repository.create_interaction(request.user_id, request.message, response_text, metadata["model_version"], metadata)
    repository.store_embedding(interaction.id, request.user_id, embedding_preprocessor._hash_embedding(request.message), request.message)

    logger.info(f"[Chat] user={request.user_id} personality={request.personality} backend={metadata['generation_backend']}")

    return {
        "interaction_id": interaction.id,
        "response": response_text,
        "model_version": metadata["model_version"],
        "system_label": "Adapting to your preferences",
        "profile": profile.model_dump(),
        "metadata": metadata,
    }


@app.post("/api/chat/stream")
async def stream_chat(request: ChatRequest, _: AuthDep, __: RateDep):
    # Always use server-side profile — no manual overrides
    profile = repository.get_user_profile(request.user_id)

    # Auto-infer profile adjustments from the current message
    profile = infer_profile_from_message(profile, request.message)
    profile = repository.upsert_user_profile(profile)

    versions = repository.list_model_versions()
    retrieved = retrieval_service.retrieve_successful_examples(request.user_id, request.message)
    response_text, metadata, iterator = await model_service.stream_response(
        user_id=request.user_id,
        message=request.message,
        profile=profile,
        history=request.history,
        retrieved_examples=retrieved,
        versions=versions,
        personality=request.personality,
    )

    async def stream():
        async for item in iterator:
            yield item
        interaction = repository.create_interaction(request.user_id, request.message, response_text, metadata["model_version"], metadata)
        repository.store_embedding(interaction.id, request.user_id, embedding_preprocessor._hash_embedding(request.message), request.message)
        logger.info(f"[StreamChat] user={request.user_id} personality={request.personality} backend={metadata['generation_backend']}")
        yield json.dumps({
            "type": "done",
            "interaction_id": interaction.id,
            "response": response_text,
            "system_label": "Adapting to your preferences",
            "profile": profile.model_dump(),
            "metadata": metadata,
        }) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, _: AuthDep, __: RateDep):
    reward = feedback_reward(request.vote, request.tags)
    repository.add_feedback(request, reward)
    current = repository.get_user_profile(request.user_id)
    updated = update_profile_from_feedback(current, request)
    repository.upsert_user_profile(updated)
    return FeedbackResponse(reward=reward, updated_profile=updated)


@app.post("/api/training/run", response_model=TrainingRunResponse)
async def trigger_training(request: TrainingRunRequest, background_tasks: BackgroundTasks, _: AuthDep, __: RateDep):
    background_tasks.add_task(training_service.run_batch, request.version_label, request.batch_limit)
    return TrainingRunResponse(accepted=True, message="Offline RLHF batch accepted")


@app.get("/api/model/versions")
async def get_versions(_: AuthDep, __: RateDep):
    return {"items": repository.list_model_versions()}


@app.post("/api/users/{user_id}/clear")
async def clear_history(user_id: str, _: AuthDep, __: RateDep):
    repository.clear_history(user_id)
    return {"status": "success"}
