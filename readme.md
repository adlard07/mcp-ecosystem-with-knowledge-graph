# MCP-Native Personal Ecosystem Platform with Knowledge Graph Intelligence

An intelligent, context-aware personal management platform that unifies daily-use applications through Model Context Protocol (MCP) and graph-based reasoning. Built for working professionals to track their career, expenses, diet plans, plan travel, personal growth, many more.

---

## 🎯 Vision

Traditional productivity apps operate in silos—your calendar doesn't know your budget, your fitness tracker doesn't understand your work stress, and your meal planner can't see your schedule. This platform breaks those walls by creating an **intelligent ecosystem** where all your apps communicate through a unified knowledge graph, enabling proactive insights and context-aware automations.

**Example Intelligence:**

```
Query: "Should I go to the office tomorrow?"

Knowledge Graph Reasoning:
├─ Calendar: 3 meetings scheduled (2 can be remote)
├─ Weather: Heavy rain forecasted + monsoon advisory
├─ Commute: 2.5hr round trip in rain vs 0hr WFH
├─ Health: Sleep quality was poor (6hrs vs target 7.5hrs)
├─ Productivity: Home productivity 15% higher on low-sleep days
└─ Recommendation: WFH + suggest rescheduling in-person meeting

Confidence: 87% | Time saved: 2.5hrs | Energy saved: High
```

---

## ✨ Key Features

### 🧠 **Intelligent Context Synthesis**

- Cross-application reasoning across data domains
- Multi-hop knowledge graph traversal
- Real-time pattern recognition and anomaly detection
<!-- - Proactive suggestion engine with 85%+ acceptance rate -->

### 📊 **Core Applications**

X

### 🔗 **Advanced Integrations**

- **Smart Notifications**: Cross-app intelligence triggers (e.g., "Meeting + Rain → Leave early + Umbrella")
- **Mumbai-Specific**: Local transport optimization, monsoon awareness, AQI tracking
- **Natural Language Interface**: LLM-powered assistant with full context access via MCP

---

## 🏗️ Architecture

---

## 🔬 Knowledge Graph Schema

