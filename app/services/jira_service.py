import base64
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings
from app.models.schemas import JiraTicket
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Mock ticket library — used when USE_MOCK_JIRA=true (default)
# ---------------------------------------------------------------------------
_MOCK_TICKETS: Dict[str, Dict[str, Any]] = {
    "_default": {
        "id": "PROJ-101",
        "summary": "Implement user login with OAuth2 (Google + GitHub)",
        "description": (
            "As a user, I want to log in using my Google or GitHub account "
            "so that I do not need a separate application password.\n\n"
            "## Background\n"
            "Currently users must maintain a local account. Adding social login "
            "reduces friction and improves onboarding conversion.\n\n"
            "## Scope\n"
            "- Integrate Google OAuth2 flow\n"
            "- Integrate GitHub OAuth2 flow\n"
            "- Create/link user profiles on first login\n"
            "- Handle edge cases: denied permission, revoked tokens, concurrent sessions"
        ),
        "acceptance_criteria": (
            "- User can click 'Login with Google' and complete OAuth2 authentication\n"
            "- User can click 'Login with GitHub' and complete OAuth2 authentication\n"
            "- Successful auth redirects user to the dashboard with a welcome message\n"
            "- Failed/denied auth shows an appropriate, user-friendly error message\n"
            "- Session expires after 8 hours of inactivity\n"
            "- CSRF state parameter is validated on callback"
        ),
        "assignee": "jane.doe@company.com",
        "reporter": "product.owner@company.com",
        "status": "In Progress",
        "priority": "High",
        "story_points": 8,
        "labels": ["authentication", "oauth2", "security"],
        "components": ["Backend", "Frontend"],
        "linked_commits": ["abc1234", "def5678", "ghi9012"],
        "created_at": "2026-03-01T10:00:00Z",
        "updated_at": "2026-03-28T14:30:00Z",
    }
}


