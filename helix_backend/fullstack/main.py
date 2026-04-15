from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from rl.state import StatePreprocessor

from .auth import require_api_token
from .config import get_settings
from .rate_limit import rate_limit_dependency
from .schemas import FeedbackRequest, FeedbackResponse, PersonalityProfile, StatusResponse, TrainingRunRequest, TrainingRunResponse, ChatRequest
from .services.model_service import AdaptiveInferenceService
from .services.profile_adapter import infer_profile_from_message, update_profile_from_feedback
from .services.prompt_builder import build_conditioned_prompt
from .services.repository import SupabaseRepository
from .services.retrieval_service import RetrievalService
from .services.reward_service import feedback_reward
from .services.training_service import OfflineRLHFService
from .marketing import LocalMarketingRepository, MarketingCampaignService, MarketingPromptEngine, MarketingStrategyService
from .marketing import MarketingApprovalService, MarketingSafetyService, MarketingSchedulerService
from .marketing import MarketingDeliveryService
from .marketing import MarketingAnalyticsService
from .marketing import MarketingOptimizationService
from .marketing import MarketingCredentialService
from .smart_parks import SmartParksRepository
from .marketing.schemas import (
    ApprovalResultResponse,
    AnalyticsSummaryResponse,
    ApproveVariantRequest,
    BrandProfileResponse,
    CampaignResponse,
    ChannelCredentialResponse,
    CreateBrandProfileRequest,
    CreateCampaignRequest,
    DeliveryLogResponse,
    DispatchJobRequest,
    GenerateVariantsRequest,
    GenerateVariantsResponse,
    PlatformAdapterStatusResponse,
    PerformanceEventResponse,
    OptimizationSummaryResponse,
    RecordPerformanceEventRequest,
    ScheduleCampaignRequest,
    ScheduleCampaignResponse,
    ScheduledJobResponse,
    StrategyRequest,
    StrategyResponse,
    UpsertChannelCredentialRequest,
    UpdateBrandProfileRequest,
)
from .smart_parks.schemas import (
    AlertResponse as SmartParkAlertResponse,
    CreateWorkOrderRequest,
    DashboardBundleResponse,
    DashboardSummaryResponse,
    DeviceResponse,
    HardwareContractResponse,
    IngestReadingsRequest,
    IngestReadingsResponse,
    ParkResponse,
    ParkRiskSummaryResponse,
    ReadingResponse,
    RegisterDeviceRequest,
    ReportsOverviewResponse,
    SimulationRequest,
    SimulationResponse,
    ThresholdEntryResponse,
    UpdateWorkOrderRequest,
    WorkOrderResponse,
    ZoneResponse,
)

from pathlib import Path

logger = logging.getLogger(__name__)

settings = get_settings()
repository = SupabaseRepository(settings)
model_service = AdaptiveInferenceService(settings)
retrieval_service = RetrievalService(repository)
training_service = OfflineRLHFService(repository, model_service, settings.adapter_root)
embedding_preprocessor = StatePreprocessor()
marketing_repository = LocalMarketingRepository(settings)
marketing_credential_service = MarketingCredentialService(marketing_repository, settings)
marketing_strategy_service = MarketingStrategyService()
marketing_prompt_engine = MarketingPromptEngine()
marketing_campaign_service = MarketingCampaignService(
    marketing_repository,
    marketing_strategy_service,
    marketing_prompt_engine,
)
marketing_safety_service = MarketingSafetyService(marketing_repository)
marketing_approval_service = MarketingApprovalService(marketing_repository, marketing_safety_service)
marketing_scheduler_service = MarketingSchedulerService(marketing_repository)
marketing_delivery_service = MarketingDeliveryService(marketing_repository, settings, marketing_credential_service)
marketing_analytics_service = MarketingAnalyticsService(marketing_repository)
marketing_optimization_service = MarketingOptimizationService(marketing_repository, marketing_analytics_service)
smart_parks_repository = SmartParksRepository(settings)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://helix-ai-eta.vercel.app", "http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-API-Token", "X-Requested-With"],
)

AuthDep = Annotated[str, Depends(require_api_token)]
RateDep = Annotated[None, Depends(rate_limit_dependency)]

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    from fastapi.responses import JSONResponse
    
    # Handle FastAPI HTTPExceptions properly
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers={
                "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
                "Access-Control-Allow-Credentials": "true",
            }
        )
        
    logger.error(f"GLOBAL EXCEPTION: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Crash",
            "exception": str(exc),
            "traceback": traceback.format_exc()
        },
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.on_event("startup")
async def on_startup() -> None:
    marketing_scheduler_service.start()
    marketing_delivery_service.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    marketing_scheduler_service.shutdown()
    marketing_delivery_service.shutdown()


