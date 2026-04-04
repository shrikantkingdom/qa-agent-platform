from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TestType(str, Enum):
    HAPPY_PATH = "Happy Path"
    NEGATIVE = "Negative"
    EDGE_CASE = "Edge Case"
    REGRESSION = "Regression"


# ── Workflow step selection ────────────────────────────────────────────────────

class WorkflowSteps(BaseModel):
    """Fine-grained control over which steps run in the QA workflow."""
    ticket_quality: bool = Field(True, description="Score ticket quality + improvement suggestions")
    code_alignment: bool = Field(True, description="Check code commits align with Jira AC")
    test_cases: bool = Field(True, description="Generate test cases (Xray-ready format)")
    bdd_scenarios: bool = Field(True, description="Generate BDD Gherkin scenarios")
    step_definitions: bool = Field(True, description="Generate pytest-bdd step definitions")
    step_def_style: str = Field("pytest_bdd", description="'pytest_bdd' (repo-aligned) or 'generic'")


class QARequest(BaseModel):
    jira_id: str = Field(..., description="Jira ticket ID, e.g. CRFLT-101")
    release: Optional[str] = Field(None, description="Release name or version")
    steps: WorkflowSteps = Field(default_factory=WorkflowSteps, description="Which steps to run")
    post_to_jira: bool = Field(False, description="Post QA comment to Jira ticket (auto, during workflow)")
    create_pr: bool = Field(False, description="Create PR in automation repo")
    custom_prompt: Optional[str] = Field(None, description="Additional QA instructions or context")
    team_id: Optional[str] = Field(None, description="Team config to load (e.g. 'statements', 'confirms', 'letters')")
    triggered_by: str = Field("anonymous", description="User name for audit log")

    # Back-compat: honour old include_bdd field if sent
    include_bdd: bool = Field(True, description="[deprecated] Use steps.bdd_scenarios instead")


class ReleaseQARequest(BaseModel):
    release: str = Field(..., description="Release version — all tickets in this release will be processed")
    include_bdd: bool = Field(True, description="Generate BDD scenarios")
    custom_prompt: Optional[str] = Field(None, description="Additional QA instructions")
    team_id: Optional[str] = Field(None, description="Team config to apply")


class JiraUploadRequest(BaseModel):
    jira_id: str = Field(..., description="Jira ticket to post results to")
    edited_summary: str = Field(..., description="QA summary text (editable before upload)")
    edited_issues: List[str] = Field(default_factory=list, description="List of issues (editable)")
    quality_score: int = Field(..., description="Final quality score (0-100)")
    grade: str = Field(..., description="Grade letter")
    attach_report: bool = Field(True, description="Attach the HTML report file")
    report_filename: Optional[str] = Field(None, description="HTML report filename to attach")


class PushTestsRequest(BaseModel):
    jira_id: str = Field(..., description="Jira ticket ID whose generated tests to push")
    create_pr: bool = Field(True, description="Open a pull request (True) or push directly to a branch (False)")
    branch_prefix: Optional[str] = Field(None, description="Custom branch prefix; defaults to qa-agent")


class TeamConfigUpdate(BaseModel):
    content: str = Field(..., description="Markdown content of the team configuration file")


class JiraTicket(BaseModel):
    id: str
    summary: str
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    story_points: Optional[int] = None
    labels: List[str] = []
    components: List[str] = []
    linked_commits: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ValidationIssue(BaseModel):
    field: str
    severity: str  # "critical" | "warning" | "info"
    message: str
    recommendation: str


class ValidationResult(BaseModel):
    quality_score: int = Field(..., ge=0, le=100)
    grade: str
    issues: List[ValidationIssue] = []
    strengths: List[str] = []
    summary: str


class GitCommit(BaseModel):
    sha: str
    message: str
    author: str
    date: str
    files_changed: List[str] = []
    diff_summary: Optional[str] = None


class AlignmentResult(BaseModel):
    score: int = Field(..., ge=0, le=100)
    aligned: bool
    coverage_gaps: List[str] = []
    over_implementation: List[str] = []
    summary: str


class TestCase(BaseModel):
    test_id: str
    scenario: str
    steps: List[str]
    expected_result: str
    test_type: TestType
    priority: str = "Medium"
    tags: List[str] = []


class BDDScenario(BaseModel):
    feature: str
    scenario_name: str
    given: List[str]
    when: List[str]
    then: List[str]
    tags: List[str] = []


class StepDefinition(BaseModel):
    step_text: str
    step_type: str  # Given | When | Then
    code: str
    language: str = "python"


