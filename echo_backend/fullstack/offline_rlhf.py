from __future__ import annotations

import argparse
import asyncio
import json

from .config import get_settings
from .services.model_service import AdaptiveInferenceService
from .services.repository import SupabaseRepository
from .services.training_service import OfflineRLHFService


async def main(batch_limit: int, version_label: str) -> None:
    settings = get_settings()
    repository = SupabaseRepository(settings)
    model_service = AdaptiveInferenceService(settings)
    trainer = OfflineRLHFService(repository, model_service, settings.adapter_root)
    result = await trainer.run_batch(version_label=version_label, limit=batch_limit)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run offline RLHF batch training from Supabase feedback.")
    parser.add_argument("--batch-limit", type=int, default=100)
    parser.add_argument("--version-label", default="candidate")
    args = parser.parse_args()
    asyncio.run(main(args.batch_limit, args.version_label))
