# SRE RCA Agent - Architecture Documentation

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Microsoft Teams Bot                          │
│                  (User Interface Layer)                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ POST /api/v1/investigate
                         │ (User Context: Free Text)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│                   (main.py - REST API)                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Orchestrator Agent                             │
│              (orchestrator.py - Controller)                      │
│                                                                   │
│  Workflow:                                                        │
│  1. Parse Context                                                │
│  2. Fetch Data (parallel)                                        │
│  3. Correlate                                                    │
│  4. Generate Response                                            │
└────┬─────────────┬─────────────┬─────────────┬─────────────────┘
     │             │             │             │
     ▼             ▼             ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐
│ Context  │ │ GitHub   │ │ DevOps   │ │ App         │
│ Parser   │ │ Fetcher  │ │ Checker  │ │ Insights    │
│ Agent    │ │ Agent    │ │ (Tool)   │ │ Retriever   │
│          │ │          │ │          │ │ (Tool)      │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬───────┘
     │            │            │             │
     │ GPT-4.1    │            │             │
     │ Nano       │            │             │
     ▼            ▼            ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐
│  Azure   │ │ GitHub   │ │  Azure   │ │   Azure     │
│ OpenAI   │ │   MCP    │ │ DevOps   │ │   Monitor   │
│ Foundry  │ │          │ │   API    │ │  App Insights│
└──────────┘ └──────────┘ └──────────┘ └─────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Correlation Engine Agent                            │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Rule-Based  │  │  ML-Based   │  │ LLM-Enhanced│            │
│  │ Correlation │  │  Anomaly    │  │  Reasoning  │            │
│  │             │  │  Detection  │  │             │            │
│  │ • Time      │  │ • Isolation │  │ • GPT-4.1   │            │
│  │   Proximity │  │   Forest    │  │   Nano      │            │
│  │ • Service   │  │ • Log       │  │ • Pattern   │            │
│  │   Matching  │  │   Patterns  │  │   Analysis  │            │
│  │ • File      │  │             │  │             │            │
│  │   Relevance │  │             │  │             │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Response Generator Agent                            │
│                                                                   │
│  • Executive Summary                                             │
│  • Ranked Suspect Causes                                         │
│  • Event Timeline                                                │
│  • Actionable Recommendations                                    │
│  • Teams Adaptive Card                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
                   RCA Response
                (JSON + Adaptive Card)
```

## Data Flow Diagram

```
User Input (Free Text)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ "Users experiencing 500 errors in payment service at 2PM.   │
│  Error code: ERR_PAYMENT_GATEWAY_TIMEOUT"                   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼ Context Parser Agent (GPT-4.1 Nano)
    │
┌─────────────────────────────────────────────────────────────┐
│ ParsedContext:                                               │
│ • service_name: "payment-service"                            │
│ • error_codes: ["ERR_PAYMENT_GATEWAY_TIMEOUT", "500"]       │
│ • timestamp: 2025-11-21T14:00:00Z                           │
│ • severity: HIGH                                             │
│ • keywords: ["timeout", "payment", "gateway"]                │
└─────────────────────────────────────────────────────────────┘
    │
    ├──────────┬──────────┬──────────┐
    │          │          │          │
    ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│GitHub  │ │DevOps  │ │ App    │ │Parallel  │
│Commits │ │Deploy  │ │Insights│ │Execution │
└───┬────┘ └───┬────┘ └───┬────┘ └──────────┘
    │          │          │
    ▼          ▼          ▼
┌──────────────────────────────────────────────┐
│ GitHub: 5 commits                             │
│ DevOps: 2 deployments (1 recent)             │
│ Logs: 127 entries (95 errors)                │
└──────────────┬───────────────────────────────┘
               │
               ▼ Correlation Engine
               │
┌──────────────────────────────────────────────┐
│ Correlation Matches:                          │
│                                               │
│ 1. Deployment "payment-deploy" (0.87)        │
│    - Completed 5 min before errors           │
│    - Modified gateway.py                     │
│    - 95% errors after deployment             │
│                                               │
│ 2. Commit abc123 (0.72)                      │
│    - Changed timeout config                  │
│    - 10 min before incident                  │
└──────────────┬───────────────────────────────┘
               │
               ▼ Response Generator
               │
