from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from .repository import LocalMarketingRepository
from .schemas import ScheduleCampaignRequest, ScheduleCampaignResponse

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover
    BackgroundScheduler = None


class _FallbackRepeatingTimer:
    """Simple repeating timer using threading — used when apscheduler is unavailable."""

    def __init__(self, interval_seconds: float, target, name: str = "timer"):
        self._interval = interval_seconds
        self._target = target
        self._name = name
        self._timer: threading.Timer | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._schedule_next()
        logger.info("[FallbackTimer:%s] Started (interval=%ss)", self._name, self._interval)

    def _schedule_next(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(self._interval, self._run)
        self._timer.daemon = True
        self._timer.start()

    def _run(self) -> None:
        if not self._running:
            return
        try:
            self._target()
        except Exception as e:
            logger.error("[FallbackTimer:%s] Error in callback: %s", self._name, e)
        self._schedule_next()

    def shutdown(self) -> None:
        self._running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        logger.info("[FallbackTimer:%s] Stopped", self._name)


class MarketingSchedulerService:
    """Promotes approved scheduled jobs into queued state when due."""

    def __init__(self, repository: LocalMarketingRepository):
        self.repository = repository
        self.scheduler = None
        self._fallback_timer: _FallbackRepeatingTimer | None = None

    def start(self) -> None:
        if self.scheduler is not None:
            return

        if BackgroundScheduler is not None:
            try:
                self.scheduler = BackgroundScheduler(timezone="UTC")
                self.scheduler.add_job(
                    self.enqueue_due_jobs, "interval", seconds=20,
                    id="helix_marketing_enqueue_due",
                )
                self.scheduler.start()
                logger.info("[MarketingScheduler] APScheduler started — checking due jobs every 20s")
                return
            except Exception as e:
                logger.warning("[MarketingScheduler] APScheduler failed to start: %s — falling back to timer", e)

        # Fallback: use a simple threading-based timer
        self._fallback_timer = _FallbackRepeatingTimer(
            interval_seconds=20,
            target=self.enqueue_due_jobs,
            name="scheduler",
        )
        self._fallback_timer.start()
        logger.info("[MarketingScheduler] Fallback timer started — checking due jobs every 20s")

    def shutdown(self) -> None:
        if self.scheduler is not None:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
        if self._fallback_timer is not None:
            self._fallback_timer.shutdown()
            self._fallback_timer = None

    def schedule_campaign(self, campaign_id: str, request: ScheduleCampaignRequest) -> ScheduleCampaignResponse:
        jobs = []
        rejected_variant_ids: list[str] = []
        for variant_id in request.variant_ids:
            variant = self.repository.get_variant(variant_id)
            if not variant or variant.campaign_id != campaign_id or variant.approval_status != "approved":
                rejected_variant_ids.append(variant_id)
                continue
            jobs.append(
                self.repository.create_scheduled_job(
                    campaign_id=campaign_id,
                    variant_id=variant_id,
                    platform=variant.platform,
                    run_at=request.run_at,
                    timezone_name=request.timezone,
                    status="pending",
                )
            )
        if jobs:
            self.repository.update_campaign(campaign_id, payload={"status": "scheduled"})  # type: ignore[arg-type]
        return ScheduleCampaignResponse(jobs=jobs, rejected_variant_ids=rejected_variant_ids)

    def enqueue_due_jobs(self) -> int:
        now = datetime.now(timezone.utc)
        count = self.repository.mark_due_jobs_queued(now)
        if count:
            logger.info("[MarketingScheduler] Promoted %s pending jobs → queued (run_at <= %s)", count, now.isoformat())
        return count

