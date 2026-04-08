from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..config import Settings
from .models import DDL_STATEMENTS, INDEX_STATEMENTS, utc_now_iso
from .schemas import (
    AnalyticsSummaryResponse,
    BrandProfileResponse,
    CampaignResponse,
    CampaignVariantResponse,
    CreateBrandProfileRequest,
    CreateCampaignRequest,
    DeliveryLogResponse,
    PerformanceEventResponse,
    ScheduledJobResponse,
    UpdateCampaignRequest,
    UpdateBrandProfileRequest,
)

logger = logging.getLogger(__name__)


class LocalMarketingRepository:
    """Local SQLite repository optimized for fast local reads and writes."""

    def __init__(self, settings: Settings):
        db_path = Path(settings.marketing_db_path)
        if not db_path.is_absolute():
            db_path = Path(settings.root_dir) / db_path
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory_uri = "file:helix_marketing_local?mode=memory&cache=shared"
        self._keeper_conn: sqlite3.Connection | None = None
        self._initialize()

    @contextmanager
    def _connect(self):
        target = self._memory_uri if self._keeper_conn is not None else str(self.db_path)
        conn = sqlite3.connect(target, timeout=30, uri=target.startswith("file:"))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL" if self._keeper_conn is None else "PRAGMA journal_mode=MEMORY")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA temp_store=MEMORY")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self) -> None:
        try:
            with self._connect() as conn:
                for statement in DDL_STATEMENTS:
                    conn.execute(statement)
                for statement in INDEX_STATEMENTS:
                    conn.execute(statement)
        except sqlite3.OperationalError as exc:
            logger.warning("Falling back to shared in-memory SQLite for marketing repository: %s", exc)
            self._keeper_conn = sqlite3.connect(self._memory_uri, uri=True, timeout=30)
            self._keeper_conn.row_factory = sqlite3.Row
            self._keeper_conn.execute("PRAGMA journal_mode=MEMORY")
            self._keeper_conn.execute("PRAGMA synchronous=OFF")
            self._keeper_conn.execute("PRAGMA foreign_keys=ON")
            self._keeper_conn.execute("PRAGMA temp_store=MEMORY")
            for statement in DDL_STATEMENTS:
                self._keeper_conn.execute(statement)
            for statement in INDEX_STATEMENTS:
                self._keeper_conn.execute(statement)
            self._keeper_conn.commit()

    @staticmethod
    def _decode_json(raw: str, fallback):
        if not raw:
            return fallback
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return fallback

    def upsert_brand_profile(
        self,
        payload: CreateBrandProfileRequest | UpdateBrandProfileRequest,
        brand_id: str | None = None,
    ) -> BrandProfileResponse:
        now = utc_now_iso()
        record_id = brand_id or str(uuid4())

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM brand_profiles WHERE id = ?",
                (record_id,),
            ).fetchone()

            existing_data = dict(existing) if existing else {}
            base = {
                "id": record_id,
                "brand_name": existing_data.get("brand_name", ""),
                "voice_style": existing_data.get("voice_style", ""),
                "preferred_vocabulary": self._decode_json(existing_data.get("preferred_vocabulary", "[]"), []),
                "banned_phrases": self._decode_json(existing_data.get("banned_phrases", "[]"), []),
                "signature_patterns": self._decode_json(existing_data.get("signature_patterns", "[]"), []),
                "default_cta_style": existing_data.get("default_cta_style", ""),
                "audience_notes": existing_data.get("audience_notes", ""),
                "positioning": existing_data.get("positioning", ""),
                "created_at": existing_data.get("created_at", now),
                "updated_at": now,
            }
            merged = {**base, **payload.model_dump(exclude_none=True)}

            conn.execute(
                """
                INSERT INTO brand_profiles (
                    id, brand_name, voice_style, preferred_vocabulary, banned_phrases,
                    signature_patterns, default_cta_style, audience_notes, positioning,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    brand_name = excluded.brand_name,
                    voice_style = excluded.voice_style,
                    preferred_vocabulary = excluded.preferred_vocabulary,
                    banned_phrases = excluded.banned_phrases,
                    signature_patterns = excluded.signature_patterns,
                    default_cta_style = excluded.default_cta_style,
                    audience_notes = excluded.audience_notes,
                    positioning = excluded.positioning,
                    updated_at = excluded.updated_at
                """,
                (
                    merged["id"],
                    merged["brand_name"],
                    merged["voice_style"],
                    json.dumps(merged["preferred_vocabulary"]),
                    json.dumps(merged["banned_phrases"]),
                    json.dumps(merged["signature_patterns"]),
                    merged["default_cta_style"],
                    merged["audience_notes"],
                    merged["positioning"],
                    merged["created_at"],
                    merged["updated_at"],
                ),
            )

        return self.get_brand_profile(record_id)

    def get_brand_profile(self, brand_id: str) -> BrandProfileResponse | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM brand_profiles WHERE id = ?",
                (brand_id,),
            ).fetchone()
        if not row:
            return None
        return BrandProfileResponse(
            id=row["id"],
            brand_name=row["brand_name"],
            voice_style=row["voice_style"],
            preferred_vocabulary=self._decode_json(row["preferred_vocabulary"], []),
            banned_phrases=self._decode_json(row["banned_phrases"], []),
            signature_patterns=self._decode_json(row["signature_patterns"], []),
            default_cta_style=row["default_cta_style"],
            audience_notes=row["audience_notes"],
            positioning=row["positioning"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_brand_profiles(self) -> list[BrandProfileResponse]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM brand_profiles ORDER BY updated_at DESC"
            ).fetchall()
        return [
            BrandProfileResponse(
                id=row["id"],
                brand_name=row["brand_name"],
                voice_style=row["voice_style"],
                preferred_vocabulary=self._decode_json(row["preferred_vocabulary"], []),
                banned_phrases=self._decode_json(row["banned_phrases"], []),
                signature_patterns=self._decode_json(row["signature_patterns"], []),
                default_cta_style=row["default_cta_style"],
                audience_notes=row["audience_notes"],
                positioning=row["positioning"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def create_campaign(self, payload: CreateCampaignRequest) -> CampaignResponse:
        now = utc_now_iso()
        record_id = str(uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO campaigns (
                    id, name, goal, target_audience, brand_profile_id, brand_voice,
                    offer_summary, strategy_summary, content_mix, posting_frequency,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    payload.name,
                    payload.goal,
                    payload.target_audience,
                    payload.brand_profile_id,
                    payload.brand_voice,
                    payload.offer_summary,
                    payload.strategy_summary,
                    json.dumps(payload.content_mix),
                    payload.posting_frequency,
                    payload.status,
                    now,
                    now,
                ),
            )
        return self.get_campaign(record_id)

    def get_campaign(self, campaign_id: str) -> CampaignResponse | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM campaigns WHERE id = ?",
                (campaign_id,),
            ).fetchone()
        if not row:
            return None
        return CampaignResponse(
            id=row["id"],
            name=row["name"],
            goal=row["goal"],
            target_audience=row["target_audience"],
            brand_profile_id=row["brand_profile_id"],
            brand_voice=row["brand_voice"],
            offer_summary=row["offer_summary"],
            strategy_summary=row["strategy_summary"],
            content_mix=self._decode_json(row["content_mix"], {}),
            posting_frequency=row["posting_frequency"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_campaigns(self, status: str | None = None) -> list[CampaignResponse]:
        query = "SELECT * FROM campaigns"
        params: tuple[str, ...] = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            CampaignResponse(
                id=row["id"],
                name=row["name"],
                goal=row["goal"],
                target_audience=row["target_audience"],
                brand_profile_id=row["brand_profile_id"],
                brand_voice=row["brand_voice"],
                offer_summary=row["offer_summary"],
                strategy_summary=row["strategy_summary"],
                content_mix=self._decode_json(row["content_mix"], {}),
                posting_frequency=row["posting_frequency"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def update_campaign(self, campaign_id: str, payload: UpdateCampaignRequest) -> CampaignResponse | None:
        if isinstance(payload, dict):
            payload = UpdateCampaignRequest(**payload)
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM campaigns WHERE id = ?",
                (campaign_id,),
            ).fetchone()
            if not existing:
                return None
            row = dict(existing)
            updates = payload.model_dump(exclude_none=True)
            merged = {
                "id": row["id"],
                "name": updates.get("name", row["name"]),
                "goal": updates.get("goal", row["goal"]),
                "target_audience": updates.get("target_audience", row["target_audience"]),
                "brand_profile_id": updates.get("brand_profile_id", row["brand_profile_id"]),
                "brand_voice": updates.get("brand_voice", row["brand_voice"]),
                "offer_summary": updates.get("offer_summary", row["offer_summary"]),
                "strategy_summary": updates.get("strategy_summary", row["strategy_summary"]),
                "content_mix": updates.get("content_mix", self._decode_json(row["content_mix"], {})),
                "posting_frequency": updates.get("posting_frequency", row["posting_frequency"]),
                "status": updates.get("status", row["status"]),
                "created_at": row["created_at"],
                "updated_at": utc_now_iso(),
            }
            conn.execute(
                """
                UPDATE campaigns
                SET name = ?, goal = ?, target_audience = ?, brand_profile_id = ?, brand_voice = ?,
                    offer_summary = ?, strategy_summary = ?, content_mix = ?, posting_frequency = ?,
                    status = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    merged["name"],
                    merged["goal"],
                    merged["target_audience"],
                    merged["brand_profile_id"],
                    merged["brand_voice"],
                    merged["offer_summary"],
                    merged["strategy_summary"],
                    json.dumps(merged["content_mix"]),
                    merged["posting_frequency"],
                    merged["status"],
                    merged["updated_at"],
                    campaign_id,
                ),
            )
        return self.get_campaign(campaign_id)

    def create_variant(
        self,
        *,
        campaign_id: str,
        platform: str,
        variant_name: str,
        prompt_snapshot: str,
        generated_text: str,
        cta: str,
        hashtags: list[str],
        score: float,
        experiment_group: str,
        approval_status: str,
    ) -> CampaignVariantResponse:
        record_id = str(uuid4())
        created_at = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO campaign_variants (
                    id, campaign_id, platform, variant_name, prompt_snapshot, generated_text,
                    cta, hashtags, score, experiment_group, approval_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    campaign_id,
                    platform,
                    variant_name,
                    prompt_snapshot,
                    generated_text,
                    cta,
                    json.dumps(hashtags),
                    score,
                    experiment_group,
                    approval_status,
                    created_at,
                ),
            )
        return self.get_variant(record_id)

    def get_variant(self, variant_id: str) -> CampaignVariantResponse | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM campaign_variants WHERE id = ?",
                (variant_id,),
            ).fetchone()
        if not row:
            return None
        return CampaignVariantResponse(
            id=row["id"],
            campaign_id=row["campaign_id"],
            platform=row["platform"],
            variant_name=row["variant_name"],
            prompt_snapshot=row["prompt_snapshot"],
            generated_text=row["generated_text"],
            cta=row["cta"],
            hashtags=self._decode_json(row["hashtags"], []),
            score=row["score"],
            experiment_group=row["experiment_group"],
            approval_status=row["approval_status"],
            created_at=row["created_at"],
        )

    def list_variants(self, campaign_id: str) -> list[CampaignVariantResponse]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM campaign_variants WHERE campaign_id = ? ORDER BY created_at DESC",
                (campaign_id,),
            ).fetchall()
        return [
            CampaignVariantResponse(
                id=row["id"],
                campaign_id=row["campaign_id"],
                platform=row["platform"],
                variant_name=row["variant_name"],
                prompt_snapshot=row["prompt_snapshot"],
                generated_text=row["generated_text"],
                cta=row["cta"],
                hashtags=self._decode_json(row["hashtags"], []),
                score=row["score"],
                experiment_group=row["experiment_group"],
                approval_status=row["approval_status"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def update_variant_score(self, variant_id: str, score: float) -> CampaignVariantResponse | None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE campaign_variants SET score = ? WHERE id = ?",
                (score, variant_id),
            )
        return self.get_variant(variant_id)

    def update_variant_approval(self, variant_id: str, approval_status: str) -> CampaignVariantResponse | None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE campaign_variants SET approval_status = ? WHERE id = ?",
                (approval_status, variant_id),
            )
        return self.get_variant(variant_id)

    def has_duplicate_variant_content(
        self,
        *,
        campaign_id: str,
        platform: str,
        generated_text: str,
        exclude_variant_id: str | None = None,
    ) -> bool:
        query = """
            SELECT 1 FROM campaign_variants
            WHERE campaign_id = ? AND platform = ? AND LOWER(TRIM(generated_text)) = LOWER(TRIM(?))
        """
        params: list[str] = [campaign_id, platform, generated_text]
        if exclude_variant_id:
            query += " AND id != ?"
            params.append(exclude_variant_id)
        query += " LIMIT 1"
        with self._connect() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
        return row is not None

    def create_scheduled_job(
        self,
        *,
        campaign_id: str,
        variant_id: str,
        platform: str,
        run_at: datetime,
        timezone_name: str,
        status: str,
    ) -> ScheduledJobResponse:
        record_id = str(uuid4())
        created_at = utc_now_iso()
        normalized_run_at = run_at.astimezone(timezone.utc).isoformat() if run_at.tzinfo else run_at.replace(tzinfo=timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO scheduled_jobs (
                    id, campaign_id, variant_id, platform, run_at, timezone, status, retry_count, last_error, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, '', ?)
                """,
                (record_id, campaign_id, variant_id, platform, normalized_run_at, timezone_name, status, created_at),
            )
        return self.get_scheduled_job(record_id)

    def get_scheduled_job(self, job_id: str) -> ScheduledJobResponse | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM scheduled_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return ScheduledJobResponse(
            id=row["id"],
            campaign_id=row["campaign_id"],
            variant_id=row["variant_id"],
            platform=row["platform"],
            run_at=row["run_at"],
            timezone=row["timezone"],
            status=row["status"],
            retry_count=row["retry_count"],
            last_error=row["last_error"],
            created_at=row["created_at"],
        )

    def list_scheduled_jobs(self, status: str | None = None) -> list[ScheduledJobResponse]:
        query = "SELECT * FROM scheduled_jobs"
        params: tuple[str, ...] = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY run_at ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            ScheduledJobResponse(
                id=row["id"],
                campaign_id=row["campaign_id"],
                variant_id=row["variant_id"],
                platform=row["platform"],
                run_at=row["run_at"],
                timezone=row["timezone"],
                status=row["status"],
                retry_count=row["retry_count"],
                last_error=row["last_error"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def update_scheduled_job_status(self, job_id: str, status: str, last_error: str = "") -> ScheduledJobResponse | None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE scheduled_jobs SET status = ?, last_error = ? WHERE id = ?",
                (status, last_error, job_id),
            )
        return self.get_scheduled_job(job_id)

    def increment_scheduled_job_retry(self, job_id: str, last_error: str) -> ScheduledJobResponse | None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE scheduled_jobs
                SET retry_count = retry_count + 1, last_error = ?
                WHERE id = ?
                """,
                (last_error, job_id),
            )
        return self.get_scheduled_job(job_id)

    def mark_due_jobs_queued(self, now: datetime) -> int:
        normalized_now = now.astimezone(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE scheduled_jobs
                SET status = 'queued'
                WHERE status = 'pending' AND run_at <= ?
                """,
                (normalized_now,),
            )
            return cursor.rowcount or 0

    def has_recent_scheduled_post(self, *, platform: str, window_minutes: int) -> bool:
        threshold = (datetime.now(timezone.utc)).timestamp() - (window_minutes * 60)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT run_at FROM scheduled_jobs WHERE platform = ? AND status IN ('pending', 'queued', 'running', 'completed') ORDER BY run_at DESC LIMIT 10",
                (platform,),
            ).fetchall()
        for row in rows:
            try:
                run_at = datetime.fromisoformat(row["run_at"].replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if run_at >= threshold:
                return True
        return False

    def create_delivery_log(
        self,
        *,
        job_id: str,
        platform: str,
        request_payload: dict,
        response_payload: dict,
        status: str,
        external_post_id: str,
        execution_mode: str,
    ) -> DeliveryLogResponse:
        record_id = str(uuid4())
        created_at = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO delivery_logs (
                    id, job_id, platform, request_payload, response_payload, status,
                    external_post_id, execution_mode, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    job_id,
                    platform,
                    json.dumps(request_payload),
                    json.dumps(response_payload),
                    status,
                    external_post_id,
                    execution_mode,
                    created_at,
                ),
            )
        return self.get_delivery_log(record_id)

    def get_delivery_log(self, log_id: str) -> DeliveryLogResponse | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM delivery_logs WHERE id = ?", (log_id,)).fetchone()
        if not row:
            return None
        return DeliveryLogResponse(
            id=row["id"],
            job_id=row["job_id"],
            platform=row["platform"],
            request_payload=self._decode_json(row["request_payload"], {}),
            response_payload=self._decode_json(row["response_payload"], {}),
            status=row["status"],
            external_post_id=row["external_post_id"],
            execution_mode=row["execution_mode"],
            created_at=row["created_at"],
        )

    def list_delivery_logs(self, platform: str | None = None) -> list[DeliveryLogResponse]:
        query = "SELECT * FROM delivery_logs"
        params: tuple[str, ...] = ()
        if platform:
            query += " WHERE platform = ?"
            params = (platform,)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            DeliveryLogResponse(
                id=row["id"],
                job_id=row["job_id"],
                platform=row["platform"],
                request_payload=self._decode_json(row["request_payload"], {}),
                response_payload=self._decode_json(row["response_payload"], {}),
                status=row["status"],
                external_post_id=row["external_post_id"],
                execution_mode=row["execution_mode"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def create_performance_event(
        self,
        *,
        campaign_id: str,
        variant_id: str | None,
        platform: str,
        metric_type: str,
        metric_value: float,
        source: str,
        note: str,
    ) -> PerformanceEventResponse:
        record_id = str(uuid4())
        created_at = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO performance_events (
                    id, campaign_id, variant_id, platform, metric_type, metric_value, source, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (record_id, campaign_id, variant_id, platform, metric_type, metric_value, source, note, created_at),
            )
        return self.get_performance_event(record_id)

    def get_performance_event(self, event_id: str) -> PerformanceEventResponse | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM performance_events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            return None
        return PerformanceEventResponse(
            id=row["id"],
            campaign_id=row["campaign_id"],
            variant_id=row["variant_id"],
            platform=row["platform"],
            metric_type=row["metric_type"],
            metric_value=row["metric_value"],
            source=row["source"],
            note=row["note"],
            created_at=row["created_at"],
        )

    def list_performance_events(self, campaign_id: str | None = None) -> list[PerformanceEventResponse]:
        query = "SELECT * FROM performance_events"
        params: tuple[str, ...] = ()
        if campaign_id:
            query += " WHERE campaign_id = ?"
            params = (campaign_id,)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            PerformanceEventResponse(
                id=row["id"],
                campaign_id=row["campaign_id"],
                variant_id=row["variant_id"],
                platform=row["platform"],
                metric_type=row["metric_type"],
                metric_value=row["metric_value"],
                source=row["source"],
                note=row["note"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def build_performance_hints(self, campaign_id: str | None = None, limit: int = 5) -> list[str]:
        events = self.list_performance_events(campaign_id=campaign_id)
        hints: list[str] = []
        for event in events:
            if event.metric_value <= 0:
                continue
            variant = self.get_variant(event.variant_id) if event.variant_id else None
            if variant:
                hints.append(
                    f"{variant.platform} {event.metric_type}={event.metric_value}: reuse pattern from variant {variant.variant_name}"
                )
            else:
                hints.append(f"{event.platform} {event.metric_type}={event.metric_value}: keep this direction")
            if len(hints) >= limit:
                break
        return hints