┌──────────────────────────────────────────────┐
│ RCA Response:                                 │
│                                               │
│ Summary: "Investigation identified recent     │
│ deployment as likely cause..."                │
│                                               │
│ Recommendations:                              │
│ 1. Review commit abc123                       │
│ 2. Consider rollback                          │
│ 3. Increase timeout threshold                 │
│                                               │
│ + Adaptive Card for Teams                     │
└──────────────────────────────────────────────┘
```

## Agent Communication Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentExecutionContext                     │
│  (Shared state passed between agents)                       │
│                                                              │
│  • request_id: UUID                                          │
│  • user_context: UserContext                                 │
│  • parsed_context: ParsedContext                             │
│  • github_result: GitHubFetchResult                          │
│  • deployment_result: DeploymentCheckResult                  │
│  • appinsights_result: AppInsightsQueryResult                │
│  • correlation_result: CorrelationResult                     │
│  • final_response: RCAResponse                               │
│  • errors: List[str]                                         │
│  • started_at / completed_at: datetime                       │
└─────────────────────────────────────────────────────────────┘

Agent Pattern:

┌─────────────────────────────────────────────────────────────┐
│ Agent Interface:                                             │
│                                                              │
│ class Agent:                                                 │
│     async def execute(self, context):                        │
│         start_time = datetime.utcnow()                       │
│         try:                                                 │
│             # Agent logic                                    │
│             result = await self._process(context)            │
│             return AgentResult(                              │
│                 agent_name=self.name,                        │
│                 success=True,                                │
│                 data=result,                                 │
│                 execution_time=elapsed                       │
│             )                                                │
│         except Exception as e:                               │
│             return AgentResult(                              │
│                 agent_name=self.name,                        │
│                 success=False,                               │
│                 error=str(e)                                 │
│             )                                                │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Orchestrator Agent
**File**: `orchestrator.py`

**Responsibilities**:
- Manage overall workflow
- Initialize all agents
- Handle parallel execution
- Aggregate results
- Error handling and fallbacks

**Key Methods**:
- `investigate(user_context)` - Main entry point
- `_fetch_github_data()` - Async GitHub data retrieval
- `_fetch_devops_data()` - Async DevOps data retrieval
- `_fetch_appinsights_data()` - Async logs retrieval

### Context Parser Agent
**File**: `agents/context_parser.py`

**Responsibilities**:
- Parse free-text input
- Extract structured entities
- Use GPT-4.1 Nano for understanding
- Fallback to heuristics if LLM fails

**Inputs**: `UserContext` (raw text)
**Outputs**: `ParsedContext` (structured)

### GitHub Fetcher Agent
**File**: `agents/github_fetcher.py`

**Responsibilities**:
- Fetch recent commits
- Filter by time and service
- Use GitHub MCP integration
- Format commit information

**Inputs**: `ParsedContext`
**Outputs**: `GitHubFetchResult`

### Correlation Engine Agent
**File**: `agents/correlation_engine.py`

**Responsibilities**:
- Combine all data sources
- Rule-based correlation scoring
- ML-based anomaly detection
- LLM-enhanced reasoning
- Rank suspected causes

**Inputs**: All data (context, commits, deployments, logs)
**Outputs**: `CorrelationResult`

**Correlation Factors**:
1. **Time Proximity** (40%): Exponential decay based on time difference
2. **Service Matching** (30%): Exact or partial name match
3. **Error Pattern** (20%): Error code presence and frequency
4. **File Relevance** (10%): Service name in changed files

### Response Generator Agent
**File**: `agents/response_generator.py`

**Responsibilities**:
- Generate executive summary
- Format correlation results
- Create recommendations
- Build timeline
- Generate Teams Adaptive Card

**Inputs**: `ParsedContext`, `CorrelationResult`
**Outputs**: `RCAResponse`

## Integration Architecture

### GitHub MCP Integration
**File**: `integrations/github_mcp.py`

**Current Implementation**:
- Uses PyGithub library
- Direct GitHub API access

**Production Alternatives**:
1. Official GitHub MCP client
2. External MCP server (HTTP/RPC)
3. Enhanced with GraphQL API

**Key Functions**:
- `fetch_recent_commits()` - Get commits in time range
- `get_commit_details()` - Get single commit details
- `search_commits_by_keyword()` - Search by message

### Azure MCP Integration
**File**: `integrations/azure_mcp.py`

**Components**:
1. **Azure DevOps**: `azure-devops` SDK
2. **App Insights**: `azure-monitor-query` SDK
3. **Authentication**: `azure-identity` SDK

**Key Functions**:
- `check_deployments()` - Query pipeline runs
- `query_app_insights_logs()` - Execute KQL queries
- `get_deployment_logs()` - Get build logs

## Data Models

### Core Models
**File**: `models.py`

```python
UserContext          # Input from user
    ├─ raw_text
    ├─ user_id
    └─ timestamp

ParsedContext        # Structured context
    ├─ service_name
    ├─ error_codes[]
    ├─ timestamp
    ├─ severity
    ├─ keywords[]
    └─ summary

CommitInfo          # GitHub commit
    ├─ sha
    ├─ message
    ├─ author
    ├─ timestamp
    ├─ files_changed[]
    └─ url

DeploymentInfo      # Azure DevOps deployment
    ├─ pipeline_id
    ├─ status
    ├─ started_time
    ├─ commit_sha
    └─ environment

