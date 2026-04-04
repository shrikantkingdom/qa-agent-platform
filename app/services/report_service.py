from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config.settings import settings
from app.models.schemas import QAWorkflowResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReportService:
    def __init__(self) -> None:
        template_dir = Path(settings.report_template_path).parent
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html"]),
        )

    def generate_html_report(self, result: QAWorkflowResult) -> str:
        template_file = Path(settings.report_template_path).name
        template = self._env.get_template(template_file)

        html = template.render(
            result=result,
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

        output_path = Path(settings.reports_path) / f"{result.jira_id}_report.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

        logger.info(f"HTML report → {output_path}")
        return str(output_path)


report_service = ReportService()
