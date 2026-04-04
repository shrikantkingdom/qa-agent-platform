from typing import Any, Dict, List, Optional
import base64

import httpx

from app.config.settings import settings
from app.models.schemas import GitCommit
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Mock commit dataset — used when USE_MOCK_GITHUB=true (default)
# ---------------------------------------------------------------------------
_MOCK_COMMITS: List[Dict[str, Any]] = [
    {
        "sha": "abc1234def5678ab",
        "message": (
            "feat(auth): add Google OAuth2 login integration\n\n"
            "Implemented Google OAuth2 authorisation flow using the oauth2-client library.\n"
            "Added callback handler, user profile fetch, and session creation.\n"
            "Refs: PROJ-101"
        ),
        "author": "jane.doe",
        "date": "2026-03-10T09:30:00Z",
        "files_changed": [
            "src/auth/oauth2.py",
            "src/auth/google_provider.py",
            "src/routes/auth_routes.py",
            "src/models/user.py",
            "tests/test_google_oauth.py",
        ],
        "diff_summary": (
            "Added OAuth2 flow: authorisation URL builder, token exchange, "
            "user profile fetch, session creation. +320 lines, -12 lines."
        ),
    },
    {
        "sha": "def5678ghi9012cd",
        "message": (
            "feat(auth): add GitHub OAuth2 provider\n\n"
            "Added GitHub as second social login provider.\n"
            "Refs: PROJ-101"
        ),
        "author": "john.smith",
        "date": "2026-03-12T14:00:00Z",
        "files_changed": [
            "src/auth/github_provider.py",
            "src/routes/auth_routes.py",
            "tests/test_github_oauth.py",
        ],
        "diff_summary": "Added GitHub OAuth2 provider with token exchange and user linking. +145 lines.",
    },
    {
        "sha": "ghi9012jkl3456ef",
        "message": (
            "fix(auth): handle expired OAuth token edge case\n\n"
            "Fixed silent failure when token was revoked externally.\n"
            "Refs: PROJ-101"
        ),
        "author": "jane.doe",
        "date": "2026-03-14T11:00:00Z",
        "files_changed": ["src/auth/oauth2.py", "tests/test_token_refresh.py"],
        "diff_summary": "Proper error handling for revoked tokens; user is prompted to re-authenticate. +28 -5 lines.",
    },
]


