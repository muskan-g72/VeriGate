import asyncio
import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def verify_github_signature(payload_bytes: bytes, signature_header: str | None, secret: str | None = None) -> bool:
    if not signature_header:
        return False
    candidates = [item.strip() for item in (secret, settings.github_webhook_secret) if item and item.strip()]
    if not candidates or not signature_header.strip().lower().startswith("sha256="):
        return False
    received = signature_header.strip()[7:]
    return any(hmac.compare_digest(hmac.new(item.encode(), payload_bytes, hashlib.sha256).hexdigest(), received) for item in candidates)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


async def post_github_commit_status(repo: str, commit_sha: str, state: str, description: str, target_url: str | None = None, context: str = "verigate/verification", token: str | None = None) -> bool:
    github_token = token or settings.github_token
    if not github_token or not repo or not commit_sha:
        return False
    payload: dict[str, Any] = {"state": state, "description": (description or "")[:140], "context": context}
    if target_url:
        payload["target_url"] = target_url
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{settings.github_api_url.rstrip('/')}/repos/{repo}/statuses/{commit_sha}", json=payload, headers=_headers(github_token))
        if response.status_code in {200, 201}:
            return True
        logger.warning("GitHub status update returned %s: %s", response.status_code, response.text[:200])
    except Exception as exc:
        logger.warning("Failed to post GitHub commit status: %s", exc)
    return False


async def _comment_request(method: str, url: str, payload: dict | None = None, retries: int = 1) -> tuple[Any | None, int, str]:
    token = settings.github_token
    if not token:
        return None, 0, "GITHUB_TOKEN is not configured"
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(method, url, json=payload, headers=_headers(token))
            if response.status_code in {200, 201}:
                return response.json(), response.status_code, ""
            if response.status_code >= 500 and attempt < retries:
                await asyncio.sleep(.25)
                continue
            return None, response.status_code, f"GitHub returned {response.status_code}: {response.text[:180]}"
        except Exception as exc:
            if attempt < retries:
                await asyncio.sleep(.25)
                continue
            return None, 0, str(exc)
    return None, 0, "GitHub comment request failed"


async def create_github_pr_comment(repo: str, pr_number: int, body: str) -> tuple[dict | None, int, str]:
    return await _comment_request("POST", f"{settings.github_api_url.rstrip('/')}/repos/{repo}/issues/{pr_number}/comments", {"body": body})


async def update_github_pr_comment(repo: str, comment_id: int, body: str) -> tuple[dict | None, int, str]:
    return await _comment_request("PATCH", f"{settings.github_api_url.rstrip('/')}/repos/{repo}/issues/comments/{comment_id}", {"body": body})


async def find_github_pr_comment(repo: str, pr_number: int, marker: str, max_pages: int = 3) -> tuple[dict | None, int, str]:
    for page in range(1, max_pages + 1):
        data, status, error = await _comment_request("GET", f"{settings.github_api_url.rstrip('/')}/repos/{repo}/issues/{pr_number}/comments?per_page=100&page={page}", retries=0)
        if data is None:
            return None, status, error
        for comment in data:
            if marker in (comment.get("body") or ""):
                return comment, status, ""
        if len(data) < 100:
            break
    return None, 404, ""
