from __future__ import annotations

from collections import defaultdict

from .analytics_service import MarketingAnalyticsService
from .repository import LocalMarketingRepository
from .schemas import AnalyticsSummaryResponse, OptimizationSummaryResponse


class MarketingOptimizationService:
    """Transforms local analytics into lightweight optimization guidance."""

    def __init__(
        self,
        repository: LocalMarketingRepository,
        analytics_service: MarketingAnalyticsService,
    ):
        self.repository = repository
        self.analytics_service = analytics_service

    def optimize(self, campaign_id: str | None = None) -> OptimizationSummaryResponse:
        summary = self.analytics_service.summary(campaign_id=campaign_id)
        top_platform = self._top_platform(summary)
        recommended_cta = self._recommended_cta(summary)
        posting_window = self._recommended_posting_window(top_platform)
        prompt_bias = self._prompt_bias(summary)
        updated_variants = self._update_variant_scores(campaign_id)

        return OptimizationSummaryResponse(
            campaign_id=campaign_id,
            top_platform=top_platform,
            recommended_cta_style=recommended_cta,
            recommended_posting_window=posting_window,
            prompt_bias_hints=prompt_bias,
            updated_variant_ids=updated_variants,
            analytics_summary=summary,
        )

    def _top_platform(self, summary: AnalyticsSummaryResponse) -> str:
        if not summary.platform_scores:
            return "linkedin"
        return next(iter(summary.platform_scores))

    def _recommended_cta(self, summary: AnalyticsSummaryResponse) -> str:
        click_rate = summary.metric_averages.get("click_rate", 0)
        conversion_rate = summary.metric_averages.get("conversion_rate", 0)
        reply_rate = summary.metric_averages.get("reply_rate", 0)
        if conversion_rate >= max(click_rate, reply_rate):
            return "direct conversion CTA"
        if reply_rate > click_rate:
            return "conversation-starting CTA"
        return "curiosity-driven CTA"

    def _recommended_posting_window(self, platform: str) -> str:
        windows = {
            "linkedin": "weekday mornings",
            "x": "weekday mornings and early evenings",
            "telegram": "late mornings",
            "discord": "evenings",
            "reddit": "subreddit-specific peak windows",
            "webhook": "whenever downstream automation is ready",
        }
        return windows.get(platform, "weekday mornings")

    def _prompt_bias(self, summary: AnalyticsSummaryResponse) -> list[str]:
        hints = list(summary.memory_hints[:4])
        if summary.metric_averages.get("click_rate", 0) >= 5:
            hints.append("favor hook-first openings with clearer curiosity gaps")
        if summary.metric_averages.get("conversion_rate", 0) >= 3:
            hints.append("use stronger benefit-led CTAs near the end of the post")
        if not hints:
            hints.append("keep messaging clear, concise, and problem-first")
        return hints

    def _update_variant_scores(self, campaign_id: str | None) -> list[str]:
        events = self.repository.list_performance_events(campaign_id=campaign_id)
        score_map: dict[str, list[float]] = defaultdict(list)
        for event in events:
            if event.variant_id:
                score_map[event.variant_id].append(event.metric_value)

        updated_variant_ids: list[str] = []
        for variant_id, values in score_map.items():
            score = round(sum(values) / max(len(values), 1), 2)
            if self.repository.update_variant_score(variant_id, score):
                updated_variant_ids.append(variant_id)
        return updated_variant_ids
