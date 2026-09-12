import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def verify_github_signature(
    payload_bytes: bytes,
    signature_header: str | None,
    secret: str | None = None,
) -> bool:
    """
    Validate GitHub webhook payload using HMAC-SHA256 signature.
    Timing-attack safe via hmac.compare_digest.
    Supports candidate secrets from project record and global settings.github_webhook_secret.
    """
    candidate_secrets: list[str] = []
    if secret:
        candidate_secrets.append(secret)
    if settings.github_webhook_secret and settings.github_webhook_secret not in candidate_secrets:
        candidate_secrets.append(settings.github_webhook_secret)

    if not candidate_secrets:
        if not signature_header:
            logger.info("GitHub webhook signature verification skipped: no secret configured.")
            return True
        logger.warning("No webhook secret configured to verify signature.")
        return False

    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header.")
        return False

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        logger.warning("Malformed X-Hub-Signature-256 format.")
        return False

    received_hash = signature_header[len(prefix) :].strip()

    for candidate in candidate_secrets:
        mac = hmac.new(
            candidate.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256,
        )
        expected_hash = mac.hexdigest()
        if hmac.compare_digest(received_hash, expected_hash):
            return True

    return False


async def post_github_commit_status(
    repo: str,
    commit_sha: str,
    state: str,
    description: str,
    target_url: str | None = None,
    context: str = "verigate/verification",
    token: str | None = None,
) -> bool:
    """
    Publish a commit status check to GitHub (pending, success, failure, error).
    Fails safely without breaking test execution if GitHub API is unreachable.
    """
    github_token = token or settings.github_token
    if not github_token:
        logger.info(
            "GitHub status update skipped: no GITHUB_TOKEN configured."
        )
        return False

    if not repo or not commit_sha:
        logger.warning("Missing repo or commit_sha for GitHub status update.")
        return False

    api_url = (
        f"{settings.github_api_url.rstrip('/')}/repos/{repo}/statuses/{commit_sha}"
    )
    payload: dict[str, Any] = {
        "state": state,
        "description": description[:140] if description else "",
        "context": context,
    }
    if target_url:
        payload["target_url"] = target_url

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)
            if response.status_code in {200, 201}:
                logger.info(
                    f"Posted GitHub commit status '{state}' to {repo}@{commit_sha[:7]}."
                )
                return True
            else:
                logger.warning(
                    f"GitHub status update returned {response.status_code}: {response.text[:200]}"
                )
                return False
    except Exception as exc:
        logger.warning(f"Failed to post GitHub commit status: {exc}")
        return False