LogEntry            # App Insights log
    ├─ timestamp
    ├─ severity
    ├─ message
    ├─ service_name
    └─ error_code

CorrelationMatch    # Suspected cause
    ├─ cause_description
    ├─ confidence_score
    ├─ evidence[]
    ├─ related_commits[]
    ├─ related_deployments[]
    └─ related_logs[]

RCAResponse         # Final output
    ├─ summary
    ├─ top_suspects[]
    ├─ timeline[]
    ├─ recommendations[]
    └─ adaptive_card
```

## API Endpoints

### Primary Endpoint

**POST** `/api/v1/investigate`
- **Purpose**: Full RCA investigation
- **Input**: `UserContext`
- **Output**: `RCAResponse`
- **Timeout**: 60 seconds
- **Rate Limit**: 10 requests/minute

### Testing Endpoints

**POST** `/api/v1/parse-context`
- **Purpose**: Test context parsing only
- **Input**: `UserContext`
- **Output**: `ParsedContext`

**POST** `/api/v1/fetch-commits`
- **Purpose**: Test GitHub integration only
- **Input**: `ParsedContext`
- **Output**: `GitHubFetchResult`

### Utility Endpoints

**GET** `/health`
- **Purpose**: Health check
- **Output**: Service status

**GET** `/api/v1/status/{request_id}`
- **Purpose**: Investigation status
- **Output**: Status information

**POST** `/api/v1/teams-webhook`
- **Purpose**: Teams bot integration
- **Input**: Teams payload
- **Output**: Adaptive Card

## Deployment Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Azure Cloud                            │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Azure Container Apps / App Service          │  │
│  │                                                     │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │    SRE RCA Agent (FastAPI)                    │  │  │
│  │  │    • Orchestrator                             │  │  │
│  │  │    • Agents                                   │  │  │
│  │  │    • Integrations                             │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └─────────┬──────────────────────────────────────────┘  │
│            │                                              │
│  ┌─────────┴──────────────────────────────────────────┐  │
│  │  Azure Services                                     │  │
│  │  • Azure OpenAI (GPT-4.1 Nano)                     │  │
│  │  • Azure DevOps (Pipelines API)                    │  │
│  │  • Azure Monitor (App Insights)                    │  │
│  │  • Azure Key Vault (Secrets)                       │  │
│  │  • Application Insights (Monitoring)               │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
└──────────────────────────────────────────────────────────┘
                         │
                         ├── GitHub API
                         │
                         └── Microsoft Teams
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Security Layers                                          │
│                                                          │
│ 1. Authentication                                        │
│    • Azure AD / Managed Identity                        │
│    • API Keys (Azure Key Vault)                         │
│    • GitHub PAT                                          │
│                                                          │
│ 2. Authorization                                         │
│    • RBAC on Azure resources                            │
│    • Scoped GitHub tokens                               │
│    • DevOps PAT with minimal permissions                │
│                                                          │
│ 3. Network Security                                      │
│    • HTTPS only (TLS 1.2+)                              │
│    • VNet integration (optional)                        │
│    • Private endpoints                                  │
│                                                          │
│ 4. Data Protection                                       │
│    • Secrets in Key Vault                               │
│    • No credentials in code                             │
│    • Encrypted at rest and in transit                   │
│                                                          │
│ 5. Rate Limiting                                         │
│    • API rate limits                                    │
│    • Token bucket algorithm                             │
│    • Per-user quotas                                    │
└─────────────────────────────────────────────────────────┘
```

## Scalability Considerations

### Horizontal Scaling
- Multiple container replicas
- Load balancing across instances
- Stateless design (no local state)

### Vertical Scaling
- Increase CPU/memory per instance
- Optimize GPT-4.1 Nano token usage
- Cache frequently accessed data

### Performance Optimization
- Parallel agent execution
- Async I/O throughout
- Connection pooling
- Result caching (Redis)

## Monitoring and Observability

```
Application Insights
    │
    ├── Custom Metrics
    │   • Investigation duration
    │   • Agent execution times
    │   • Correlation match counts
    │   • API call latencies
    │
    ├── Logs
    │   • Agent execution logs
    │   • Error traces
    │   • User interactions
    │
    └── Alerts
        • High error rate
        • Slow investigations
        • Integration failures
```

## Future Enhancements

1. **Streaming Responses**: Real-time updates during investigation
2. **Caching Layer**: Redis for frequently accessed data
3. **ML Model Training**: Learn from resolved incidents
4. **Multi-Repository**: Support multiple GitHub repos
5. **Custom Integrations**: Pluggable integration framework
6. **Feedback Loop**: Learn from user feedback on RCA accuracy
7. **Dashboard**: Web UI for investigation history and analytics