@app.get("/")
async def root():
    return {"message": "HELIX V1 API is online.", "docs": "/docs"}


@app.post("/api/auth/signup")
async def signup(payload: dict):
    email = payload.get("email", "")
    password = payload.get("password", "")
    name = payload.get("name", "")
    user_id, error = repository.signup(email, password, name)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"user_id": user_id, "message": "Account created successfully"}


@app.post("/api/auth/login")
async def login(payload: dict):
    email = payload.get("email", "")
    password = payload.get("password", "")
    user_id, error = repository.login(email, password)
    if error:
        raise HTTPException(status_code=401, detail=error)
    return {"user_id": user_id, "message": "Login successful"}


@app.post("/api/marketing/brand-profiles", response_model=BrandProfileResponse)
async def create_brand_profile(payload: CreateBrandProfileRequest, _: AuthDep, __: RateDep) -> BrandProfileResponse:
    return marketing_repository.upsert_brand_profile(payload)


@app.get("/api/marketing/brand-profiles", response_model=list[BrandProfileResponse])
async def list_brand_profiles(_: AuthDep, __: RateDep) -> list[BrandProfileResponse]:
    return marketing_repository.list_brand_profiles()


@app.get("/api/marketing/brand-profiles/{brand_id}", response_model=BrandProfileResponse)
async def get_brand_profile(brand_id: str, _: AuthDep, __: RateDep) -> BrandProfileResponse:
    brand = marketing_repository.get_brand_profile(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    return brand


@app.put("/api/marketing/brand-profiles/{brand_id}", response_model=BrandProfileResponse)
async def update_brand_profile(
    brand_id: str,
    payload: UpdateBrandProfileRequest,
    _: AuthDep,
    __: RateDep,
) -> BrandProfileResponse:
    return marketing_repository.upsert_brand_profile(payload, brand_id=brand_id)


@app.post("/api/marketing/campaigns", response_model=CampaignResponse)
async def create_marketing_campaign(payload: CreateCampaignRequest, _: AuthDep, __: RateDep) -> CampaignResponse:
    return marketing_repository.create_campaign(payload)


@app.get("/api/marketing/campaigns", response_model=list[CampaignResponse])
async def list_marketing_campaigns(_: AuthDep, __: RateDep, status: str | None = None) -> list[CampaignResponse]:
    return marketing_repository.list_campaigns(status=status)


@app.get("/api/marketing/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_marketing_campaign(campaign_id: str, _: AuthDep, __: RateDep) -> CampaignResponse:
    campaign = marketing_repository.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@app.post("/api/marketing/strategy", response_model=StrategyResponse)
async def infer_marketing_strategy(payload: StrategyRequest, _: AuthDep, __: RateDep) -> StrategyResponse:
    return marketing_strategy_service.infer_strategy(payload)


@app.post("/api/marketing/campaigns/{campaign_id}/strategy", response_model=StrategyResponse)
async def generate_campaign_strategy(campaign_id: str, _: AuthDep, __: RateDep) -> StrategyResponse:
    result = marketing_campaign_service.generate_strategy_for_campaign(campaign_id)
    if not result:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _, strategy = result
    return strategy


@app.post("/api/marketing/campaigns/{campaign_id}/generate", response_model=GenerateVariantsResponse)
async def generate_campaign_variants(
    campaign_id: str,
    payload: GenerateVariantsRequest,
    _: AuthDep,
    __: RateDep,
) -> GenerateVariantsResponse:
    result = marketing_campaign_service.generate_variants(campaign_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result


@app.get("/api/marketing/campaigns/{campaign_id}/variants")
async def list_campaign_variants(campaign_id: str, _: AuthDep, __: RateDep):
    campaign = marketing_repository.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"items": [item.model_dump() for item in marketing_repository.list_variants(campaign_id)]}


@app.post("/api/marketing/variants/{variant_id}/approve", response_model=ApprovalResultResponse)
async def review_campaign_variant(
    variant_id: str,
    payload: ApproveVariantRequest,
    _: AuthDep,
    __: RateDep,
) -> ApprovalResultResponse:
    result = marketing_approval_service.review_variant(variant_id, approved=payload.approved)
    if not result:
        raise HTTPException(status_code=404, detail="Variant not found")
    return result


@app.post("/api/marketing/campaigns/{campaign_id}/schedule", response_model=ScheduleCampaignResponse)
async def schedule_campaign(
    campaign_id: str,
    payload: ScheduleCampaignRequest,
    _: AuthDep,
    __: RateDep,
) -> ScheduleCampaignResponse:
    campaign = marketing_repository.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return marketing_scheduler_service.schedule_campaign(campaign_id, payload)


@app.get("/api/marketing/schedules", response_model=list[ScheduledJobResponse])
async def list_campaign_schedules(_: AuthDep, __: RateDep, status: str | None = None) -> list[ScheduledJobResponse]:
    return marketing_repository.list_scheduled_jobs(status=status)


@app.post("/api/marketing/schedules/{job_id}/pause", response_model=ScheduledJobResponse)
async def pause_campaign_schedule(job_id: str, _: AuthDep, __: RateDep) -> ScheduledJobResponse:
    job = marketing_repository.update_scheduled_job_status(job_id, "paused")
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")
    return job


@app.post("/api/marketing/schedules/{job_id}/resume", response_model=ScheduledJobResponse)
async def resume_campaign_schedule(job_id: str, _: AuthDep, __: RateDep) -> ScheduledJobResponse:
    job = marketing_repository.update_scheduled_job_status(job_id, "pending")
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")
    return job


@app.post("/api/marketing/jobs/{job_id}/dispatch-now", response_model=DeliveryLogResponse)
async def dispatch_campaign_job(
    job_id: str,
    payload: DispatchJobRequest,
    _: AuthDep,
    __: RateDep,
) -> DeliveryLogResponse:
    log = marketing_delivery_service.dispatch_job(job_id, execution_mode=payload.execution_mode)
    if not log:
        raise HTTPException(status_code=404, detail="Scheduled job not found or dispatch failed before logging")
    return log


@app.get("/api/marketing/delivery-logs", response_model=list[DeliveryLogResponse])
async def list_delivery_logs(_: AuthDep, __: RateDep, platform: str | None = None) -> list[DeliveryLogResponse]:
    return marketing_repository.list_delivery_logs(platform=platform)


@app.get("/api/marketing/platform-health", response_model=list[PlatformAdapterStatusResponse])
async def get_platform_health(_: AuthDep, __: RateDep) -> list[PlatformAdapterStatusResponse]:
    return marketing_delivery_service.platform_statuses()


@app.get("/api/marketing/channel-credentials", response_model=list[ChannelCredentialResponse])
async def list_channel_credentials(_: AuthDep, __: RateDep) -> list[ChannelCredentialResponse]:
    return marketing_credential_service.list_credentials()


@app.post("/api/marketing/channel-credentials", response_model=ChannelCredentialResponse)
async def upsert_channel_credentials(
    payload: UpsertChannelCredentialRequest,
    _: AuthDep,
    __: RateDep,
) -> ChannelCredentialResponse:
    return marketing_credential_service.save(payload)


@app.post("/api/marketing/performance-events", response_model=PerformanceEventResponse)
async def record_performance_event(
    payload: RecordPerformanceEventRequest,
    _: AuthDep,
    __: RateDep,
) -> PerformanceEventResponse:
    campaign = marketing_repository.get_campaign(payload.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return marketing_analytics_service.record_event(payload)


@app.get("/api/marketing/analytics/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    _: AuthDep,
    __: RateDep,
    campaign_id: str | None = None,
) -> AnalyticsSummaryResponse:
    return marketing_analytics_service.summary(campaign_id=campaign_id)


@app.get("/api/marketing/analytics/campaigns/{campaign_id}", response_model=AnalyticsSummaryResponse)
async def get_campaign_analytics(campaign_id: str, _: AuthDep, __: RateDep) -> AnalyticsSummaryResponse:
    campaign = marketing_repository.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return marketing_analytics_service.summary(campaign_id=campaign_id)


@app.post("/api/marketing/optimize", response_model=OptimizationSummaryResponse)
async def optimize_marketing(_: AuthDep, __: RateDep, campaign_id: str | None = None) -> OptimizationSummaryResponse:
    if campaign_id:
        campaign = marketing_repository.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
    return marketing_optimization_service.optimize(campaign_id=campaign_id)


@app.post("/api/marketing/optimize/campaigns/{campaign_id}", response_model=OptimizationSummaryResponse)
async def optimize_campaign(campaign_id: str, _: AuthDep, __: RateDep) -> OptimizationSummaryResponse:
    campaign = marketing_repository.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return marketing_optimization_service.optimize(campaign_id=campaign_id)


@app.get("/api/smart-parks/dashboard", response_model=DashboardBundleResponse)
async def get_smart_parks_dashboard(_: AuthDep, __: RateDep) -> DashboardBundleResponse:
    return smart_parks_repository.dashboard_bundle()


@app.get("/api/smart-parks/summary", response_model=DashboardSummaryResponse)
async def get_smart_parks_summary(_: AuthDep, __: RateDep) -> DashboardSummaryResponse:
    return smart_parks_repository.dashboard_summary()


@app.get("/api/smart-parks/parks", response_model=list[ParkResponse])
async def list_smart_parks(_: AuthDep, __: RateDep) -> list[ParkResponse]:
    return smart_parks_repository.list_parks()


@app.get("/api/smart-parks/parks/{park_id}", response_model=ParkResponse)
async def get_smart_park(park_id: str, _: AuthDep, __: RateDep) -> ParkResponse:
    park = smart_parks_repository.get_park(park_id)
    if not park:
        raise HTTPException(status_code=404, detail="Park not found")
    return park


@app.get("/api/smart-parks/zones", response_model=list[ZoneResponse])
async def list_smart_park_zones(_: AuthDep, __: RateDep, park_id: str | None = None) -> list[ZoneResponse]:
    return smart_parks_repository.list_zones(park_id=park_id)


@app.get("/api/smart-parks/devices", response_model=list[DeviceResponse])
async def list_smart_park_devices(_: AuthDep, __: RateDep, park_id: str | None = None) -> list[DeviceResponse]:
    return smart_parks_repository.list_devices(park_id=park_id)


@app.post("/api/smart-parks/devices", response_model=DeviceResponse)
async def register_smart_park_device(payload: RegisterDeviceRequest, _: AuthDep, __: RateDep) -> DeviceResponse:
    return smart_parks_repository.register_device(payload)


@app.get("/api/smart-parks/readings", response_model=list[ReadingResponse])
async def list_smart_park_readings(
    _: AuthDep,
    __: RateDep,
    park_id: str | None = None,
    device_id: str | None = None,
    limit: int = 100,
) -> list[ReadingResponse]:
    return smart_parks_repository.list_readings(park_id=park_id, device_id=device_id, limit=limit)


@app.post("/api/smart-parks/readings/ingest", response_model=IngestReadingsResponse)
async def ingest_smart_park_readings(payload: IngestReadingsRequest, _: AuthDep, __: RateDep) -> IngestReadingsResponse:
    return smart_parks_repository.ingest_readings(payload)


@app.post("/api/smart-parks/simulate", response_model=SimulationResponse)
async def simulate_smart_parks(payload: SimulationRequest, _: AuthDep, __: RateDep) -> SimulationResponse:
    return smart_parks_repository.run_simulation(ticks=payload.ticks, park_id=payload.park_id)


@app.get("/api/smart-parks/thresholds", response_model=list[ThresholdEntryResponse])
async def list_smart_park_thresholds(_: AuthDep, __: RateDep) -> list[ThresholdEntryResponse]:
    return smart_parks_repository.list_thresholds()


@app.get("/api/smart-parks/hardware-contract", response_model=HardwareContractResponse)
async def get_smart_park_hardware_contract(_: AuthDep, __: RateDep) -> HardwareContractResponse:
    return HardwareContractResponse(
        ingestion_endpoint="/api/smart-parks/readings/ingest",
        simulation_endpoint="/api/smart-parks/simulate",
        supported_connectivity=["lorawan", "nbiot", "simulator", "manual"],
        expected_payload_shape={
            "readings": [
                {
                    "device_id": "device-uuid-or-slug",
                    "metric_key": "soil_moisture_pct",
                    "metric_value": 28.4,
                    "unit": "%",
                    "recorded_at": "2026-04-13T18:00:00Z",
                    "source": "hardware",
                    "metadata": {"gateway_id": "gw-01"},
                }
            ]
        },
        notes=[
            "One request can contain batched readings from a gateway uplink.",
            "Unknown device_ids are ignored rather than failing the full batch.",
            "Threshold breaches automatically create alerts, and critical breaches also create work orders.",
        ],
    )


@app.get("/api/smart-parks/alerts", response_model=list[SmartParkAlertResponse])
async def list_smart_park_alerts(
    _: AuthDep,
    __: RateDep,
    status: str | None = None,
    park_id: str | None = None,
) -> list[SmartParkAlertResponse]:
    return smart_parks_repository.list_alerts(status=status, park_id=park_id)


@app.post("/api/smart-parks/alerts/{alert_id}/acknowledge", response_model=SmartParkAlertResponse)
async def acknowledge_smart_park_alert(alert_id: str, _: AuthDep, __: RateDep) -> SmartParkAlertResponse:
    alert = smart_parks_repository.acknowledge_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@app.post("/api/smart-parks/alerts/{alert_id}/resolve", response_model=SmartParkAlertResponse)
async def resolve_smart_park_alert(alert_id: str, _: AuthDep, __: RateDep) -> SmartParkAlertResponse:
    alert = smart_parks_repository.resolve_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@app.get("/api/smart-parks/work-orders", response_model=list[WorkOrderResponse])
async def list_smart_park_work_orders(
    _: AuthDep,
    __: RateDep,
    status: str | None = None,
    park_id: str | None = None,
) -> list[WorkOrderResponse]:
    return smart_parks_repository.list_work_orders(status=status, park_id=park_id)


@app.post("/api/smart-parks/work-orders", response_model=WorkOrderResponse)
async def create_smart_park_work_order(
    payload: CreateWorkOrderRequest,
    _: AuthDep,
    __: RateDep,
) -> WorkOrderResponse:
    return smart_parks_repository.create_work_order(payload)


@app.patch("/api/smart-parks/work-orders/{work_order_id}", response_model=WorkOrderResponse)
async def update_smart_park_work_order(
    work_order_id: str,
    payload: UpdateWorkOrderRequest,
    _: AuthDep,
    __: RateDep,
) -> WorkOrderResponse:
    work_order = smart_parks_repository.update_work_order(work_order_id, payload)
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")
    return work_order


@app.get("/api/smart-parks/park-risks", response_model=list[ParkRiskSummaryResponse])
async def get_smart_park_risks(_: AuthDep, __: RateDep) -> list[ParkRiskSummaryResponse]:
    return smart_parks_repository.park_risk_summary()


@app.get("/api/smart-parks/reports/overview", response_model=ReportsOverviewResponse)
async def get_smart_park_report(_: AuthDep, __: RateDep) -> ReportsOverviewResponse:
    return smart_parks_repository.reports_overview()


@app.get("/api/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    return StatusResponse(status="online", model_version=model_service.active_version, supabase_connected=repository.connected)


@app.get("/api/v1/status")
async def status_v1():
    # Parity with app.py
    return {
        "status": "online",
        "version": "beta 1.1.0-fastapi",
        "provider": "HELIX-HYBRID",
        "network": "online",
        "edge_engine": "warm",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/diagnostics")
async def system_diagnostics():
    """FORENSIC v1: Full system health check."""
    import psutil
    bin_path = Path(settings.root_dir) / "helix_backend" / "edge_model" / "llama-server.exe"
    
    return {
        "timestamp": datetime.now().isoformat(),
        "env": {
            "GROQ_KEY_PRESENT": bool(settings.groq_api_key),
            "SUPABASE_URL_PRESENT": bool(settings.supabase_url),
            "PORT": 8000
        },
        "engine": {
            "binary_exists": bin_path.exists(),
            "binary_path": str(bin_path),
            "model_exists": True, # Assume True if initialized
        },
        "system": {
            "ram_free_mb": int(psutil.virtual_memory().available / (1024*1024)),
            "cpu_count": os.cpu_count()
        }
    }


@app.get("/api/users/{user_id}/profile", response_model=PersonalityProfile)
async def get_profile(user_id: str, _: AuthDep, __: RateDep) -> PersonalityProfile:
    profile = repository.get_user_profile(user_id)
    return repository.upsert_user_profile(profile)


@app.put("/api/users/{user_id}/profile", response_model=PersonalityProfile)
async def update_profile(user_id: str, payload: PersonalityProfile, _: AuthDep, __: RateDep) -> PersonalityProfile:
    updated = payload.model_copy(update={"user_id": user_id})
    return repository.upsert_user_profile(updated)


@app.get("/api/users/{user_id}/history")
async def get_history(user_id: str, _: AuthDep, __: RateDep):
    return {"items": [record.model_dump() for record in repository.list_recent_interactions(user_id)]}


@app.post("/api/chat")
async def chat(request: ChatRequest, _: AuthDep, __: RateDep):
    # Always use server-side profile — no manual overrides from frontend
    profile = repository.get_user_profile(request.user_id)

    # Auto-infer profile adjustments from the current message
    profile = infer_profile_from_message(profile, request.message)
    profile = repository.upsert_user_profile(profile)

    versions = repository.list_model_versions()
    retrieved = retrieval_service.retrieve_successful_examples(request.user_id, request.message)
    model_version, _ = model_service.choose_ab_bucket(versions)
    prompt = build_conditioned_prompt(
        request.message,
        profile,
        request.history,
        retrieved,
        model_version,
        request.personality,
    )
    response_text, backend = model_service.generate_response(
        prompt=prompt,
        message=request.message,
        history=request.history,
        personality=request.personality,
        mode=request.mode,
        privacy_mode=request.privacy_mode,
        force_offline=request.force_offline,
    )
    metadata = {
        "model_version": model_version,
        "personality": request.personality,
        "generation_backend": backend,
        "selected_mode": request.mode,
    }
    interaction = repository.create_interaction(request.user_id, request.message, response_text, metadata["model_version"], metadata)
    repository.store_embedding(interaction.id, request.user_id, embedding_preprocessor._hash_embedding(request.message), request.message)

    logger.info(f"[Chat] user={request.user_id} personality={request.personality} backend={metadata['generation_backend']}")

    return {
        "interaction_id": interaction.id,
        "response": response_text,
        "model_version": metadata["model_version"],
        "system_label": "Adapting to your preferences",
        "profile": profile.model_dump(),
        "metadata": metadata,
    }


@app.post("/api/chat/stream")
async def stream_chat(request: ChatRequest, _: AuthDep, __: RateDep):
    # Always use server-side profile — no manual overrides
    profile = repository.get_user_profile(request.user_id)

    # Auto-infer profile adjustments from the current message
    profile = infer_profile_from_message(profile, request.message)
    profile = repository.upsert_user_profile(profile)

    versions = repository.list_model_versions()
    retrieved = retrieval_service.retrieve_successful_examples(request.user_id, request.message)
    response_state, metadata, iterator = await model_service.stream_response(
        user_id=request.user_id,
        message=request.message,
        profile=profile,
        history=request.history,
        retrieved_examples=retrieved,
        versions=versions,
        personality=request.personality,
        mode=request.mode,
        privacy_mode=request.privacy_mode,
        force_offline=request.force_offline,
    )

    async def stream():
        async for item in iterator:
            yield f"data: {item.strip()}\n\n"
        final_response = response_state["text"]
        interaction = repository.create_interaction(request.user_id, request.message, final_response, metadata["model_version"], metadata)
        repository.store_embedding(interaction.id, request.user_id, embedding_preprocessor._hash_embedding(request.message), request.message)
        logger.info(f"[StreamChat] user={request.user_id} personality={request.personality} backend={metadata['generation_backend']}")
        final_payload = {
            "type": "done",
            "interaction_id": interaction.id,
            "response": final_response,
            "system_label": "Adapting to your preferences",
            "profile": profile.model_dump(),
            "metadata": metadata,
        }
        yield f"data: {json.dumps(final_payload)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, _: AuthDep, __: RateDep):
    reward = feedback_reward(request.vote, request.tags)
    repository.add_feedback(request, reward)
    current = repository.get_user_profile(request.user_id)
    updated = update_profile_from_feedback(current, request)
    repository.upsert_user_profile(updated)
    return FeedbackResponse(reward=reward, updated_profile=updated)


@app.post("/api/training/run", response_model=TrainingRunResponse)
async def trigger_training(request: TrainingRunRequest, background_tasks: BackgroundTasks, _: AuthDep, __: RateDep):
    background_tasks.add_task(training_service.run_batch, request.version_label, request.batch_limit)
    return TrainingRunResponse(accepted=True, message="Offline RLHF batch accepted")


@app.get("/api/model/versions")
async def get_versions(_: AuthDep, __: RateDep):
    return {"items": repository.list_model_versions()}


@app.post("/api/users/{user_id}/clear")
async def clear_history(user_id: str, _: AuthDep, __: RateDep):
    repository.clear_history(user_id)
    return {"status": "success"}