class GitHubService:
    def __init__(self) -> None:
        self.use_mock = settings.use_mock_github
        self.token = settings.github_token
        self.owner = settings.github_repo_owner
        self.repo = self._bare_repo_name(settings.github_repo_name)

    @staticmethod
    def _bare_repo_name(value: Optional[str]) -> Optional[str]:
        """Accept 'repo-name' or 'https://github.com/owner/repo-name'."""
        if not value:
            return value
        # Strip trailing slash, then take last path segment
        return value.rstrip("/").split("/")[-1] or value

    async def get_commits_from_jira(self, jira_id: str) -> List[GitCommit]:
        logger.info(f"Fetching commits linked to: {jira_id}")
        if self.use_mock:
            return [GitCommit(**c) for c in _MOCK_COMMITS]
        return await self._fetch_commits(jira_id)

    async def get_diff(self, commit_sha: str) -> Optional[str]:
        logger.info(f"Fetching diff for commit: {commit_sha}")
        if self.use_mock:
            return f"[MOCK diff for {commit_sha}]"
        return await self._fetch_diff(commit_sha)

    async def create_pr(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        repo_name: Optional[str] = None,
    ) -> Optional[str]:
        target = self._bare_repo_name(repo_name or settings.github_automation_repo)
        logger.info(f"Creating PR '{title}' in {target}")
        if self.use_mock:
            logger.info(f"[MOCK] PR would be created: {title}")
            return "https://github.com/org/automation-repo/pull/42"
        return await self._create_pr(title, body, head_branch, base_branch, target)

    # ------------------------------------------------------------------ #
    # Real API calls                                                        #
    # ------------------------------------------------------------------ #

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _fetch_commits(self, jira_id: str) -> List[GitCommit]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"https://api.github.com/search/commits",
                    params={"q": f"{jira_id} repo:{self.owner}/{self.repo}"},
                    headers=self._auth_headers(),
                )
                resp.raise_for_status()
                items = resp.json().get("items", [])
                return [self._parse_commit(c) for c in items]
        except httpx.HTTPError as exc:
            logger.error(f"GitHub commits error for {jira_id}: {exc}")
            return []

    async def _fetch_diff(self, sha: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"https://api.github.com/repos/{self.owner}/{self.repo}/commits/{sha}",
                    headers={
                        **self._auth_headers(),
                        "Accept": "application/vnd.github.v3.diff",
                    },
                )
                resp.raise_for_status()
                return resp.text
        except httpx.HTTPError as exc:
            logger.error(f"GitHub diff error for {sha}: {exc}")
            return None

    async def _create_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str,
        repo: Optional[str],
    ) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"https://api.github.com/repos/{self.owner}/{repo}/pulls",
                    json={"title": title, "body": body, "head": head, "base": base},
                    headers=self._auth_headers(),
                )
                resp.raise_for_status()
                return resp.json().get("html_url")
        except httpx.HTTPError as exc:
            logger.error(f"GitHub PR creation failed: {exc}")
            return None

    async def push_playwright_test_file(
        self,
        jira_id: str,
        file_content: str,
        create_pr: bool = True,
        branch_prefix: str = "qa-agent",
    ) -> Dict[str, Any]:
        """Push a generated Playwright test file to the automation repo.

        Returns a dict with keys:
          - branch (str)
          - file_path (str) — path inside the repo
          - pr_url (Optional[str]) — URL of the PR if created
          - html_url (str) — direct GitHub link to the file
        """
        auto_repo = self._bare_repo_name(settings.github_automation_repo)
        branch = f"{branch_prefix}/{jira_id.lower()}"
        file_path = f"tests/qa_generated/test_{jira_id.lower().replace('-', '_')}.py"

        if self.use_mock:
            logger.info(f"[MOCK] Would push {file_path} to branch {branch} in {auto_repo}")
            mock_pr = f"https://github.com/{self.owner}/{auto_repo}/pull/99" if create_pr else None
            return {
                "branch": branch,
                "file_path": file_path,
                "pr_url": mock_pr,
                "html_url": f"https://github.com/{self.owner}/{auto_repo}/blob/{branch}/{file_path}",
            }

        result: Dict[str, Any] = {"branch": branch, "file_path": file_path, "pr_url": None}

        try:
            # 1. Get default branch SHA to base the new branch on
            base_sha = await self._get_default_branch_sha(auto_repo)
            if not base_sha:
                raise RuntimeError(f"Could not determine default branch SHA for {auto_repo}")

            # 2. Create branch (ignore 422 if it already exists)
            await self._create_branch(auto_repo, branch, base_sha)

            # 3. Upsert the file
            html_url = await self._upsert_file(auto_repo, branch, file_path, file_content, jira_id)
            result["html_url"] = html_url or ""

            # 4. Optionally open a PR
            if create_pr:
                pr_url = await self._create_pr(
                    title=f"[QA Agent] Add generated tests for {jira_id}",
                    body=(
                        f"Auto-generated Playwright tests for **{jira_id}**.\n\n"
                        "Generated by QA Agent Platform. Please review before merging."
                    ),
                    head=branch,
                    base="main",
                    repo=auto_repo,
                )
                result["pr_url"] = pr_url

        except Exception as exc:
            logger.error(f"push_playwright_test_file failed: {exc}")
            raise

        return result

    async def _get_default_branch_sha(self, repo: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"https://api.github.com/repos/{self.owner}/{repo}",
                    headers=self._auth_headers(),
                )
                resp.raise_for_status()
                default_branch = resp.json().get("default_branch", "main")
                resp2 = await client.get(
                    f"https://api.github.com/repos/{self.owner}/{repo}/git/ref/heads/{default_branch}",
                    headers=self._auth_headers(),
                )
                resp2.raise_for_status()
                return resp2.json()["object"]["sha"]
        except Exception as exc:
            logger.error(f"_get_default_branch_sha error: {exc}")
            return None

    async def _create_branch(self, repo: str, branch: str, sha: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"https://api.github.com/repos/{self.owner}/{repo}/git/refs",
                    json={"ref": f"refs/heads/{branch}", "sha": sha},
                    headers=self._auth_headers(),
                )
                if resp.status_code == 422:
                    logger.info(f"Branch {branch} already exists — reusing")
                    return
                resp.raise_for_status()
        except Exception as exc:
            logger.error(f"_create_branch error: {exc}")
            raise

    async def _upsert_file(
        self, repo: str, branch: str, path: str, content: str, jira_id: str
    ) -> Optional[str]:
        """Create or update a file; returns its html_url."""
        encoded = base64.b64encode(content.encode()).decode()
        payload: Dict[str, Any] = {
            "message": f"feat(qa): add generated tests for {jira_id}",
            "content": encoded,
            "branch": branch,
        }
        # Check if file already exists (get its SHA for updates)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                check = await client.get(
                    f"https://api.github.com/repos/{self.owner}/{repo}/contents/{path}",
                    params={"ref": branch},
                    headers=self._auth_headers(),
                )
                if check.status_code == 200:
                    payload["sha"] = check.json().get("sha")
        except Exception:
            pass

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.put(
                    f"https://api.github.com/repos/{self.owner}/{repo}/contents/{path}",
                    json=payload,
                    headers=self._auth_headers(),
                )
                resp.raise_for_status()
                return resp.json().get("content", {}).get("html_url")
        except Exception as exc:
            logger.error(f"_upsert_file error: {exc}")
            return None

    def _parse_commit(self, raw: Dict[str, Any]) -> GitCommit:
        commit = raw.get("commit", {})
        return GitCommit(
            sha=raw.get("sha", "")[:16],
            message=commit.get("message", ""),
            author=(commit.get("author") or {}).get("name", "unknown"),
            date=(commit.get("author") or {}).get("date", ""),
            files_changed=[f.get("filename", "") for f in raw.get("files", [])],
        )


github_service = GitHubService()
