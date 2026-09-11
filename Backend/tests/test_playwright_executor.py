import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.playwright_executor import (
    _execute_playwright_steps,
    execute_playwright_test,
)


def test_execute_playwright_steps_success() -> None:
    async def _run():
        mock_page = AsyncMock()
        mock_page.title.return_value = "Example Domain"

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_playwright

        with patch(
            "app.services.playwright_executor.async_playwright",
            return_value=mock_cm,
        ):
            steps = [
                {"action": "goto", "value": "https://example.com"},
                {"action": "expect_title", "value": "Example Domain"},
            ]
            result = await _execute_playwright_steps(steps)

        assert result["status"] == "passed"
        assert result["failure_message"] is None
        assert "Example Domain" in result["actual_result"]
        assert result["screenshot"] is None
        mock_browser.close.assert_awaited_once()

    asyncio.run(_run())


def test_execute_playwright_steps_assertion_failure() -> None:
    async def _run():
        mock_page = AsyncMock()
        mock_page.title.return_value = "Example Domain"
        mock_page.screenshot.return_value = b"fake_screenshot_bytes"

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_playwright

        with patch(
            "app.services.playwright_executor.async_playwright",
            return_value=mock_cm,
        ):
            steps = [
                {"action": "goto", "value": "https://example.com"},
                {"action": "expect_title", "value": "Wrong Title"},
            ]
            result = await _execute_playwright_steps(steps)

        assert result["status"] == "failed"
        assert "Expected title 'Wrong Title', but got 'Example Domain'" in result["failure_message"]
        assert "Example Domain" in result["actual_result"]
        assert result["screenshot"] is not None
        assert result["stack_trace"] is not None
        mock_browser.close.assert_awaited_once()

    asyncio.run(_run())


def test_execute_playwright_steps_supports_url_and_text_aliases() -> None:
    async def _run():
        mock_page = AsyncMock()
        mock_page.title.return_value = "My Page"

        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_playwright

        with patch(
            "app.services.playwright_executor.async_playwright",
            return_value=mock_cm,
        ):
            steps = [
                {"action": "goto", "url": "https://example.com"},
                {"action": "expect_title", "text": "My Page"},
            ]
            result = await _execute_playwright_steps(steps)

        assert result["status"] == "passed"
        assert result["failure_message"] is None
        mock_page.goto.assert_awaited_once_with(
            "https://example.com", wait_until="networkidle"
        )

    asyncio.run(_run())


def test_execute_playwright_steps_missing_action() -> None:
    async def _run():
        result = await _execute_playwright_steps([{"value": "no-action"}])
        assert result["status"] == "failed"
        assert "missing 'action'" in result["failure_message"]

    asyncio.run(_run())


def test_execute_playwright_steps_unsupported_action() -> None:
    async def _run():
        result = await _execute_playwright_steps([{"action": "fly_to_moon"}])
        assert result["status"] == "failed"
        assert "Unsupported Playwright action" in result["failure_message"]

    asyncio.run(_run())


def test_execute_playwright_test_selector_loop_delegation() -> None:
    """
    Regression test for the Windows NotImplementedError bug:
    Verifies that when running on a SelectorEventLoop, execute_playwright_test
    delegates execution to the proactor worker thread.
    """
    fake_result = {
        "status": "passed",
        "actual_result": "Test passed",
        "failure_message": None,
        "stack_trace": None,
        "duration": 0.1,
        "screenshot": None,
    }

    async def _run():
        with patch("sys.platform", "win32"), patch(
            "app.services.playwright_executor._run_in_proactor_thread",
            return_value=fake_result,
        ) as mock_proactor_thread:
            # Mock loop as SelectorEventLoop (not ProactorEventLoop)
            mock_loop = MagicMock()
            mock_loop.__class__ = asyncio.SelectorEventLoop

            async def fake_run_in_executor(executor, func, *args):
                return func(*args)

            mock_loop.run_in_executor = AsyncMock(side_effect=fake_run_in_executor)

            with patch("asyncio.get_running_loop", return_value=mock_loop):
                steps = [{"action": "goto", "value": "https://example.com"}]
                res = await execute_playwright_test(steps)

            assert res["status"] == "passed"
            mock_proactor_thread.assert_called_once_with(steps)

    asyncio.run(_run())
