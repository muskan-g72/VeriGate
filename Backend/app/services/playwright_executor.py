import base64
import time
import traceback
from typing import Any

from playwright.async_api import async_playwright


async def execute_playwright_test(
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    started_at = time.perf_counter()

    result: dict[str, Any] = {
        "status": "passed",
        "actual_result": "Test passed",
        "failure_message": None,
        "stack_trace": None,
        "duration": 0.0,
        "screenshot": None,
    }

    browser = None
    page = None

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True
            )

            page = await browser.new_page()

            try:
                for step_number, step in enumerate(
                    steps,
                    start=1,
                ):
                    if not isinstance(step, dict):
                        raise ValueError(
                            f"Step {step_number} must be a JSON object"
                        )

                    action = step.get("action")
                    selector = step.get("selector")
                    value = step.get("value")

                    if not action:
                        raise ValueError(
                            f"Step {step_number} is missing 'action'"
                        )

                    if action == "goto":
                        if not value:
                            raise ValueError(
                                f"Step {step_number}: "
                                "'goto' requires 'value'"
                            )

                        await page.goto(
                            str(value),
                            wait_until="networkidle",
                        )

                    elif action == "click":
                        if not selector:
                            raise ValueError(
                                f"Step {step_number}: "
                                "'click' requires 'selector'"
                            )

                        await page.locator(selector).click()

                    elif action == "fill":
                        if not selector:
                            raise ValueError(
                                f"Step {step_number}: "
                                "'fill' requires 'selector'"
                            )

                        if value is None:
                            raise ValueError(
                                f"Step {step_number}: "
                                "'fill' requires 'value'"
                            )

                        await page.locator(selector).fill(
                            str(value)
                        )

                    elif action == "expect_text":
                        if value is None:
                            raise ValueError(
                                f"Step {step_number}: "
                                "'expect_text' requires 'value'"
                            )

                        await page.get_by_text(
                            str(value)
                        ).wait_for()

                    elif action == "expect_title":
                        if value is None:
                            raise ValueError(
                                f"Step {step_number}: "
                                "'expect_title' requires 'value'"
                            )

                        actual_title = await page.title()

                        if actual_title != str(value):
                            raise AssertionError(
                                f"Expected title '{value}', "
                                f"but got '{actual_title}'"
                            )

                    else:
                        raise ValueError(
                            f"Unsupported Playwright action: {action}"
                        )

            except Exception as exc:
                result["status"] = "failed"
                result["actual_result"] = "Test failed"
                result["failure_message"] = (
                    str(exc)
                    or exc.__class__.__name__
                )
                result["stack_trace"] = traceback.format_exc()

                if page is not None:
                    try:
                        screenshot_bytes = await page.screenshot(
                            type="png",
                            full_page=True,
                        )

                        result["screenshot"] = (
                            base64.b64encode(
                                screenshot_bytes
                            ).decode("utf-8")
                        )

                    except Exception:
                        result["stack_trace"] += (
                            "\n\nScreenshot capture failed:\n"
                            + traceback.format_exc()
                        )

            finally:
                result["duration"] = round(
                    time.perf_counter() - started_at,
                    3,
                )

    except Exception as exc:
        result["status"] = "failed"
        result["actual_result"] = "Test failed"
        result["failure_message"] = (
            str(exc)
            or exc.__class__.__name__
        )
        result["stack_trace"] = traceback.format_exc()
        result["duration"] = round(
            time.perf_counter() - started_at,
            3,
        )

    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass

    return result