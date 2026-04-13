from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["normal", "watch", "warning", "critical"]
AlertSeverity = Literal["watch", "warning", "critical"]
AlertStatus = Literal["open", "acknowledged", "resolved"]
WorkOrderStatus = Literal["open", "in_progress", "resolved", "closed"]
DeviceStatus = Literal["online", "warning", "offline", "maintenance"]
DeviceType = Literal["tree", "soil", "water", "gateway"]
Connectivity = Literal["lorawan", "nbiot", "simulator", "manual"]


class ParkResponse(BaseModel):
    id: str
    name: str
    location: str
    city: str = "Delhi"
    area_hectares: float = 0
    status: str = "pilot"
    description: str = ""
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime
    updated_at: datetime


class ZoneResponse(BaseModel):
    id: str
    park_id: str
    name: str
    category: str
    description: str = ""
    created_at: datetime


class DeviceResponse(BaseModel):
    id: str
    park_id: str
    zone_id: str | None = None
    name: str
    device_type: DeviceType
    connectivity: Connectivity
    status: DeviceStatus = "online"
    battery_level: float | None = None
    firmware_version: str = ""
    last_seen_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ReadingResponse(BaseModel):
    id: str
    park_id: str
    device_id: str
    sensor_type: str
    metric_key: str
    metric_value: float
    unit: str
    risk_level: RiskLevel = "normal"
    source: str = "simulator"
    metadata: dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime


class AlertResponse(BaseModel):
    id: str
    park_id: str
    device_id: str | None = None
    severity: AlertSeverity
    status: AlertStatus = "open"
    title: str
    message: str
    metric_key: str = ""
    metric_value: float | None = None
    threshold_value: float | None = None
    created_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None


class WorkOrderResponse(BaseModel):
    id: str
    park_id: str
    alert_id: str | None = None
    title: str
    description: str = ""
    priority: AlertSeverity = "watch"
    status: WorkOrderStatus = "open"
    assigned_to: str = ""
    due_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CreateWorkOrderRequest(BaseModel):
    park_id: str
    alert_id: str | None = None
    title: str
    description: str = ""
    priority: AlertSeverity = "watch"
    assigned_to: str = ""
    due_at: datetime | None = None


class UpdateWorkOrderRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: AlertSeverity | None = None
    status: WorkOrderStatus | None = None
    assigned_to: str | None = None
    due_at: datetime | None = None


class IngestReadingItem(BaseModel):
    device_id: str
    metric_key: str
    metric_value: float
    unit: str
    recorded_at: datetime | None = None
    source: str = "hardware"
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestReadingsRequest(BaseModel):
    readings: list[IngestReadingItem] = Field(default_factory=list)


class IngestReadingsResponse(BaseModel):
    accepted: int = 0
    alerts_created: int = 0
    latest_alerts: list[AlertResponse] = Field(default_factory=list)


class SimulationRequest(BaseModel):
    ticks: int = 1
    park_id: str | None = None


class SimulationResponse(BaseModel):
    ticks: int
    readings_created: int
    alerts_created: int
    affected_parks: list[str] = Field(default_factory=list)


class BudgetSnapshotResponse(BaseModel):
    total_budget_lakh: float = 10
    committed_budget_lakh: float = 6.86
    buffer_budget_lakh: float = 3.14
    phase: str = "Phase 1 Pilot"


class DashboardSummaryResponse(BaseModel):
    park_count: int
    zone_count: int
    device_count: int
    online_devices: int
    active_alerts: int
    open_work_orders: int
    latest_readings: int
    readiness_score: float
    budget: BudgetSnapshotResponse


class ParkRiskSummaryResponse(BaseModel):
    park_id: str
    park_name: str
    latest_tree_risk: RiskLevel = "normal"
    latest_soil_risk: RiskLevel = "normal"
    latest_water_risk: RiskLevel = "normal"
    open_alerts: int = 0
    open_work_orders: int = 0
    latest_note: str = ""


class ReportsOverviewResponse(BaseModel):
    generated_at: datetime
    pilot_window: str
    total_alerts: int
    resolved_alerts: int
    unresolved_alerts: int
    average_battery_level: float
    risk_distribution: dict[str, int] = Field(default_factory=dict)
    park_summaries: list[ParkRiskSummaryResponse] = Field(default_factory=list)


class DashboardBundleResponse(BaseModel):
    summary: DashboardSummaryResponse
    parks: list[ParkResponse] = Field(default_factory=list)
    zones: list[ZoneResponse] = Field(default_factory=list)
    devices: list[DeviceResponse] = Field(default_factory=list)
    readings: list[ReadingResponse] = Field(default_factory=list)
    alerts: list[AlertResponse] = Field(default_factory=list)
    work_orders: list[WorkOrderResponse] = Field(default_factory=list)
    park_risks: list[ParkRiskSummaryResponse] = Field(default_factory=list)
