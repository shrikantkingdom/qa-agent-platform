from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "QA Agent Platform"
    app_version: str = "1.0.0"
    debug: bool = False

    # LLM Provider
    # Supported: openai | github | anthropic | deepseek | azure | groq | mistral | ollama | gemini
    llm_provider: str = "openai"

    # LLM credentials / model
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: Optional[str] = None   # Leave blank — auto-resolved from llm_provider
    llm_temperature: float = 0.2
    llm_max_tokens: int = 4096

    # Jira MCP
    jira_mcp_url: Optional[str] = None
    jira_base_url: Optional[str] = None
    jira_api_token: Optional[str] = None
    jira_email: Optional[str] = None
    jira_project_key: str = "PROJ"
    use_mock_jira: bool = True
    jira_webhook_secret: str = ""  # shared secret for header validation

    # GitHub MCP
    github_mcp_url: Optional[str] = None
    github_token: Optional[str] = None
    github_repo_owner: Optional[str] = None
    github_repo_name: Optional[str] = None
    github_automation_repo: Optional[str] = None
    use_mock_github: bool = True

    # Output paths
    output_base_path: str = "outputs"
    reports_path: str = "outputs/reports"
    testcases_path: str = "outputs/testcases"
    bdd_path: str = "outputs/bdd"
    db_path: str = "outputs/history.db"

    # CRFLT project / teams
    crflt_project_key: str = "CRFLT"
    default_team: str = "statements"
    jira_project_key: str = "CRFLT"   # override keeps existing code working

    # Report
    report_template_path: str = "templates/report_template.html"


settings = Settings()
