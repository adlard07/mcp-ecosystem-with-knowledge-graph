from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from utils.utils import random_uuid


class PreferencesModel(BaseModel):
    categories_of_interest: List[str]
    notification_frequency: str
    language: str
    timezone: str


class AuthConfigModel(BaseModel):
    token_url: Optional[str] = None
    scopes: Optional[List[str]] = None
    header_name: Optional[str] = None


class AuthModel(BaseModel):
    type: str
    config: Optional[AuthConfigModel] = None


class InfrastructureModel(BaseModel):
    provider: str
    service: str
    region: str


class MilestoneModel(BaseModel):
    label: str
    target: float
    reached_at: Optional[str] = None


class StepModel(BaseModel):
    order: int
    server_id: str
    tool_id: str
    tool_name: str
    label: str
    input_mapping: Dict


# User


class UserModel(BaseModel):
    user_id: str = Field(default_factory=random_uuid)
    name: str
    age: int
    email: str
    password_hash: str

    gender: str
    career_status: str
    role: str

    active_goal_ids: List[str]

    preferences: PreferencesModel

    onboarding_complete: bool

    last_active_at: str
    created_at: str
    updated_at: str


# Server


class ServerModel(BaseModel):
    server_id: str = Field(default_factory=random_uuid)
    publisher_id: str

    name: str
    description: Optional[str] = None

    category: str
    tags: List[str]

    transport: str

    url: str
    health_check_url: str

    host: str
    port: int

    system_prompt: Optional[str] = None

    status: str

    auth: AuthModel
    infrastructure: InfrastructureModel

    mcp_protocol_version: str
    server_version: str

    popularity_score: float

    total_connections: int
    avg_rating: float

    is_verified: bool
    is_featured: bool

    created_at: str
    updated_at: str


# Server Stats


class ServerStatsModel(BaseModel):
    server_id: str = Field(default_factory=random_uuid)

    total_invocations_24h: int
    total_invocations_7d: int
    total_invocations_30d: int

    error_rate_24h: float

    avg_latency_ms: float
    p99_latency_ms: float

    unique_users_7d: int

    uptime_pct_30d: float

    last_health_check: str
    updated_at: str


# Tool


class ToolSchemaModel(BaseModel):
    type: str
    properties: Dict
    required: Optional[List[str]] = None


class ToolModel(BaseModel):
    tool_id: str = Field(default_factory=random_uuid)
    server_id: str

    name: str
    description: str

    input_schema: ToolSchemaModel
    output_schema: ToolSchemaModel

    category: str
    tags: List[str]

    is_deprecated: bool

    invocation_count: int
    avg_latency_ms: float

    created_at: str
    updated_at: str


# Goal


class GoalModel(BaseModel):
    goal_id: str = Field(default_factory=random_uuid)
    user_id: str

    template_id: Optional[str] = None

    title: str
    description: str

    goal_type: str

    target_value: float
    current_value: float

    unit: str

    progress_pct: float

    deadline: str

    priority: int

    status: str

    milestones: List[MilestoneModel]

    linked_tool_ids: List[str]
    linked_server_ids: List[str]

    created_at: str
    updated_at: str


# Connection


class ConnectionModel(BaseModel):
    connection_id: str = Field(default_factory=random_uuid)
    user_id: str
    server_id: str

    server_name: str

    status: str

    auth_token_ref: str

    permissions_granted: List[str]

    tools_enabled: List[str]
    tools_disabled: List[str]

    connected_at: str
    last_used_at: str

    total_invocations: int

    updated_at: str


# Tool Usage
# =========================================================


class ToolUsageModel(BaseModel):
    usage_id: str = Field(default_factory=random_uuid)
    user_id: str
    server_id: str
    tool_id: str

    tool_name: str

    invocation_id: str

    input_summary: str
    output_summary: str

    status: str

    latency_ms: int

    error_code: Optional[str] = None

    session_id: str

    goal_context: Optional[str] = None

    created_at: str


# Pattern


class PatternModel(BaseModel):
    pattern_id: str = Field(default_factory=random_uuid)
    user_id: str

    pattern_type: str

    confidence: float

    data: Dict

    sample_size: int

    last_computed_at: str

    created_at: str
    updated_at: str


# Feedback


class FeedbackModel(BaseModel):
    feedback_id: str = Field(default_factory=random_uuid)
    user_id: str

    target_type: str
    target_id: str

    rating: int

    review: Optional[str] = None

    tags: List[str]

    is_public: bool

    created_at: str
    updated_at: str


# Recommendation


class RecommendationModel(BaseModel):
    rec_id: str = Field(default_factory=random_uuid)

    user_id: str

    rec_type: str

    target_id: str

    title: str
    description: str

    reason_codes: List[str]

    score: float

    source_algorithm: str

    goal_context: Optional[str] = None

    is_seen: bool
    is_dismissed: bool
    is_acted_on: bool

    acted_on_at: Optional[str] = None

    expires_at: str

    created_at: str


# Workflow


class WorkflowModel(BaseModel):
    workflow_id: str = Field(default_factory=random_uuid)

    title: str
    description: str

    steps: List[StepModel]

    category: str

    goal_types: List[str]

    is_system: bool

    creator_id: Optional[str] = None

    usage_count: int

    avg_rating: float

    created_at: str
    updated_at: str


# Category


class CategoryModel(BaseModel):
    category_id: str = Field(default_factory=random_uuid)
    slug: str

    label: str

    description: str

    icon: str

    parent_category: Optional[str] = None

    server_count: int
    tool_count: int

    is_active: bool

    display_order: int

    created_at: str
    updated_at: str
