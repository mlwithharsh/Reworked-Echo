from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


CampaignStatus = Literal["draft", "ready", "scheduled", "running", "completed", "archived"]
ApprovalStatus = Literal["pending", "approved", "rejected"]
JobStatus = Literal["pending", "queued", "running", "completed", "failed", "paused", "cancelled"]
ExecutionMode = Literal["live", "dry_run"]


class BrandProfileBase(BaseModel):
    brand_name: str
    voice_style: str = ""
    preferred_vocabulary: list[str] = Field(default_factory=list)
    banned_phrases: list[str] = Field(default_factory=list)
    signature_patterns: list[str] = Field(default_factory=list)
    default_cta_style: str = ""
    audience_notes: str = ""
    positioning: str = ""


class CreateBrandProfileRequest(BrandProfileBase):
    pass


class UpdateBrandProfileRequest(BaseModel):
    brand_name: str | None = None
    voice_style: str | None = None
    preferred_vocabulary: list[str] | None = None
    banned_phrases: list[str] | None = None
    signature_patterns: list[str] | None = None
    default_cta_style: str | None = None
    audience_notes: str | None = None
    positioning: str | None = None


class BrandProfileResponse(BrandProfileBase):
    id: str
    created_at: datetime
    updated_at: datetime


class CampaignBase(BaseModel):
    name: str
    goal: str
    target_audience: str = ""
    brand_profile_id: str | None = None
    brand_voice: str = ""
    offer_summary: str = ""
    strategy_summary: str = ""
    content_mix: dict[str, float] = Field(default_factory=dict)
    posting_frequency: str = ""
    status: CampaignStatus = "draft"


class CreateCampaignRequest(CampaignBase):
    pass


class UpdateCampaignRequest(BaseModel):
    name: str | None = None
    goal: str | None = None
    target_audience: str | None = None
    brand_profile_id: str | None = None
    brand_voice: str | None = None
    offer_summary: str | None = None
    strategy_summary: str | None = None
    content_mix: dict[str, float] | None = None
    posting_frequency: str | None = None
    status: CampaignStatus | None = None


class CampaignResponse(CampaignBase):
    id: str
    created_at: datetime
    updated_at: datetime


class StrategyRequest(BaseModel):
    goal: str
    target_audience: str = ""
    offer_summary: str = ""
    brand_voice: str = ""
    preferred_platforms: list[str] = Field(default_factory=list)
    autonomous_mode: bool = False


class StrategyResponse(BaseModel):
    campaign_goal: str
    inferred_intent: str
    primary_platforms: list[str] = Field(default_factory=list)
    content_mix: dict[str, float] = Field(default_factory=dict)
    posting_frequency: str
    timing_hypothesis: str
    tone_direction: str
    cta_direction: str
    experiment_ideas: list[str] = Field(default_factory=list)
    strategy_summary: str


class PromptBuildRequest(BaseModel):
    platform: str
    campaign_goal: str
    target_audience: str = ""
    offer_summary: str = ""
    brand_voice: str = ""
    desired_tone: str = ""
    cta_style: str = ""
    experiment_label: str = "A"
    performance_hints: list[str] = Field(default_factory=list)
    preferred_vocabulary: list[str] = Field(default_factory=list)
    banned_phrases: list[str] = Field(default_factory=list)
    signature_patterns: list[str] = Field(default_factory=list)
    extra_context: list[str] = Field(default_factory=list)


class PromptBuildResponse(BaseModel):
    platform: str
    system_prompt: str
    user_prompt: str
    output_contract: dict[str, Any] = Field(default_factory=dict)
    generation_params: dict[str, Any] = Field(default_factory=dict)


class GeneratedVariantDraft(BaseModel):
    platform: str
    variant_name: str
    headline: str = ""
    body: str
    cta: str = ""
    hashtags: list[str] = Field(default_factory=list)
    reasoning_tags: list[str] = Field(default_factory=list)
    experiment_label: str = "A"


class CampaignVariantResponse(BaseModel):
    id: str
    campaign_id: str
    platform: str
    variant_name: str
    prompt_snapshot: str = ""
    generated_text: str = ""
    cta: str = ""
    hashtags: list[str] = Field(default_factory=list)
    score: float = 0
    experiment_group: str = ""
    approval_status: ApprovalStatus = "pending"
    created_at: datetime


class GenerateVariantsRequest(BaseModel):
    platforms: list[str] = Field(default_factory=list)
    experiment_labels: list[str] = Field(default_factory=lambda: ["A"])
    desired_tone: str = ""
    cta_style: str = ""
    performance_hints: list[str] = Field(default_factory=list)
    extra_context: list[str] = Field(default_factory=list)


class GenerateVariantsResponse(BaseModel):
    campaign: CampaignResponse
    strategy: StrategyResponse
    variants: list[CampaignVariantResponse] = Field(default_factory=list)


class ApproveVariantRequest(BaseModel):
    approved: bool
    notes: str = ""


class ApprovalResultResponse(BaseModel):
    variant: CampaignVariantResponse
    safe_to_schedule: bool
    reasons: list[str] = Field(default_factory=list)


class TemplateResponse(BaseModel):
    id: str
    name: str
    category: str = ""
    platform: str = ""
    template_text: str
    tone: str = ""
    cta_style: str = ""
    score: float = 0
    created_at: datetime


class ScheduledJobResponse(BaseModel):
    id: str
    campaign_id: str
    variant_id: str
    platform: str
    run_at: datetime
    timezone: str
    status: JobStatus
    retry_count: int = 0
    last_error: str = ""
    created_at: datetime


class ScheduleCampaignRequest(BaseModel):
    variant_ids: list[str]
    run_at: datetime
    timezone: str = "UTC"


class ScheduleCampaignResponse(BaseModel):
    jobs: list[ScheduledJobResponse] = Field(default_factory=list)
    rejected_variant_ids: list[str] = Field(default_factory=list)


class DeliveryLogResponse(BaseModel):
    id: str
    job_id: str
    platform: str
    request_payload: dict[str, Any] = Field(default_factory=dict)
    response_payload: dict[str, Any] = Field(default_factory=dict)
    status: str
    external_post_id: str = ""
    execution_mode: ExecutionMode = "dry_run"
    created_at: datetime


class DispatchJobRequest(BaseModel):
    execution_mode: ExecutionMode = "dry_run"


class RecordPerformanceEventRequest(BaseModel):
    campaign_id: str
    variant_id: str | None = None
    platform: str
    metric_type: str
    metric_value: float
    source: str = "manual"
    note: str = ""


class PerformanceEventResponse(BaseModel):
    id: str
    campaign_id: str
    variant_id: str | None = None
    platform: str
    metric_type: str
    metric_value: float
    source: str = "manual"
    note: str = ""
    created_at: datetime


class AnalyticsSummaryResponse(BaseModel):
    campaign_id: str | None = None
    total_events: int = 0
    platform_scores: dict[str, float] = Field(default_factory=dict)
    metric_averages: dict[str, float] = Field(default_factory=dict)
    memory_hints: list[str] = Field(default_factory=list)


class OptimizationSummaryResponse(BaseModel):
    campaign_id: str | None = None
    top_platform: str
    recommended_cta_style: str
    recommended_posting_window: str
    prompt_bias_hints: list[str] = Field(default_factory=list)
    updated_variant_ids: list[str] = Field(default_factory=list)
    analytics_summary: AnalyticsSummaryResponse


class ExperimentRunResponse(BaseModel):
    id: str
    campaign_id: str
    variant_a_id: str
    variant_b_id: str
    winner_variant_id: str | None = None
    decision_reason: str = ""
    created_at: datetime
