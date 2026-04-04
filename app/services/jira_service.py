import base64
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings
from app.models.schemas import JiraTicket
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Team → Jira Component mapping  (CRFLT project — Client Reporting)
# To add a new team: add a key here and in config/jira/jira_filters.json
# ---------------------------------------------------------------------------
TEAM_COMPONENT_MAP: Dict[str, str] = {
    "statements": "CR-statements",
    "confirms": "CR-confirms",
    "letters": "CR-letters",
}

VALID_TEAMS = set(TEAM_COMPONENT_MAP.keys())

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

    async def create_issue(
        self,
        team_name: str,
        summary: str,
        description: str,
        issue_type: str = "Story",
        priority: str = "Medium",
        labels: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Create a Jira issue under the CRFLT project for the given team.

        The team name is automatically mapped to the correct Jira component so
        that the issue appears on the right Kanban board.

        Args:
            team_name:   One of 'statements', 'confirms', 'letters'.
            summary:     Issue summary / title (max 255 chars).
            description: Full description text (will be converted to ADF).
            issue_type:  Jira issue type (default 'Story').
            priority:    Jira priority (default 'Medium').
            labels:      Optional list of label strings.

        Returns:
            The newly created Jira issue key (e.g. 'CRFLT-42') or None on failure.

        Raises:
            ValueError: If team_name is not in TEAM_COMPONENT_MAP.
        """
        team_key = team_name.lower().strip()
        if team_key not in VALID_TEAMS:
            raise ValueError(
                f"Invalid team '{team_name}'. Valid teams: {sorted(VALID_TEAMS)}"
            )

        component = TEAM_COMPONENT_MAP[team_key]
        logger.info(
            f"Creating Jira issue for team '{team_key}' "
            f"(component={component}): {summary[:60]}"
        )

        if self.use_mock:
            mock_key = f"{settings.jira_project_key}-999"
            logger.info(
                f"[MOCK] Jira issue created: {mock_key} — "
                f"component={component}, summary={summary[:60]}"
            )
            return mock_key

        return await self._create_issue_api(
            summary=summary,
            description=description,
            component=component,
            issue_type=issue_type,
            priority=priority,
            labels=labels or [team_key],
        )


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

    async def _create_issue_api(
        self,
        summary: str,
        description: str,
        component: str,
        issue_type: str,
        priority: str,
        labels: List[str],
    ) -> Optional[str]:
        """POST to Jira REST API v3 to create an issue. Returns the issue key or None."""
        payload = {
            "fields": {
                "project": {"key": settings.jira_project_key},
                "summary": summary,
                "description": self._to_adf(description),
                "issuetype": {"name": issue_type},
                "priority": {"name": priority},
                "components": [{"name": component}],
                "labels": labels,
            }
        }
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.post(
                    f"{self._get_api_base()}/issue",
                    json=payload,
                    headers=self._auth_headers(with_body=True),
                )
                if resp.status_code not in (200, 201):
                    logger.error(
                        f"Jira issue creation failed ({resp.status_code}): {resp.text[:300]}"
                    )
                    return None
                issue_key = resp.json().get("key")
                logger.info(f"Jira issue created: {issue_key}")
                return issue_key
        except Exception as exc:
            logger.error(f"Error creating Jira issue: {exc}")
            return None

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

    @staticmethod
    def _to_adf(text: str) -> Dict[str, Any]:
        """Convert a plain/wiki-markup string to Atlassian Document Format (ADF).

        Jira REST API v3 requires ADF for comment bodies.
        Supports: *bold*, _italic_, plain text, multi-line.
        """
        import re

        def _parse_inline(line: str) -> list:
            nodes: list = []
            pattern = re.compile(r'(\*[^*]+\*|_[^_]+_)')
            pos = 0
            for m in pattern.finditer(line):
                before = line[pos:m.start()]
                if before:
                    nodes.append({"type": "text", "text": before})
                token = m.group(0)
                inner = token[1:-1]
                mark_type = "strong" if token.startswith("*") else "em"
                nodes.append({
                    "type": "text",
                    "text": inner,
                    "marks": [{"type": mark_type}],
                })
                pos = m.end()
            tail = line[pos:]
            if tail:
                nodes.append({"type": "text", "text": tail})
            return nodes or [{"type": "text", "text": line}]

        paragraphs = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                paragraphs.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": " "}],
                })
            else:
                paragraphs.append({
                    "type": "paragraph",
                    "content": _parse_inline(stripped),
                })

        if not paragraphs:
            paragraphs = [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]

        return {"version": 1, "type": "doc", "content": paragraphs}

    async def _post_comment(self, jira_id: str, comment: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.post(
                    f"{self._get_api_base()}/issue/{jira_id}/comment",
                    json={"body": self._to_adf(comment)},
                    headers=self._auth_headers(with_body=True),
                )
                if resp.status_code not in (200, 201):
                    logger.error(
                        f"Jira comment POST returned {resp.status_code} for {jira_id}: "
                        f"{resp.text[:300]}"
                    )
                    return False
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
