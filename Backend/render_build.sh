#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
python -m pip install -r requirements.txt

# Render's native Python runtime uses a non-root build user.  --with-deps tries
# to install Debian packages via su, which is not available there.  Debian 12 is
# a supported Playwright runtime, so download Chromium into the deploy artifact
# and verify that the runtime-provided libraries can launch it headlessly.
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$PWD/.playwright-browsers}"
python -m playwright install chromium
python - <<'PY'
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    )
    browser.close()
PY
