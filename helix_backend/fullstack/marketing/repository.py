from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from ..config import Settings
from .models import DDL_STATEMENTS, INDEX_STATEMENTS, utc_now_iso
from .schemas import (
    BrandProfileResponse,
    CampaignResponse,
    CreateBrandProfileRequest,
    CreateCampaignRequest,
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
