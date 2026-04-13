from __future__ import annotations

import json
import logging
import random
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from ..config import Settings
from .models import DDL_STATEMENTS, INDEX_STATEMENTS, utc_now_iso
from .schemas import (
    AlertResponse,
    BudgetSnapshotResponse,
    CreateWorkOrderRequest,
    DashboardBundleResponse,
    DashboardSummaryResponse,
    DeviceResponse,
    IngestReadingsRequest,
    IngestReadingsResponse,
    ParkResponse,
    ParkRiskSummaryResponse,
    ReadingResponse,
    ReportsOverviewResponse,
    SimulationResponse,
    UpdateWorkOrderRequest,
    WorkOrderResponse,
    ZoneResponse,
)

logger = logging.getLogger(__name__)


THRESHOLDS: dict[str, dict[str, float]] = {
    "tree_tilt_deg": {"watch": 5, "warning": 8, "critical": 12},
    "tree_bark_temp_c": {"watch": 33, "warning": 38, "critical": 42},
    "soil_moisture_pct": {"critical_low": 18, "warning_low": 25, "watch_low": 32},
    "soil_npk_index": {"critical_low": 28, "warning_low": 40, "watch_low": 52},
    "soil_ph": {"watch_low": 5.8, "warning_low": 5.2, "critical_low": 4.8, "watch_high": 8.1, "warning_high": 8.6, "critical_high": 9.0},
    "water_tds_ppm": {"watch": 650, "warning": 900, "critical": 1200},
    "water_turbidity_ntu": {"watch": 15, "warning": 25, "critical": 40},
    "water_dissolved_oxygen_mg_l": {"critical_low": 2.5, "warning_low": 4.0, "watch_low": 5.0},
}


