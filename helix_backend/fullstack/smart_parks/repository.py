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

    def ingest_readings(self, payload: IngestReadingsRequest) -> IngestReadingsResponse:
        created_alerts: list[AlertResponse] = []
        accepted = 0
        with self._connect() as conn:
            for item in payload.readings:
                device_row = conn.execute("SELECT * FROM devices WHERE id = ?", (item.device_id,)).fetchone()
                if not device_row:
                    continue
                accepted += 1
                park_id = device_row["park_id"]
                recorded_at = (item.recorded_at or datetime.now(timezone.utc)).isoformat()
                sensor_type = device_row["device_type"]
                risk, threshold = self._classify_risk(item.metric_key, item.metric_value)
                conn.execute(
                    """
                    INSERT INTO telemetry_readings (
                        id, park_id, device_id, sensor_type, metric_key, metric_value, unit,
                        risk_level, source, metadata, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        park_id,
                        item.device_id,
                        sensor_type,
                        item.metric_key,
                        item.metric_value,
                        item.unit,
                        risk,
                        item.source,
                        json.dumps(item.metadata),
                        recorded_at,
                    ),
                )
                conn.execute(
                    """
                    UPDATE devices
                    SET last_seen_at = ?, updated_at = ?, status = ?, battery_level = COALESCE(battery_level, ?)
                    WHERE id = ?
                    """,
                    (
                        recorded_at,
                        utc_now_iso(),
                        "warning" if risk in {"warning", "critical"} else "online",
                        round(random.uniform(55, 97), 2),
                        item.device_id,
                    ),
                )
                alert = self._maybe_create_alert(conn, park_id, item.device_id, item.metric_key, item.metric_value, risk, threshold)
                if alert:
                    created_alerts.append(alert)

        return IngestReadingsResponse(
            accepted=accepted,
            alerts_created=len(created_alerts),
            latest_alerts=created_alerts[-10:],
        )

    def _classify_risk(self, metric_key: str, value: float) -> tuple[str, float | None]:
        rule = THRESHOLDS.get(metric_key)
        if not rule:
            return "normal", None

        if "critical" in rule and value >= rule["critical"]:
            return "critical", rule["critical"]
        if "warning" in rule and value >= rule["warning"]:
            return "warning", rule["warning"]
        if "watch" in rule and value >= rule["watch"]:
            return "watch", rule["watch"]
        if "critical_low" in rule and value <= rule["critical_low"]:
            return "critical", rule["critical_low"]
        if "warning_low" in rule and value <= rule["warning_low"]:
            return "warning", rule["warning_low"]
        if "watch_low" in rule and value <= rule["watch_low"]:
            return "watch", rule["watch_low"]
        if "critical_high" in rule and value >= rule["critical_high"]:
            return "critical", rule["critical_high"]
        if "warning_high" in rule and value >= rule["warning_high"]:
            return "warning", rule["warning_high"]
        if "watch_high" in rule and value >= rule["watch_high"]:
            return "watch", rule["watch_high"]
        return "normal", None

    def _maybe_create_alert(
        self,
        conn: sqlite3.Connection,
        park_id: str,
        device_id: str,
        metric_key: str,
        metric_value: float,
        risk_level: str,
        threshold: float | None,
    ) -> AlertResponse | None:
        if risk_level == "normal":
            return None
        existing = conn.execute(
            """
            SELECT * FROM alerts
            WHERE park_id = ? AND device_id = ? AND metric_key = ? AND status != 'resolved'
            ORDER BY created_at DESC LIMIT 1
            """,
            (park_id, device_id, metric_key),
        ).fetchone()
        if existing:
            return None

        severity = "critical" if risk_level == "critical" else "warning" if risk_level == "warning" else "watch"
        record_id = str(uuid4())
        created_at = utc_now_iso()
        title = f"{metric_key.replace('_', ' ').title()} threshold breach"
        message = f"Device {device_id} reported {metric_value:.2f} for {metric_key}, entering {risk_level} risk."
        conn.execute(
            """
            INSERT INTO alerts (
                id, park_id, device_id, severity, status, title, message,
                metric_key, metric_value, threshold_value, created_at
            ) VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)
            """,
            (record_id, park_id, device_id, severity, title, message, metric_key, metric_value, threshold, created_at),
        )
        row = conn.execute("SELECT * FROM alerts WHERE id = ?", (record_id,)).fetchone()
        if severity == "critical":
            conn.execute(
                """
                INSERT INTO work_orders (
                    id, park_id, alert_id, title, description, priority, status, assigned_to, due_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'open', '', ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    park_id,
                    record_id,
                    f"Inspect {metric_key.replace('_', ' ')} issue",
                    f"Auto-created from critical alert on device {device_id}.",
                    severity,
                    (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                    created_at,
                    created_at,
                ),
            )
        return self._alert_from_row(row)

    def run_simulation(self, ticks: int = 1, park_id: str | None = None) -> SimulationResponse:
        generated_readings = 0
        generated_alerts = 0
        affected_parks: set[str] = set()
        for _ in range(max(1, ticks)):
            payload_items = []
            for device in self.list_devices(park_id=park_id):
                affected_parks.add(device.park_id)
                for metric_key, unit, value in self._simulate_metrics(device):
                    payload_items.append(
                        {
                            "device_id": device.id,
                            "metric_key": metric_key,
                            "metric_value": value,
                            "unit": unit,
                            "metadata": {"simulated": True},
                        }
                    )
            response = self.ingest_readings(IngestReadingsRequest(readings=payload_items))
            generated_readings += response.accepted
            generated_alerts += response.alerts_created
        return SimulationResponse(
            ticks=ticks,
            readings_created=generated_readings,
            alerts_created=generated_alerts,
            affected_parks=sorted(affected_parks),
        )

    def _simulate_metrics(self, device: DeviceResponse) -> list[tuple[str, str, float]]:
        if device.device_type == "tree":
            return [
                ("tree_tilt_deg", "deg", round(random.uniform(2.0, 11.5), 2)),
                ("tree_bark_temp_c", "c", round(random.uniform(27.0, 40.5), 2)),
            ]
        if device.device_type == "soil":
            return [
                ("soil_moisture_pct", "%", round(random.uniform(16.0, 48.0), 2)),
                ("soil_npk_index", "index", round(random.uniform(24.0, 76.0), 2)),
                ("soil_ph", "ph", round(random.uniform(5.0, 8.9), 2)),
            ]
        if device.device_type == "water":
            return [
                ("water_tds_ppm", "ppm", round(random.uniform(420.0, 1350.0), 2)),
                ("water_turbidity_ntu", "ntu", round(random.uniform(8.0, 42.0), 2)),
                ("water_dissolved_oxygen_mg_l", "mg/l", round(random.uniform(2.0, 7.0), 2)),
            ]
        return [("gateway_heartbeat", "count", 1.0)]

    def dashboard_summary(self) -> DashboardSummaryResponse:
        parks = self.list_parks()
        zones = self.list_zones()
        devices = self.list_devices()
        alerts = self.list_alerts(status="open")
        work_orders = self.list_work_orders()
        readings = self.list_readings(limit=50)
        online_devices = len([device for device in devices if device.status == "online"])
        open_work_orders = len([item for item in work_orders if item.status not in {"resolved", "closed"}])
        readiness_score = round(((online_devices / max(1, len(devices))) * 60) + (max(0, 20 - len(alerts)) / 20 * 20) + 20, 2)
        return DashboardSummaryResponse(
            park_count=len(parks),
            zone_count=len(zones),
            device_count=len(devices),
            online_devices=online_devices,
            active_alerts=len(alerts),
            open_work_orders=open_work_orders,
            latest_readings=len(readings),
            readiness_score=min(readiness_score, 100),
            budget=BudgetSnapshotResponse(),
        )

    def park_risk_summary(self) -> list[ParkRiskSummaryResponse]:
        risks: list[ParkRiskSummaryResponse] = []
        alerts = self.list_alerts()
        work_orders = self.list_work_orders()
        now = datetime.now(timezone.utc)
        default_tree = ReadingResponse(id="", park_id="", device_id="", sensor_type="tree", metric_key="", metric_value=0, unit="", risk_level="normal", recorded_at=now)
        default_soil = ReadingResponse(id="", park_id="", device_id="", sensor_type="soil", metric_key="", metric_value=0, unit="", risk_level="normal", recorded_at=now)
        default_water = ReadingResponse(id="", park_id="", device_id="", sensor_type="water", metric_key="", metric_value=0, unit="", risk_level="normal", recorded_at=now)
        for park in self.list_parks():
            readings = self.list_readings(park_id=park.id, limit=50)
            latest_by_sensor: dict[str, ReadingResponse] = {}
            for reading in readings:
                latest_by_sensor.setdefault(reading.sensor_type, reading)
            park_alerts = [item for item in alerts if item.park_id == park.id and item.status != "resolved"]
            park_orders = [item for item in work_orders if item.park_id == park.id and item.status not in {"resolved", "closed"}]
            note = park_alerts[0].message if park_alerts else (readings[0].metric_key.replace("_", " ") if readings else "Awaiting telemetry")
            risks.append(
                ParkRiskSummaryResponse(
                    park_id=park.id,
                    park_name=park.name,
                    latest_tree_risk=latest_by_sensor.get("tree", default_tree).risk_level,
                    latest_soil_risk=latest_by_sensor.get("soil", default_soil).risk_level,
                    latest_water_risk=latest_by_sensor.get("water", default_water).risk_level,
                    open_alerts=len(park_alerts),
                    open_work_orders=len(park_orders),
                    latest_note=note,
                )
            )
        return risks

    def reports_overview(self) -> ReportsOverviewResponse:
        alerts = self.list_alerts()
        resolved = len([item for item in alerts if item.status == "resolved"])
        unresolved = len(alerts) - resolved
        devices = self.list_devices()
        batteries = [item.battery_level for item in devices if item.battery_level is not None]
        readings = self.list_readings(limit=250)
        risk_distribution = {"normal": 0, "watch": 0, "warning": 0, "critical": 0}
        for reading in readings:
            risk_distribution[reading.risk_level] = risk_distribution.get(reading.risk_level, 0) + 1
        return ReportsOverviewResponse(
            generated_at=datetime.now(timezone.utc),
            pilot_window="90-day pilot setup with rolling telemetry baseline",
            total_alerts=len(alerts),
            resolved_alerts=resolved,
            unresolved_alerts=unresolved,
            average_battery_level=round(sum(batteries) / len(batteries), 2) if batteries else 0,
            risk_distribution=risk_distribution,
            park_summaries=self.park_risk_summary(),
        )

    def dashboard_bundle(self) -> DashboardBundleResponse:
        return DashboardBundleResponse(
            summary=self.dashboard_summary(),
            parks=self.list_parks(),
            zones=self.list_zones(),
            devices=self.list_devices(),
            readings=self.list_readings(limit=120),
            alerts=self.list_alerts(),
            work_orders=self.list_work_orders(),
            park_risks=self.park_risk_summary(),
        )
