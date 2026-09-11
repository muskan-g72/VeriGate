import asyncio
import base64
import sys
import time
import traceback
from typing import Any

from playwright.async_api import async_playwright


async def _execute_playwright_steps(
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
                    if value is None:
                        if action == "goto":
                            value = step.get("url")
                        elif action in {"expect_title", "expect_text"}:
                            value = step.get("text")

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
                        result["actual_result"] = f"Navigated to {value}"

                    elif action == "click":
                        if not selector:
                            raise ValueError(
                                f"Step {step_number}: "
                                "'click' requires 'selector'"
                            )

                        await page.locator(selector).click()
                        result["actual_result"] = f"Clicked {selector}"

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
                        result["actual_result"] = f"Filled {selector}"

                    elif action == "expect_text":
                        if value is None:
                            raise ValueError(
                                f"Step {step_number}: "
                                "'expect_text' requires 'value'"
                            )

                        if selector:
                            await page.locator(selector).wait_for()
                            text_content = await page.locator(
                                selector
                            ).text_content()
                            if str(value) not in (text_content or ""):
                                raise AssertionError(
                                    f"Expected text '{value}' in selector '{selector}', "
                                    f"but got '{text_content}'"
                                )
                        else:
                            await page.get_by_text(
                                str(value)
                            ).wait_for()

                        result["actual_result"] = f"Found text '{value}'"

                    elif action == "expect_title":
                        if value is None:
                            raise ValueError(
                                f"Step {step_number}: "
                                "'expect_title' requires 'value'"
                            )

                        actual_title = await page.title()
                        result["actual_result"] = f"Page title is '{actual_title}'"

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
                if result["actual_result"] == "Test passed":
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


def _run_in_proactor_thread(
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_execute_playwright_steps(steps))
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()


async def execute_playwright_test(
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    if sys.platform == "win32" and not isinstance(
        loop, getattr(asyncio, "ProactorEventLoop", ())
    ):
        return await loop.run_in_executor(None, _run_in_proactor_thread, steps)
    return await _execute_playwright_steps(steps)