### Nodes
```python
user = {
    "user_id": str,                # "u_abc123" — nanoid or uuid
    "name": str,
    "age": int,
    "email": str,
    "password_hash": str,          # bcrypt hash, never store plaintext
    "gender": str,                 # "male", "female", "non_binary", "prefer_not_to_say"
    "career_status": str,          # "working", "student", "freelancer", "retired", "non_working"
    "role": str,                   # "admin", "developer", "consumer"
    "active_goal_ids": list[str],  # ["g_001", "g_002"] — current goals
    "preferences": {
        "categories_of_interest": list[str],  # ["finance", "health", "productivity"]
        "notification_frequency": str,        # "realtime", "daily", "weekly", "off"
        "language": str,                      # "en", "hi", "mr"
        "timezone": str,                      # "Asia/Kolkata"
    },
    "onboarding_complete": bool,
    "last_active_at": str,         # ISO 8601
    "created_at": str,
    "updated_at": str,
}

server = {
    "server_id": str,              # "s_xyz789"
    "publisher_id": str,           # user_id of who registered this server
    "name": str,
    "description": str,
    "category": str,               # primary category slug — "finance", "health"
    "tags": list[str],             # ["budgeting", "investing", "expense-tracker"]
    "transport": str,              # "sse", "stdio", "streamable_http"
    "url": str,                    # full MCP endpoint — "https://finbot.example.com/mcp/sse"
    "health_check_url": str,       # "https://finbot.example.com/health"
    "host": str,                   # "finbot.example.com"
    "port": int,                   # 443
    "system_prompt": str,          # default system prompt for this server's tools
    "status": str,                 # "active", "degraded", "offline", "deprecated"
    "auth": {
        "type": str,               # "none", "api_key", "oauth2", "bearer"
        "config": {
            "token_url": str,      # oauth2 token endpoint
            "scopes": list[str],   # ["read", "write"]
            "header_name": str,    # for api_key — "X-API-Key"
        },
    },
    "infrastructure": {
        "provider": str,           # "aws", "gcp", "azure", "self_hosted"
        "service": str,            # "ecs_fargate", "ec2", "cloud_run", "gke"
        "region": str,             # "ap-south-1"
    },
    "mcp_protocol_version": str,   # "2025-03-26"
    "server_version": str,         # semver — "1.2.0"
    "popularity_score": float,     # computed — 0.0 to 100.0
    "total_connections": int,      # denormalized count
    "avg_rating": float,           # denormalized — 0.0 to 5.0
    "is_verified": bool,           # manually verified by platform admins
    "is_featured": bool,           # promoted in discovery
    "created_at": str,
    "updated_at": str,
}

server_stats = {
    "server_id": str,
    "total_invocations_24h": int,
    "total_invocations_7d": int,
    "total_invocations_30d": int,
    "error_rate_24h": float,       # 0.0 to 1.0
    "avg_latency_ms": float,
    "p99_latency_ms": float,
    "unique_users_7d": int,
    "uptime_pct_30d": float,       # 99.7
    "last_health_check": str,      # ISO 8601
    "updated_at": str,
}

tool = {
    "tool_id": str,                # "t_budget01"
    "server_id": str,
    "name": str,                   # MCP tool name — "create_budget"
    "description": str,            # human-readable description for discovery
    "input_schema": {              # JSON Schema for tool input
        "type": str,               # "object"
        "properties": dict,
        "required": list[str],
    },
    "output_schema": {             # JSON Schema for tool output
        "type": str,
        "properties": dict,
    },
    "category": str,               # inherits or overrides server category
    "tags": list[str],
    "is_deprecated": bool,
    "invocation_count": int,       # denormalized — updated via atomic counters
    "avg_latency_ms": float,
    "created_at": str,
    "updated_at": str,
}

goal = {
    "goal_id": str,                # "g_001"
    "user_id": str,
    "template_id": str,            # nullable — "gt_save_emergency_fund" if from template
    "title": str,
    "description": str,
    "goal_type": str,              # "financial", "health", "career", "education", productivity"
    "target_value": float,         # 300000
    "current_value": float,        # 125000
    "unit": str,                   # "INR", "kg", "hours", "count"
    "progress_pct": float,         # computed — 41.7
    "deadline": str,               # ISO 8601
    "priority": int,               # 1 = highest
    "status": str,                 # "not_started", "in_progress", "completed", "abandoned"
    "milestones": [
        {
            "label": str,          # "₹1L saved"
            "target": float,       # 100000
            "reached_at": str,     # ISO 8601 or null
        },
    ],
    "linked_tool_ids": list[str],  # tools actively helping this goal
    "linked_server_ids": list[str],
    "created_at": str,
    "updated_at": str,
}

connection = {
    "user_id": str,
    "server_id": str,
    "server_name": str,            # denormalized for display without extra fetch
    "status": str,                 # "active", "paused", "revoked"
    "auth_token_ref": str,         # SSM/Secrets Manager path — never store raw tokens
    "permissions_granted": list[str],  # ["read", "write", "admin"]
    "tools_enabled": list[str],    # tool_ids the user has turned on
    "tools_disabled": list[str],   # tool_ids the user explicitly turned off
    "connected_at": str,           # ISO 8601 — when first connected
    "last_used_at": str,           # ISO 8601 — last tool invocation via this connection
    "total_invocations": int,      # lifetime count through this connection
    "updated_at": str,
}

tool_usage = {
    "user_id": str,
    "server_id": str,
    "tool_id": str,
    "tool_name": str,              # denormalized — "create_budget"
    "invocation_id": str,          # unique per call — "inv_998877"
    "input_summary": str,          # truncated/redacted input for pattern mining
    "output_summary": str,         # truncated/redacted output
    "status": str,                 # "success", "error", "timeout"
    "latency_ms": int,
    "error_code": str,             # nullable — "RATE_LIMITED", "AUTH_EXPIRED", "TIMEOUT"
    "session_id": str,             # groups tool calls within a single user session
    "goal_context": str,           # nullable — which goal this invocation was serving
    "created_at": str,
}

pattern = {
    "user_id": str,
    "pattern_type": str,           # see pattern_types below
    "confidence": float,           # 0.0 to 1.0 — how reliable this pattern is
    "data": dict,                  # shape varies by pattern_type — see examples below
    "sample_size": int,            # number of events this pattern was computed from
    "last_computed_at": str,
    "created_at": str,
    "updated_at": str,
}

feedback = {
    "user_id": str,
    "target_type": str,            # "server" or "tool"
    "target_id": str,              # server_id or tool_id
    "rating": int,                 # 1 to 5
    "review": str,                 # nullable — free text
    "tags": list[str],             # ["useful", "buggy", "fast", "needs-more-tools"]
    "is_public": bool,             # visible to other users
    "created_at": str,
    "updated_at": str,
}

recommendation = {
    "rec_id": str,                 # "rec_445566"
    "user_id": str,
    "rec_type": str,               # "server", "tool", "workflow", "goal_template"
    "target_id": str,              # id of the recommended entity
    "title": str,                  # display title
    "description": str,            # why this is recommended — human readable
    "reason_codes": list[str],     # machine-readable — ["goal_alignment", "category_match"]
    "score": float,                # 0.0 to 1.0 — recommendation confidence
    "source_algorithm": str,       # "rule_based_v1", "collaborative_filtering_v2"
    "goal_context": str,           # nullable — which goal triggered this rec
    "is_seen": bool,
    "is_dismissed": bool,          # user explicitly dismissed
    "is_acted_on": bool,           # user clicked through / connected
    "acted_on_at": str,            # nullable — ISO 8601
    "expires_at": str,             # ISO 8601 — stale after this
    "created_at": str,
}

workflow = {
    "workflow_id": str,            # "wf_monthly_finance"
    "title": str,
    "description": str,
    "steps": [
        {
            "order": int,          # execution order — 1, 2, 3...
            "server_id": str,
            "tool_id": str,
            "tool_name": str,      # denormalized
            "label": str,          # human-readable step label
            "input_mapping": dict,  # how output of step N maps to input of step N+1
        },
    ],
    "category": str,
    "goal_types": list[str],       # which goal types this workflow supports
    "is_system": bool,             # true = platform-curated, false = user-created
    "creator_id": str,             # nullable — user_id if user-created
    "usage_count": int,
    "avg_rating": float,
    "created_at": str,
    "updated_at": str,
}

category = {
    "slug": str,                   # "finance", "health", "productivity"
    "label": str,                  # "Finance & Money"
    "description": str,
    "icon": str,                   # emoji or icon key — "💰"
    "parent_category": str,        # nullable — for subcategories ("investing" → "finance")
    "server_count": int,           # denormalized
    "tool_count": int,             # denormalized
    "is_active": bool,
    "display_order": int,          # for UI sorting
    "created_at": str,
    "updated_at": str,
}

# pattern_usage_rhythm = {
#     "peak_hours": list[int],           # [9, 10, 21, 22]
#     "peak_days": list[str],            # ["monday", "wednesday"]
#     "avg_session_duration_min": float,  # 12.5
#     "avg_tools_per_session": float,     # 3.2
#     "sessions_per_week": float,         # 4.1
# }

# pattern_tool_affinity = {
#     "top_tools": [                     # ranked by usage
#         {
#             "tool_id": str,
#             "tool_name": str,
#             "server_id": str,
#             "invocation_count": int,
#             "last_used_at": str,
#         },
#     ],
#     "co_occurrence": [                 # tools frequently used together in same session
#         {
#             "tool_a": str,
#             "tool_b": str,
#             "co_occurrence_count": int,
#             "lift": float,             # statistical lift over random chance
#         },
#     ],
# }

# pattern_goal_progression = {
#     "goals_completed": int,
#     "goals_abandoned": int,
#     "avg_completion_days": float,
#     "active_goal_types": list[str],    # ["financial", "health"]
#     "goal_velocity_trend": str,        # "accelerating", "steady", "decelerating"
# }

# pattern_category_drift = {
#     "current_top_categories": list[str],  # ["finance", "productivity"]
#     "emerging_categories": list[str],     # categories with rising usage in last 14d
#     "declining_categories": list[str],
#     "category_usage_30d": {               # category_slug → invocation count
#         str: int,
#     },
# }

# pattern_churn_signal = {
#     "days_since_last_active": int,
#     "usage_trend_7d": str,             # "increasing", "stable", "declining", "inactive"
#     "tools_dropped": list[str],        # tool_ids user stopped using
#     "servers_disconnected": list[str],
#     "risk_level": str,                 # "low", "medium", "high"
# }

# pattern_workflow_tendency = {
#     "detected_chains": [               # recurring tool sequences
#         {
#             "chain": list[str],        # ["t_expense_track", "t_budget01", "t_savings_auto"]
#             "occurrence_count": int,
#             "avg_total_latency_ms": float,
#             "matching_workflow_id": str,  # nullable — if a formal workflow matches
#         },
#     ],
# }

# pattern_feedback_sentiment = {
#     "avg_rating_given": float,         # average across all feedback
#     "total_reviews": int,
#     "sentiment_distribution": {
#         "positive": int,
#         "neutral": int,
#         "negative": int,
#     },
#     "common_tags": list[str],          # ["useful", "slow", "needs-more-tools"]
# }

```