class JiraService:
    def __init__(self) -> None:
        self.base_url = settings.jira_base_url
        self.use_mock = settings.use_mock_jira

    async def get_ticket(self, jira_id: str) -> Optional[JiraTicket]:
        logger.info(f"Fetching Jira ticket: {jira_id}")
        if self.use_mock:
            return self._mock_ticket(jira_id)
        return await self._fetch_from_api(jira_id)

    async def get_release_tickets(self, release: str) -> List[JiraTicket]:
        logger.info(f"Fetching tickets for release: {release}")
        if self.use_mock:
            ticket = self._mock_ticket(f"{settings.jira_project_key}-101")
            return [ticket]
        return await self._search_by_release(release)

    async def add_comment(self, jira_id: str, comment: str) -> bool:
        logger.info(f"Posting comment to Jira ticket: {jira_id}")
        if self.use_mock:
            logger.info(f"[MOCK] Comment posted to {jira_id}: {comment[:80]}…")
            return True
        return await self._post_comment(jira_id, comment)

    async def attach_file(self, jira_id: str, file_path: str) -> bool:
        logger.info(f"Attaching file to Jira ticket: {jira_id}")
        if self.use_mock:
            logger.info(f"[MOCK] Attachment {file_path} → {jira_id}")
            return True
        return await self._post_attachment(jira_id, file_path)

    # ------------------------------------------------------------------ #
    # Mock helpers                                                          #
    # ------------------------------------------------------------------ #

    def _mock_ticket(self, jira_id: str) -> JiraTicket:
        data = _MOCK_TICKETS.get(jira_id, _MOCK_TICKETS["_default"]).copy()
        data["id"] = jira_id
        return JiraTicket(**data)

    # ------------------------------------------------------------------ #
    # Real API calls                                                        #
    # ------------------------------------------------------------------ #

    def _get_api_base(self) -> str:
        """Return a normalised Jira REST API v3 base URL (no trailing slash)."""
        base = (self.base_url or "").rstrip("/")
        # If the user only supplied the site root, append the REST API path
        if "/rest/api/" not in base:
            base = f"{base}/rest/api/3"
        return base

    def _auth_headers(self, *, with_body: bool = False) -> Dict[str, str]:
        """Build auth headers.  Only add Content-Type for requests that send a body."""
        token = base64.b64encode(
            f"{settings.jira_email}:{settings.jira_api_token}".encode()
        ).decode()
        headers: Dict[str, str] = {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
        }
        if with_body:
            headers["Content-Type"] = "application/json"
        return headers

    async def _fetch_from_api(self, jira_id: str) -> Optional[JiraTicket]:
        url = f"{self._get_api_base()}/issue/{jira_id}"
        logger.info(f"Jira API GET: {url}")
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=self._auth_headers())

                if resp.status_code == 404:
                    logger.error(f"Jira ticket not found (404): {jira_id}")
                    return None
                if resp.status_code == 401:
                    logger.error("Jira authentication failed — check JIRA_EMAIL and JIRA_API_TOKEN")
                    return None
                resp.raise_for_status()
                return self._parse_response(resp.json())
        except httpx.HTTPStatusError as exc:
            logger.error(f"Jira HTTP error {exc.response.status_code} for {jira_id}: {exc}")
            return None
        except httpx.HTTPError as exc:
            logger.error(f"Jira connection error for {jira_id}: {exc}")
            return None
        except Exception as exc:
            logger.error(f"Unexpected error fetching Jira ticket {jira_id}: {exc}")
            return None

    async def _search_by_release(self, release: str) -> List[JiraTicket]:
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(
                    f"{self._get_api_base()}/search/jql",
                    params={"jql": f"fixVersion='{release}'", "maxResults": 50},
                    headers=self._auth_headers(),
                )
                resp.raise_for_status()
                return [self._parse_response(i) for i in resp.json().get("issues", [])]
        except Exception as exc:
            logger.error(f"Jira search error for release {release}: {exc}")
            return []

    async def _post_comment(self, jira_id: str, comment: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.post(
                    f"{self._get_api_base()}/issue/{jira_id}/comment",
                    json={"body": comment},
                    headers=self._auth_headers(with_body=True),
                )
                resp.raise_for_status()
                return True
        except Exception as exc:
            logger.error(f"Failed to post comment to {jira_id}: {exc}")
            return False

    async def _post_attachment(self, jira_id: str, file_path: str) -> bool:
        try:
            with open(file_path, "rb") as fh:
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    resp = await client.post(
                        f"{self._get_api_base()}/issue/{jira_id}/attachments",
                        files={"file": fh},
                        headers={
                            **self._auth_headers(),
                            "X-Atlassian-Token": "no-check",
                        },
                    )
                    resp.raise_for_status()
                    return True
        except Exception as exc:
            logger.error(f"Failed to attach file to {jira_id}: {exc}")
            return False

    @staticmethod
    def _adf_to_text(node: Any, depth: int = 0) -> str:
        """Recursively extract plain text from an Atlassian Document Format node."""
        if node is None:
            return ""
        if isinstance(node, str):
            return node
        if isinstance(node, dict):
            node_type = node.get("type", "")
            # Leaf text node
            if node_type == "text":
                return node.get("text", "")
            # Separator for certain block nodes
            sep = "\n" if node_type in ("paragraph", "heading", "bulletList",
                                        "orderedList", "listItem", "blockquote",
                                        "codeBlock", "rule", "panel") else ""
            parts = [JiraService._adf_to_text(child, depth + 1)
                     for child in node.get("content", [])]
            return sep + "".join(parts)
        if isinstance(node, list):
            return "".join(JiraService._adf_to_text(item, depth) for item in node)
        return str(node)

    @staticmethod
    def _extract_acceptance_criteria(description_text: str, fields: Dict[str, Any]) -> str:
        """Try to pull acceptance criteria from known custom fields or the description."""
        # Some teams put AC in customfield_10034 or similar; try common ones first
        for cf in ("customfield_10034", "customfield_10035", "customfield_10036"):
            val = fields.get(cf)
            if isinstance(val, str) and val.strip():
                return val.strip()
            if isinstance(val, dict):
                text = JiraService._adf_to_text(val).strip()
                if text:
                    return text
        # Fall back: extract the section after "Acceptance Criteria" in the description
        import re
        match = re.search(
            r"(?:acceptance criteria|ac)[:\s]*\n(.*?)(?:\n##|\n\*\*|\Z)",
            description_text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return ""

    def _parse_response(self, raw: Dict[str, Any]) -> JiraTicket:
        fields = raw.get("fields", {})

        # description: real Jira returns ADF dict; convert to plain text
        raw_desc = fields.get("description")
        description = (
            self._adf_to_text(raw_desc).strip()
            if isinstance(raw_desc, dict)
            else (raw_desc or "")
        )

        acceptance_criteria = self._extract_acceptance_criteria(description, fields)
        # story_points lives in customfield_10016 (float or None)
        sp_raw = fields.get("customfield_10016")
        story_points = int(sp_raw) if sp_raw is not None else None

        return JiraTicket(
            id=raw.get("key", ""),
            summary=fields.get("summary", ""),
            description=description,
            acceptance_criteria=acceptance_criteria,
            assignee=(fields.get("assignee") or {}).get("emailAddress"),
            reporter=(fields.get("reporter") or {}).get("emailAddress"),
            status=(fields.get("status") or {}).get("name"),
            priority=(fields.get("priority") or {}).get("name"),
            story_points=story_points,
            labels=fields.get("labels", []),
            components=[c.get("name", "") for c in fields.get("components", [])],
            created_at=fields.get("created"),
            updated_at=fields.get("updated"),
        )


jira_service = JiraService()
