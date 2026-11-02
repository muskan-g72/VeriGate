"""Send a clearly labelled, locally simulated GitHub pull_request delivery.

Default mode exercises parsing, project lookup, and HMAC validation without
creating a verification run: it sends the unsupported `closed` PR action. Pass
`--trigger` only when the local backend has no GITHUB_TOKEN configured; that mode
uses `opened` and queues the normal local verification workflow.

Usage (PowerShell):
  $env:GITHUB_WEBHOOK_SECRET = 'the same secret configured for the project/backend'
  python Backend/scripts/send_local_github_webhook.py
  $env:LOCAL_WEBHOOK_TRIGGER_ACK = 'I_UNDERSTAND'
  python Backend/scripts/send_local_github_webhook.py --trigger
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request
import uuid


DEFAULT_URL = "http://127.0.0.1:8000/api/v1/github/webhook"
TEST_PR_NUMBER = 987654


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a local-only signed VeriGate webhook simulation.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Local FastAPI webhook URL")
    parser.add_argument("--trigger", action="store_true", help="Use the supported opened action and queue a local verification run")
    args = parser.parse_args()

    secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    if not secret:
        print("GITHUB_WEBHOOK_SECRET is required; it is never read from or written to this script.", file=sys.stderr)
        return 2
    if args.trigger:
        if os.environ.get("GITHUB_TOKEN") or os.environ.get("LOCAL_WEBHOOK_TRIGGER_ACK") != "I_UNDERSTAND":
            print("Refusing --trigger. Confirm the backend has no GITHUB_TOKEN and set LOCAL_WEBHOOK_TRIGGER_ACK=I_UNDERSTAND.", file=sys.stderr)
            return 2

    action = "opened" if args.trigger else "closed"
    payload = {
        "action": action,
        "number": TEST_PR_NUMBER,
        "repository": {"full_name": "muskan-g72/VeriGate", "private": False},
        "pull_request": {
            "number": TEST_PR_NUMBER,
            "title": "[LOCAL WEBHOOK SIMULATION — DO NOT MERGE]",
            "html_url": "https://github.com/muskan-g72/VeriGate/pull/987654",
            "state": "open",
            "user": {"login": "verigate-local-simulator"},
            "head": {"ref": "local-webhook-test", "sha": "0123456789abcdef0123456789abcdef01234567"},
            "base": {"ref": "main"},
        },
        "sender": {"login": "verigate-local-simulator"},
    }
    # Sign the exact bytes supplied as HTTP content, as GitHub does.
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    delivery_id = f"local-simulation-{uuid.uuid4()}"
    request = urllib.request.Request(
        args.url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": delivery_id,
            "X-Hub-Signature-256": signature,
            "User-Agent": "VeriGate-local-webhook-simulator",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            print(f"LOCAL SIMULATION ONLY: HTTP {response.status}")
            print(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        print(f"LOCAL SIMULATION ONLY: HTTP {error.code}", file=sys.stderr)
        print(error.read().decode("utf-8"), file=sys.stderr)
        return 1
    except urllib.error.URLError as error:
        print(f"Could not reach local FastAPI backend at {args.url}: {error.reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
