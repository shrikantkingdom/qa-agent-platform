import json
from typing import Any, Dict, Optional, Tuple

from openai import AsyncOpenAI, RateLimitError, APITimeoutError, APIStatusError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config.settings import settings
from app.config.providers import get_provider, resolve_base_url, supports_json_mode
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIService:
    def __init__(self) -> None:
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            provider = settings.llm_provider
            base_url = resolve_base_url(provider, settings.openai_base_url)
            logger.info(
                f"LLM client initialised | provider={provider} "
                f"model={settings.openai_model} base_url={base_url or 'SDK default'}"
            )
            kwargs: Dict[str, Any] = {
                "api_key": settings.openai_api_key or "mock-key"
            }
            if base_url:
                kwargs["base_url"] = base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    def _reset_client(self) -> None:
        """Force client re-initialisation (e.g. after env changes in tests)."""
        self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APITimeoutError,)),
        reraise=True,
    )
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        if not settings.openai_api_key:
            logger.warning("No LLM API key configured — using mock response")
            return self._mock_response(user_prompt)

        provider = settings.llm_provider
        use_json_mode = supports_json_mode(provider)

        try:
            kwargs: Dict[str, Any] = dict(
                model=settings.openai_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            if use_json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or "{}"

        except RateLimitError as exc:
            if "insufficient_quota" in str(exc):
                logger.warning(
                    f"[{provider}] Quota/billing limit reached — falling back to mock response"
                )
                return self._mock_response(user_prompt)
            raise  # real rate-limit: tenacity will retry
        except APIStatusError as exc:
            logger.error(f"[{provider}] API error {exc.status_code}: {exc.message}")
            raise

    async def call_structured(
        self, system_prompt: str, user_prompt: str
    ) -> Dict[str, Any]:
        raw = await self._call_llm(system_prompt, user_prompt)
        # Strip markdown code fences that some models emit despite instructions
        stripped = raw.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            stripped = "\n".join(
                l for l in lines if not l.startswith("```")
            ).strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            logger.error(f"LLM returned non-JSON — raw: {raw[:200]}")
            return {}

    # ------------------------------------------------------------------ #
    # Prompt Builders                                                       #
    # ------------------------------------------------------------------ #

    def build_validation_prompt(
        self,
        ticket: Dict[str, Any],
        additional_context: str = "",
    ) -> Tuple[str, str]:
        system = (
            "You are a senior QA analyst. Evaluate Jira ticket quality and return "
            "a structured JSON object. Be precise and actionable. "
            "Output ONLY valid JSON — no markdown, no prose."
        )
        user = f"""Analyse this Jira ticket and return a JSON object with these exact keys:
- quality_score  (integer 0–100)
- grade          (string: A / B / C / D / F)
- issues         (array of objects: field, severity ["critical"|"warning"|"info"], message, recommendation)
- strengths      (array of strings)
- summary        (string)

Evaluation criteria:
1. Summary clarity and specificity
2. Description completeness
3. Acceptance criteria quality and testability
4. Missing required fields (assignee, story points, components)
5. Ambiguity and undefined terms

Ticket:
{json.dumps(ticket, indent=2)}"""
        if additional_context:
            user += f"\n\nAdditional QA context / instructions:\n{additional_context}"
        return system, user

    def build_alignment_prompt(
        self,
        ticket: Dict[str, Any],
        commits: list,
        additional_context: str = "",
    ) -> Tuple[str, str]:
        system = (
            "You are a senior QA engineer performing code-to-requirements alignment analysis. "
            "Return structured JSON only — no markdown, no prose."
        )
        user = f"""Analyse alignment between the Jira ticket and the GitHub commits below.
Return a JSON object with these exact keys:
- score               (integer 0–100)
- aligned             (boolean)
- coverage_gaps       (array of strings — requirements not covered by committed code)
- over_implementation (array of strings — code features beyond ticket scope)
- summary             (string)

Ticket:
{json.dumps(ticket, indent=2)}

Commits:
{json.dumps(commits, indent=2)}"""
        if additional_context:
            user += f"\n\nAdditional context:\n{additional_context}"
        return system, user

    def build_test_generation_prompt(
        self,
        ticket: Dict[str, Any],
        alignment: Dict[str, Any],
        additional_context: str = "",
    ) -> Tuple[str, str]:
        system = (
            "You are an expert QA engineer. Generate comprehensive, structured test cases. "
            "Return JSON only — no markdown, no prose."
        )
        user = f"""Generate test cases for the Jira ticket below.
Return a JSON object with key "test_cases" — an array of objects with:
  - test_id         (string, format TC-001)
  - scenario        (string)
  - steps           (array of strings)
  - expected_result (string)
  - test_type       (one of: "Happy Path" | "Negative" | "Edge Case" | "Regression")
  - priority        (High | Medium | Low)
  - tags            (array of strings)

Requirements:
- Minimum 3 Happy Path scenarios
- Minimum 3 Negative scenarios
- Minimum 2 Edge Case scenarios
- Address every coverage gap listed below

Ticket:
{json.dumps(ticket, indent=2)}

Coverage gaps to address:
{json.dumps(alignment.get("coverage_gaps", []))}"""
        if additional_context:
            user += f"\n\nAdditional context:\n{additional_context}"
        return system, user

    def build_bdd_prompt(
        self,
        ticket: Dict[str, Any],
        test_cases: list,
        additional_context: str = "",
    ) -> Tuple[str, str]:
        system = (
            "You are a BDD expert. Convert requirements and test cases into Gherkin scenarios. "
            "Return JSON only — no markdown, no prose."
        )
        user = f"""Generate BDD Gherkin scenarios for the ticket below.
Return a JSON object with:
- feature_name (string)
- scenarios    (array of objects):
    - scenario_name (string)
    - given         (array of strings — each a complete Given step)
    - when          (array of strings — each a complete When step)
    - then          (array of strings — each a complete Then step)
    - tags          (array of strings e.g. "@smoke", "@regression")

Ticket:
{json.dumps(ticket, indent=2)}

Representative test cases:
{json.dumps(test_cases[:6], indent=2)}"""
        if additional_context:
            user += f"\n\nAdditional context:\n{additional_context}"
        return system, user

    def build_step_definitions_prompt(
        self,
        scenarios: list,
        additional_context: str = "",
    ) -> Tuple[str, str]:
        """Generate pytest-bdd step definitions aligned with playwright_project structure."""
        system = (
            "You are a test automation engineer specialising in pytest-bdd + Playwright. "
            "Generate production-ready pytest-bdd step definition files that integrate with "
            "the playwright_project framework. "
            "Return JSON only — no markdown, no prose."
        )
        repo_context = (
            "Target framework: playwright_project (pytest-bdd 7.x + Playwright sync_api + POM)\n\n"
            "Project structure:\n"
            "- Feature files: features/ui/<feature>.feature  or  features/api/<feature>.feature\n"
            "- Step definitions: tests/step_defs/ui/test_<feature>_steps.py  or  tests/step_defs/api/test_<feature>_steps.py\n"
            "- Page Object classes in pages/ (BasePage subclasses)\n\n"
            "Root conftest.py fixtures available:\n"
            "    * page              — Playwright Page (function-scoped)\n"
            "    * authenticated_page — Page already logged in to the app\n"
            "    * config            — BaseConfig (ui_base_url, api_base_url, etc.)\n"
            "    * api_client        — HTTP client for API tests\n"
            "    * browser_context   — Playwright BrowserContext\n\n"
            "Conventions:\n"
            "- Import: from pytest_bdd import given, when, then, parsers, scenarios\n"
            "- Link feature file at top: scenarios(str(FEATURES_DIR / 'ui' / '<name>.feature'))\n"
            "- Decorator style: @given(...) @when(...) @then(...)\n"
            "- Use parsers.parse(...) for steps with parameters e.g. @when(parsers.parse('I login as \"{username}\"'))\n"
            "- Use target_fixture on @given to return Page Object as a named fixture\n"
            "- Function naming: given_<verb>, when_<verb>, then_<verb>\n"
            "- Keep @scenario-level markers via pytest.mark on the step def functions only when applicable\n\n"
            "Example UI step definitions file:\n"
            "    from pathlib import Path\n"
            "    from pytest_bdd import given, when, then, parsers, scenarios\n"
            "    from pages.login_page import LoginPage\n\n"
            "    FEATURES_DIR = Path(__file__).parent.parent.parent.parent / 'features'\n"
            "    scenarios(str(FEATURES_DIR / 'ui' / 'login.feature'))\n\n"
            "    @given('I am on the login page', target_fixture='login_page')\n"
            "    def given_on_login_page(page, config):\n"
            "        lp = LoginPage(page)\n"
            "        lp.open(config.ui_base_url)\n"
            "        return lp\n\n"
            "    @when(parsers.parse('I login with username \"{username}\" and password \"{password}\"'))\n"
            "    def when_login(login_page, username, password):\n"
            "        login_page.login(username, password)\n\n"
            "    @then('I should be redirected to the inventory page')\n"
            "    def then_on_inventory_page(page):\n"
            "        page.wait_for_url('**/inventory.html')\n"
            "        assert 'inventory.html' in page.url\n"
        )
        user = f"""Generate pytest-bdd step definitions for the BDD scenarios below.

{repo_context}

Return a JSON object with key "step_definitions" — an array of objects with:
  - step_text  (string — the step definition function name, e.g. "given_on_login_page")
  - step_type  (string — "given" | "when" | "then")
  - code       (string — COMPLETE step definitions file including all imports, scenarios() call, and ALL @given/@when/@then decorated functions for the scenario)
  - language   (always "python")

Rules:
- One code entry per scenario — each entry should be a COMPLETE step definitions file
- Always include the FEATURES_DIR and scenarios() call at the top
- Use parsers.parse() for any step containing quoted strings or numeric parameters
- Use target_fixture on @given steps that instantiate Page Objects
- Use page or authenticated_page fixture — never import playwright directly
- Use config fixture for URLs/credentials — never hardcode them
- Write complete, runnable code (not pseudocode or placeholders)

Scenarios:
{json.dumps(scenarios[:4], indent=2)}"""
        if additional_context:
            user += f"\n\nAdditional context:\n{additional_context}"
        return system, user

    # ------------------------------------------------------------------ #
    # Mock Responses (used when OPENAI_API_KEY is not set)                  #
    # ------------------------------------------------------------------ #

    def _mock_response(self, user_prompt: str) -> str:  # noqa: PLR0911
        prompt_lower = user_prompt.lower()

        if "quality_score" in prompt_lower:
            return json.dumps({
                "quality_score": 72,
                "grade": "B",
                "issues": [
                    {
                        "field": "acceptance_criteria",
                        "severity": "warning",
                        "message": "Acceptance criteria are vague and lack measurable pass/fail conditions.",
                        "recommendation": "Rewrite as explicit Given/When/Then statements.",
                    },
                    {
                        "field": "description",
                        "severity": "info",
                        "message": "Description lacks API contract details and data flow context.",
                        "recommendation": "Add endpoint specifications, request/response schemas, and sequence diagrams.",
                    },
                ],
                "strengths": [
                    "Clear, descriptive summary",
                    "Priority and assignee are set",
                    "Linked to relevant components",
                ],
                "summary": (
                    "The ticket has solid fundamentals but needs stronger acceptance criteria "
                    "and more technical context to be fully testable."
                ),
            })

        if "coverage_gaps" in prompt_lower or "alignment" in prompt_lower:
            return json.dumps({
                "score": 78,
                "aligned": True,
                "coverage_gaps": [
                    "Error handling for expired OAuth tokens not addressed in commits",
                    "Session timeout behaviour (8-hour requirement) not implemented",
                ],
                "over_implementation": [
                    "Additional Redis session caching layer added beyond ticket scope",
                ],
                "summary": (
                    "Code generally aligns with requirements. "
                    "Minor gaps in token error handling and session timeout logic."
                ),
            })

        if "test_cases" in prompt_lower:
            return json.dumps({
                "test_cases": [
                    {
                        "test_id": "TC-001",
                        "scenario": "Successful login via Google OAuth2",
                        "steps": [
                            "Navigate to login page",
                            "Click 'Login with Google'",
                            "Authenticate with valid Google credentials in OAuth popup",
                        ],
                        "expected_result": "User is redirected to dashboard with welcome message",
                        "test_type": "Happy Path",
                        "priority": "High",
                        "tags": ["smoke", "oauth", "google"],
                    },
                    {
                        "test_id": "TC-002",
                        "scenario": "Successful login via GitHub OAuth2",
                        "steps": [
                            "Navigate to login page",
                            "Click 'Login with GitHub'",
                            "Authenticate with valid GitHub credentials",
                        ],
                        "expected_result": "User is redirected to dashboard",
                        "test_type": "Happy Path",
                        "priority": "High",
                        "tags": ["smoke", "oauth", "github"],
                    },
                    {
                        "test_id": "TC-003",
                        "scenario": "Session persists across browser restart",
                        "steps": [
                            "Login with valid OAuth credentials",
                            "Close and reopen the browser",
                            "Navigate to the application URL",
                        ],
                        "expected_result": "User remains authenticated (session persists)",
                        "test_type": "Happy Path",
                        "priority": "Medium",
                        "tags": ["session"],
                    },
                    {
                        "test_id": "TC-004",
                        "scenario": "OAuth login fails with denied permission",
                        "steps": [
                            "Navigate to login page",
                            "Click 'Login with Google'",
                            "Click 'Deny' on the Google consent screen",
                        ],
                        "expected_result": "User sees error message: 'Login cancelled. Please try again.'",
                        "test_type": "Negative",
                        "priority": "High",
                        "tags": ["oauth", "negative"],
                    },
                    {
                        "test_id": "TC-005",
                        "scenario": "Login with revoked OAuth token",
                        "steps": [
                            "Revoke application access in Google account settings",
                            "Return to app and attempt login",
                        ],
                        "expected_result": "User sees informative error and is prompted to re-authenticate",
                        "test_type": "Negative",
                        "priority": "High",
                        "tags": ["oauth", "security", "negative"],
                    },
                    {
                        "test_id": "TC-006",
                        "scenario": "Session expires after 8 hours of inactivity",
                        "steps": [
                            "Login successfully",
                            "Leave the session idle for 8 hours",
                            "Attempt to navigate to a protected page",
                        ],
                        "expected_result": "User is redirected to login page with 'Session expired' message",
                        "test_type": "Negative",
                        "priority": "High",
                        "tags": ["session", "security"],
                    },
                    {
                        "test_id": "TC-007",
                        "scenario": "OAuth callback with tampered state parameter",
                        "steps": [
                            "Initiate OAuth login",
                            "Intercept and modify the 'state' parameter in the callback URL",
                            "Submit the tampered callback",
                        ],
                        "expected_result": "Login is rejected; CSRF protection triggers an error",
                        "test_type": "Edge Case",
                        "priority": "High",
                        "tags": ["security", "csrf"],
                    },
                    {
                        "test_id": "TC-008",
                        "scenario": "Concurrent login from two different browsers",
                        "steps": [
                            "Login in Browser A",
                            "Login with the same account in Browser B",
                        ],
                        "expected_result": "Both sessions are valid simultaneously",
                        "test_type": "Edge Case",
                        "priority": "Medium",
                        "tags": ["session", "concurrency"],
                    },
                ],
            })

        if "scenarios" in prompt_lower or "gherkin" in prompt_lower or "bdd" in prompt_lower:
            return json.dumps({
                "feature_name": "OAuth2 Social Login",
                "scenarios": [
                    {
                        "scenario_name": "User logs in successfully via Google OAuth2",
                        "given": ["the user is on the login page"],
                        "when": [
                            "the user clicks the 'Login with Google' button",
                            "the user grants permission on the Google consent screen",
                        ],
                        "then": [
                            "the user should be redirected to the dashboard",
                            "a personalised welcome message should be displayed",
                        ],
                        "tags": ["@smoke", "@oauth", "@happy-path"],
                    },
                    {
                        "scenario_name": "User denies OAuth permission",
                        "given": ["the user is on the login page"],
                        "when": [
                            "the user clicks the 'Login with Google' button",
                            "the user clicks 'Deny' on the consent screen",
                        ],
                        "then": [
                            "the user should remain on the login page",
                            "an error message 'Login cancelled. Please try again.' should be displayed",
                        ],
                        "tags": ["@negative", "@oauth"],
                    },
                    {
                        "scenario_name": "Session expires after inactivity",
                        "given": [
                            "the user is authenticated",
                            "the session has been idle for 8 hours",
                        ],
                        "when": ["the user navigates to a protected resource"],
                        "then": [
                            "the user should be redirected to the login page",
                            "the message 'Session expired. Please log in again.' should be shown",
                        ],
                        "tags": ["@session", "@security", "@negative"],
                    },
                    {
                        "scenario_name": "CSRF protection rejects tampered state parameter",
                        "given": ["the user has initiated an OAuth login flow"],
                        "when": [
                            "the OAuth callback is received with a modified state parameter"
                        ],
                        "then": [
                            "the login attempt should be rejected",
                            "an error message about an invalid request should be displayed",
                        ],
                        "tags": ["@security", "@edge-case"],
                    },
                ],
            })

        if "step_definitions" in prompt_lower or "pytest-bdd" in prompt_lower or "playwright" in prompt_lower:
            return json.dumps({
                "step_definitions": [
                    {
                        "step_text": "given_on_login_page",
                        "step_type": "given",
                        "code": (
                            "from pathlib import Path\n\n"
                            "from pytest_bdd import given, when, then, parsers, scenarios\n\n"
                            "from pages.login_page import LoginPage\n\n"
                            "FEATURES_DIR = Path(__file__).parent.parent.parent.parent / 'features'\n"
                            "scenarios(str(FEATURES_DIR / 'ui' / 'login.feature'))\n\n\n"
                            "# ── Given ────────────────────────────────────────────────────────────────────\n\n"
                            "@given('I am on the login page', target_fixture='login_page')\n"
                            "def given_on_login_page(page, config):\n"
                            "    lp = LoginPage(page)\n"
                            "    lp.open(config.ui_base_url)\n"
                            "    return lp\n\n\n"
                            "# ── When ─────────────────────────────────────────────────────────────────────\n\n"
                            "@when(parsers.parse('I login with username \"{username}\" and password \"{password}\"'))\n"
                            "def when_login(login_page, username, password):\n"
                            "    login_page.login(username, password)\n\n\n"
                            "# ── Then ─────────────────────────────────────────────────────────────────────\n\n"
                            "@then('I should be redirected to the inventory page')\n"
                            "def then_on_inventory_page(page):\n"
                            "    page.wait_for_url('**/inventory.html')\n"
                            "    assert 'inventory.html' in page.url\n\n"
                            "@then(parsers.parse('I should see the error message containing \"{text}\"'))\n"
                            "def then_see_error_containing(login_page, text):\n"
                            "    error = login_page.get_error_message()\n"
                            "    assert text.lower() in error.lower()\n"
                        ),
                        "language": "python",
                    },
                    {
                        "step_text": "when_request_all_posts",
                        "step_type": "when",
                        "code": (
                            "from pathlib import Path\n\n"
                            "import pytest\n"
                            "from pytest_bdd import given, when, then, parsers, scenarios\n\n"
                            "FEATURES_DIR = Path(__file__).parent.parent.parent.parent / 'features'\n"
                            "scenarios(str(FEATURES_DIR / 'api' / 'posts.feature'))\n\n\n"
                            "# ── Given ────────────────────────────────────────────────────────────────────\n\n"
                            "@pytest.fixture\n"
                            "def context():\n"
                            "    return {}\n\n\n"
                            "# ── When ─────────────────────────────────────────────────────────────────────\n\n"
                            "@when('I request all posts')\n"
                            "def when_request_all_posts(api_client, context):\n"
                            "    context['response'] = api_client.get_posts()\n\n\n"
                            "# ── Then ─────────────────────────────────────────────────────────────────────\n\n"
                            "@then('the response status should be 200')\n"
                            "def then_status_200(context):\n"
                            "    assert context['response'].status_code == 200\n\n"
                            "@then('the response should contain a list of posts')\n"
                            "def then_posts_list(context):\n"
                            "    data = context['response'].json()\n"
                            "    assert isinstance(data, list)\n"
                            "    assert len(data) > 0\n"
                        ),
                        "language": "python",
                    },
                ],
            })

        return "{}"


ai_service = AIService()