class SmartParksRepository:
    def __init__(self, settings: Settings):
        db_path = Path(settings.smart_parks_db_path)
        if not db_path.is_absolute():
            db_path = Path(settings.root_dir) / db_path
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self._seed_if_empty()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _decode_json(raw: str | None, fallback):
        if not raw:
            return fallback
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return fallback

    def _initialize(self) -> None:
        with self._connect() as conn:
            for statement in DDL_STATEMENTS:
                conn.execute(statement)
            for statement in INDEX_STATEMENTS:
                conn.execute(statement)

    def _seed_if_empty(self) -> None:
        with self._connect() as conn:
            existing = conn.execute("SELECT COUNT(*) AS count FROM parks").fetchone()
            if existing and existing["count"] > 0:
                return

            now = utc_now_iso()
            parks = [
                ("park-nehru-ridge", "Nehru Ridge Pilot", "Central Ridge, Delhi", 14.2, "Tree stability pilot near dense canopy", 28.6822, 77.2058),
                ("park-dwarka-green", "Dwarka Sector Green", "Dwarka Sector 12, Delhi", 9.1, "High sapling turnover and irrigation variability", 28.5921, 77.0460),
                ("park-yamuna-edge", "Yamuna Biodiversity Edge", "Yamuna floodplain edge, Delhi", 11.8, "Water quality sensitivity and runoff exposure", 28.6129, 77.2755),
            ]
            conn.executemany(
                """
                INSERT INTO parks (id, name, location, city, area_hectares, status, description, latitude, longitude, created_at, updated_at)
                VALUES (?, ?, ?, 'Delhi', ?, 'pilot', ?, ?, ?, ?, ?)
                """,
                [(park_id, name, location, area, description, lat, lng, now, now) for park_id, name, location, area, description, lat, lng in parks],
            )

            zones = [
                ("zone-ridge-tree", "park-nehru-ridge", "North Canopy", "tree"),
                ("zone-ridge-soil", "park-nehru-ridge", "Plantation Belt", "soil"),
                ("zone-dwarka-soil", "park-dwarka-green", "Sapling Corridor", "soil"),
                ("zone-dwarka-tree", "park-dwarka-green", "Perimeter Trees", "tree"),
                ("zone-yamuna-water", "park-yamuna-edge", "Retention Pond", "water"),
                ("zone-yamuna-soil", "park-yamuna-edge", "Floodplain Soil", "soil"),
            ]
            conn.executemany(
                "INSERT INTO park_zones (id, park_id, name, category, description, created_at) VALUES (?, ?, ?, ?, '', ?)",
                [(zone_id, park_id, name, category, now) for zone_id, park_id, name, category in zones],
            )

            devices = [
                ("dev-tree-01", "park-nehru-ridge", "zone-ridge-tree", "Ridge Tilt Mast 01", "tree", "lorawan"),
                ("dev-soil-01", "park-nehru-ridge", "zone-ridge-soil", "Ridge Soil Pod 01", "soil", "lorawan"),
                ("dev-gw-01", "park-nehru-ridge", None, "Ridge Gateway", "gateway", "nbiot"),
                ("dev-soil-02", "park-dwarka-green", "zone-dwarka-soil", "Dwarka Soil Pod 01", "soil", "lorawan"),
                ("dev-tree-02", "park-dwarka-green", "zone-dwarka-tree", "Dwarka Tilt Mast 01", "tree", "lorawan"),
                ("dev-gw-02", "park-dwarka-green", None, "Dwarka Gateway", "gateway", "nbiot"),
                ("dev-water-01", "park-yamuna-edge", "zone-yamuna-water", "Yamuna Pond Probe", "water", "lorawan"),
                ("dev-soil-03", "park-yamuna-edge", "zone-yamuna-soil", "Yamuna Soil Pod 01", "soil", "lorawan"),
                ("dev-gw-03", "park-yamuna-edge", None, "Yamuna Gateway", "gateway", "nbiot"),
            ]
            for device_id, park_id, zone_id, name, device_type, connectivity in devices:
                metadata = {"sensor_profile": device_type, "hardware_ready": True}
                conn.execute(
                    """
                    INSERT INTO devices (
                        id, park_id, zone_id, name, device_type, connectivity, status, battery_level,
                        firmware_version, last_seen_at, metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'online', ?, 'v1.0.0', ?, ?, ?, ?)
                    """,
                    (
                        device_id,
                        park_id,
                        zone_id,
                        name,
                        device_type,
                        connectivity,
                        round(random.uniform(72, 98), 2),
                        now,
                        json.dumps(metadata),
                        now,
                        now,
                    ),
                )

        self.run_simulation(ticks=2)

    def _park_from_row(self, row) -> ParkResponse:
        return ParkResponse(
            id=row["id"],
            name=row["name"],
            location=row["location"],
            city=row["city"],
            area_hectares=row["area_hectares"],
            status=row["status"],
            description=row["description"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _zone_from_row(self, row) -> ZoneResponse:
        return ZoneResponse(
            id=row["id"],
            park_id=row["park_id"],
            name=row["name"],
            category=row["category"],
            description=row["description"],
            created_at=row["created_at"],
        )

    def _device_from_row(self, row) -> DeviceResponse:
        return DeviceResponse(
            id=row["id"],
            park_id=row["park_id"],
            zone_id=row["zone_id"],
            name=row["name"],
            device_type=row["device_type"],
            connectivity=row["connectivity"],
            status=row["status"],
            battery_level=row["battery_level"],
            firmware_version=row["firmware_version"],
            last_seen_at=row["last_seen_at"],
            metadata=self._decode_json(row["metadata"], {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _reading_from_row(self, row) -> ReadingResponse:
        return ReadingResponse(
            id=row["id"],
            park_id=row["park_id"],
            device_id=row["device_id"],
            sensor_type=row["sensor_type"],
            metric_key=row["metric_key"],
            metric_value=row["metric_value"],
            unit=row["unit"],
            risk_level=row["risk_level"],
            source=row["source"],
            metadata=self._decode_json(row["metadata"], {}),
            recorded_at=row["recorded_at"],
        )

    def _alert_from_row(self, row) -> AlertResponse:
        return AlertResponse(
            id=row["id"],
            park_id=row["park_id"],
            device_id=row["device_id"],
            severity=row["severity"],
            status=row["status"],
            title=row["title"],
            message=row["message"],
            metric_key=row["metric_key"],
            metric_value=row["metric_value"],
            threshold_value=row["threshold_value"],
            created_at=row["created_at"],
            acknowledged_at=row["acknowledged_at"],
            resolved_at=row["resolved_at"],
        )

    def _work_order_from_row(self, row) -> WorkOrderResponse:
        return WorkOrderResponse(
            id=row["id"],
            park_id=row["park_id"],
            alert_id=row["alert_id"],
            title=row["title"],
            description=row["description"],
            priority=row["priority"],
            status=row["status"],
            assigned_to=row["assigned_to"],
            due_at=row["due_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_parks(self) -> list[ParkResponse]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM parks ORDER BY name ASC").fetchall()
        return [self._park_from_row(row) for row in rows]

    def get_park(self, park_id: str) -> ParkResponse | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM parks WHERE id = ?", (park_id,)).fetchone()
        return self._park_from_row(row) if row else None

    def list_zones(self, park_id: str | None = None) -> list[ZoneResponse]:
        query = "SELECT * FROM park_zones"
        params: tuple[str, ...] = ()
        if park_id:
            query += " WHERE park_id = ?"
            params = (park_id,)
        query += " ORDER BY name ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._zone_from_row(row) for row in rows]

    def list_devices(self, park_id: str | None = None) -> list[DeviceResponse]:
        query = "SELECT * FROM devices"
        params: tuple[str, ...] = ()
        if park_id:
            query += " WHERE park_id = ?"
            params = (park_id,)
        query += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._device_from_row(row) for row in rows]

    def list_readings(self, park_id: str | None = None, device_id: str | None = None, limit: int = 100) -> list[ReadingResponse]:
        query = "SELECT * FROM telemetry_readings"
        params: list[object] = []
        clauses = []
        if park_id:
            clauses.append("park_id = ?")
            params.append(park_id)
        if device_id:
            clauses.append("device_id = ?")
            params.append(device_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY recorded_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._reading_from_row(row) for row in rows]

    def list_alerts(self, status: str | None = None, park_id: str | None = None) -> list[AlertResponse]:
        query = "SELECT * FROM alerts"
        params: list[str] = []
        clauses = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if park_id:
            clauses.append("park_id = ?")
            params.append(park_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._alert_from_row(row) for row in rows]

    def list_work_orders(self, status: str | None = None, park_id: str | None = None) -> list[WorkOrderResponse]:
        query = "SELECT * FROM work_orders"
        params: list[str] = []
        clauses = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if park_id:
            clauses.append("park_id = ?")
            params.append(park_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._work_order_from_row(row) for row in rows]

    def acknowledge_alert(self, alert_id: str) -> AlertResponse | None:
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                "UPDATE alerts SET status = 'acknowledged', acknowledged_at = ? WHERE id = ? AND status = 'open'",
                (now, alert_id),
            )
            row = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        return self._alert_from_row(row) if row else None

    def resolve_alert(self, alert_id: str) -> AlertResponse | None:
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                "UPDATE alerts SET status = 'resolved', resolved_at = ? WHERE id = ? AND status != 'resolved'",
                (now, alert_id),
            )
            row = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        return self._alert_from_row(row) if row else None

    def create_work_order(self, payload: CreateWorkOrderRequest) -> WorkOrderResponse:
        record_id = str(uuid4())
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO work_orders (
                    id, park_id, alert_id, title, description, priority, status,
                    assigned_to, due_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)
                """,
                (
                    record_id,
                    payload.park_id,
                    payload.alert_id,
                    payload.title,
                    payload.description,
                    payload.priority,
                    payload.assigned_to,
                    payload.due_at.isoformat() if payload.due_at else None,
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM work_orders WHERE id = ?", (record_id,)).fetchone()
        return self._work_order_from_row(row)

    def update_work_order(self, work_order_id: str, payload: UpdateWorkOrderRequest) -> WorkOrderResponse | None:
        updates = payload.model_dump(exclude_none=True)
        if not updates:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM work_orders WHERE id = ?", (work_order_id,)).fetchone()
            return self._work_order_from_row(row) if row else None

        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM work_orders WHERE id = ?", (work_order_id,)).fetchone()
            if not existing:
                return None
            row = dict(existing)
            merged = {
                "title": updates.get("title", row["title"]),
                "description": updates.get("description", row["description"]),
                "priority": updates.get("priority", row["priority"]),
                "status": updates.get("status", row["status"]),
                "assigned_to": updates.get("assigned_to", row["assigned_to"]),
                "due_at": updates.get("due_at", row["due_at"]),
                "updated_at": utc_now_iso(),
            }
            due_at = merged["due_at"].isoformat() if isinstance(merged["due_at"], datetime) else merged["due_at"]
            conn.execute(
                """
                UPDATE work_orders
                SET title = ?, description = ?, priority = ?, status = ?, assigned_to = ?, due_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    merged["title"],
                    merged["description"],
                    merged["priority"],
                    merged["status"],
                    merged["assigned_to"],
                    due_at,
                    merged["updated_at"],
                    work_order_id,
                ),
            )
            row = conn.execute("SELECT * FROM work_orders WHERE id = ?", (work_order_id,)).fetchone()
        return self._work_order_from_row(row)