class QAWorkflowResult(BaseModel):
    jira_id: str
    release: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    ticket: Optional[JiraTicket] = None
    validation: Optional[ValidationResult] = None
    commits: List[GitCommit] = []
    alignment: Optional[AlignmentResult] = None
    test_cases: List[TestCase] = []
    bdd_scenarios: List[BDDScenario] = []
    step_definitions: List[StepDefinition] = []
    report_path: Optional[str] = None
    testcases_csv_path: Optional[str] = None
    testcases_json_path: Optional[str] = None
    bdd_feature_path: Optional[str] = None
    status: str = "completed"
    error: Optional[str] = None
    duration_seconds: Optional[float] = None


class QAResponse(BaseModel):
    success: bool
    message: str
    data: Optional[QAWorkflowResult] = None
    error: Optional[str] = None
    run_id: Optional[str] = None


# ── History ───────────────────────────────────────────────────────────────────

class HistoryEntry(BaseModel):
    run_id: str
    task_type: str
    jira_id: Optional[str]
    release: Optional[str]
    team_id: Optional[str]
    team_name: Optional[str]
    triggered_by: str
    triggered_at: str
    duration_secs: Optional[float]
    status: str
    steps_selected: Optional[Dict[str, Any]]
    quality_score: Optional[int]
    alignment_score: Optional[int]
    test_case_count: Optional[int]
    bdd_count: Optional[int]
    error_message: Optional[str]
    outputs: Optional[Dict[str, Any]]


class HistoryResponse(BaseModel):
    total: int
    offset: int
    limit: int
    runs: List[HistoryEntry]


class StatsResponse(BaseModel):
    total_runs: int
    completed_runs: int
    failed_runs: int
    avg_quality_score: Optional[float]
    by_team: Dict[str, int]
    by_task_type: Dict[str, int]
    recent_runs: List[Dict[str, Any]]


# ── Upstream / Test Data ──────────────────────────────────────────────────────

class UpstreamCallRequest(BaseModel):
    endpoint: str = Field(..., description="Endpoint key or path, e.g. 'GET /accounts/{id}/holdings'")
    params: Dict[str, Any] = Field(default_factory=dict, description="Path + query params to pass")


class UpstreamCallResponse(BaseModel):
    system_id: str
    endpoint: str
    response: Dict[str, Any]
    stub: bool = True


class TestDataRequest(BaseModel):
    system_id: str = Field(..., description="Upstream system identifier")
    data_type: str = Field(..., description="Type of data to discover/create, e.g. 'retirement_account'")
    action: str = Field("discover", description="'discover' or 'create'")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Criteria to match existing data")
    spec: Dict[str, Any] = Field(default_factory=dict, description="Spec for data creation")


class TestDataResponse(BaseModel):
    success: bool
    system_id: str
    action: str
    data: Dict[str, Any]


# ── Jira Ops ──────────────────────────────────────────────────────────────────

class JiraQueryRequest(BaseModel):
    component: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    sprint: Optional[str] = None
    fix_version: Optional[str] = None
    label: Optional[str] = None
    ticket_type: Optional[str] = None
    text_search: Optional[str] = None
    limit: int = Field(50, ge=1, le=200)


class JiraCreateRequest(BaseModel):
    type: str = Field("Story", description="Issue type: Epic, Story, Bug, Sub-task, Test, ...")
    summary: str
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    component: Optional[str] = None
    assignee: Optional[str] = None
    priority: str = "Medium"
    labels: List[str] = []
    story_points: Optional[int] = None
    fix_version: Optional[str] = None
    sprint: Optional[str] = None
    epic_id: Optional[str] = None
    team_id: Optional[str] = None


class BulkTransitionRequest(BaseModel):
    ticket_ids: List[str]
    new_status: str
    comment: Optional[str] = None


class BulkFieldUpdateRequest(BaseModel):
    ticket_ids: List[str]
    fields: Dict[str, Any] = Field(..., description="Fields to update, e.g. {assignee, priority}")
    comment: Optional[str] = None


class AddCommentRequest(BaseModel):
    ticket_id: str
    comment: str
    author: str = "qa-agent"


class TestPlanRequest(BaseModel):
    name: str
    fix_version: str
    ticket_ids: List[str]
    team_id: str


class TestSetRequest(BaseModel):
    plan_id: str
    name: str
    ticket_ids: List[str]


class TestExecutionRequest(BaseModel):
    plan_id: str
    set_id: Optional[str] = None
    ticket_ids: List[str]


class MarkTestResultRequest(BaseModel):
    exec_id: str
    ticket_id: str
    result: str = Field(..., description="Pass | Fail | Blocked | Not Run")
    comment: Optional[str] = None


# ── Quick Tasks ───────────────────────────────────────────────────────────────

class QuickRegressionRequest(BaseModel):
    jira_id: str
    pr_url: Optional[str] = None
    additional_context: Optional[str] = None
    team_id: Optional[str] = None
    triggered_by: str = "anonymous"
