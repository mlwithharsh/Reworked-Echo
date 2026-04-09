from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .repository import LocalMarketingRepository


class MarketingSafetyService:
    """Low-latency validation for approval and scheduling decisions."""

    def __init__(self, repository: LocalMarketingRepository):
        self.repository = repository

    def evaluate_variant(self, variant_id: str) -> tuple[bool, list[str]]:
        variant = self.repository.get_variant(variant_id)
        if not variant:
            return False, ["Variant not found"]

        campaign = self.repository.get_campaign(variant.campaign_id)
        if not campaign:
            return False, ["Campaign not found"]

        reasons: list[str] = []
        brand = self.repository.get_brand_profile(campaign.brand_profile_id) if campaign.brand_profile_id else None
        text = (variant.generated_text or "").lower()

        if not text.strip():
            reasons.append("Generated content is empty")

        if brand:
            for phrase in brand.banned_phrases:
                if phrase and phrase.lower() in text:
                    reasons.append(f"Contains banned phrase: {phrase}")

        if self.repository.has_duplicate_variant_content(
            campaign_id=variant.campaign_id,
            platform=variant.platform,
            generated_text=variant.generated_text,
            exclude_variant_id=variant.id,
        ):
            reasons.append("Duplicate content detected for this platform")

        if self.repository.has_recent_scheduled_post(
            platform=variant.platform,
            window_minutes=0.01,
        ):
            reasons.append("Cooldown active for this platform")

        return (len(reasons) == 0), reasons

