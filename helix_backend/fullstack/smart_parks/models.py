from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS parks (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        city TEXT NOT NULL DEFAULT 'Delhi',
        area_hectares REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pilot',
        description TEXT NOT NULL DEFAULT '',
        latitude REAL,
        longitude REAL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS park_zones (
        id TEXT PRIMARY KEY,
        park_id TEXT NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY (park_id) REFERENCES parks(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY,
        park_id TEXT NOT NULL,
        zone_id TEXT,
        name TEXT NOT NULL,
        device_type TEXT NOT NULL,
        connectivity TEXT NOT NULL DEFAULT 'simulator',
        status TEXT NOT NULL DEFAULT 'online',
        battery_level REAL,
        firmware_version TEXT NOT NULL DEFAULT '',
        last_seen_at TEXT,
        metadata TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (park_id) REFERENCES parks(id) ON DELETE CASCADE,
        FOREIGN KEY (zone_id) REFERENCES park_zones(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS telemetry_readings (
        id TEXT PRIMARY KEY,
        park_id TEXT NOT NULL,
        device_id TEXT NOT NULL,
        sensor_type TEXT NOT NULL,
        metric_key TEXT NOT NULL,
        metric_value REAL NOT NULL,
        unit TEXT NOT NULL,
        risk_level TEXT NOT NULL DEFAULT 'normal',
        source TEXT NOT NULL DEFAULT 'simulator',
        metadata TEXT NOT NULL DEFAULT '{}',
        recorded_at TEXT NOT NULL,
        FOREIGN KEY (park_id) REFERENCES parks(id) ON DELETE CASCADE,
        FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        park_id TEXT NOT NULL,
        device_id TEXT,
        severity TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        metric_key TEXT NOT NULL DEFAULT '',
        metric_value REAL,
        threshold_value REAL,
        created_at TEXT NOT NULL,
        acknowledged_at TEXT,
        resolved_at TEXT,
        FOREIGN KEY (park_id) REFERENCES parks(id) ON DELETE CASCADE,
        FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS work_orders (
        id TEXT PRIMARY KEY,
        park_id TEXT NOT NULL,
        alert_id TEXT,
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        priority TEXT NOT NULL DEFAULT 'watch',
        status TEXT NOT NULL DEFAULT 'open',
        assigned_to TEXT NOT NULL DEFAULT '',
        due_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (park_id) REFERENCES parks(id) ON DELETE CASCADE,
        FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE SET NULL
    )
    """,
]


INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_devices_park_type ON devices(park_id, device_type)",
    "CREATE INDEX IF NOT EXISTS idx_readings_device_metric_time ON telemetry_readings(device_id, metric_key, recorded_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_readings_park_time ON telemetry_readings(park_id, recorded_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_status_severity ON alerts(status, severity)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_park_device ON alerts(park_id, device_id)",
    "CREATE INDEX IF NOT EXISTS idx_work_orders_status_priority ON work_orders(status, priority)",
]
