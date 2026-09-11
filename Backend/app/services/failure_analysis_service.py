import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.models.test_case import TestCase
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun
from app.schemas.failure_analysis import (
    FailureAnalysis,
    FailureCategory,
    VerificationRunAnalysisResponse,
)

logger = logging.getLogger(__name__)


def _extract_evidence_signals(
    result: VerificationResult,
    test_case: TestCase | None,
) -> list[str]:
    signals: list[str] = []
    if result.failure_message:
        signals.append("Failure message")
    if test_case and test_case.expected_result:
        signals.append("Expected result")
    if result.actual_result:
        signals.append("Actual result")
    if result.stack_trace:
        signals.append("Stack trace")
    if test_case and (test_case.steps or test_case.automation_steps):
        signals.append("Test steps")
    if result.evidence_items:
        signals.append(f"Evidence items ({len(result.evidence_items)})")
    return signals


def _heuristic_analyze_result(
    result: VerificationResult,
    test_case: TestCase | None,
    evidence_signals: list[str],
) -> FailureAnalysis:
    failure_msg = (result.failure_message or "").strip()
    stack = (result.stack_trace or "").strip()
    expected = (test_case.expected_result if test_case else "") or ""
    actual = (result.actual_result or "").strip()
    title = test_case.title if test_case else f"Test case {result.test_case_id}"
    combined_text = f"{failure_msg}\n{actual}\n{stack}"

    # 1. Expected title mismatch (Playwright expect_title)
    title_match = re.search(
        r"Expected title ['\"]([^'\"]+)['\"],?\s+but (?:got|received) ['\"]([^'\"]+)['\"]",
        combined_text,
        re.IGNORECASE,
    )
    if title_match:
        exp_val, act_val = title_match.group(1), title_match.group(2)
        return FailureAnalysis(
            test_case_id=result.test_case_id,
            test_case_title=title,
            result_id=result.id,
            status=result.status,
            root_cause=f"Page title mismatch: expected '{exp_val}', but received '{act_val}'.",
            failure_category="Assertion Failure",
            confidence=0.96,
            explanation=(
                f"The automated verification navigated to the target page and verified the document title. "
                f"The actual page title rendered was '{act_val}', which did not match the expected title '{exp_val}'."
            ),
            suggested_fix=(
                f"If the application title was intentionally updated to '{act_val}', update the test case's "
                f"expected result. Otherwise, verify that the test is navigating to the correct URL and that "
                f"the application deployed the expected page version."
            ),
            evidence_used=evidence_signals,
            analysis_source="heuristic_engine",
            analyzed_at=datetime.now(UTC),
        )

    # 2. General assertion error / mismatch
    if "AssertionError" in stack or "AssertionError" in failure_msg:
        return FailureAnalysis(
            test_case_id=result.test_case_id,
            test_case_title=title,
            result_id=result.id,
            status=result.status,
            root_cause=f"Assertion condition failed: {failure_msg or 'values did not match'}",
            failure_category="Assertion Failure",
            confidence=0.92,
            explanation=(
                f"The test assertion evaluated to false. Expected criteria: '{expected or 'N/A'}'. "
                f"Actual result recorded: '{actual or 'N/A'}'."
            ),
            suggested_fix=(
                "Compare the test expectation against the actual outcome. Determine whether application "
                "behavior changed or if test criteria need adjustment."
            ),
            evidence_used=evidence_signals,
            analysis_source="heuristic_engine",
            analyzed_at=datetime.now(UTC),
        )

    # 3. Authentication / Authorization Failure (401 / 403)
    if any(
        kw in combined_text.lower()
        for kw in ["401", "unauthorized", "403", "forbidden", "credentials", "invalid token"]
    ):
        return FailureAnalysis(
            test_case_id=result.test_case_id,
            test_case_title=title,
            result_id=result.id,
            status=result.status,
            root_cause="Authentication failed: credentials rejected or session token expired (HTTP 401/403).",
            failure_category="Authentication Failure",
            confidence=0.90,
            explanation=(
                "The target endpoint or authentication guard returned an unauthorized/forbidden response. "
                "The test either supplied invalid credentials, missing authentication headers, or an expired token."
            ),
            suggested_fix=(
                "Verify test user credentials in the database or test setup, ensure valid Bearer tokens are provided, "
                "and confirm the test account has the required role permissions."
            ),
            evidence_used=evidence_signals,
            analysis_source="heuristic_engine",
            analyzed_at=datetime.now(UTC),
        )

    # 4. Element Not Found / Selector Timeout
    if any(
        kw in combined_text.lower()
        for kw in ["locator.wait_for", "waiting for locator", "nosuchelement", "selector", "expect_text"]
    ):
        return FailureAnalysis(
            test_case_id=result.test_case_id,
            test_case_title=title,
            result_id=result.id,
            status=result.status,
            root_cause="Target UI element could not be found in the DOM within the configured timeout.",
            failure_category="Element Not Found",
            confidence=0.88,
            explanation=(
                "The Playwright browser engine attempted to locate and interact with an element, but the selector "
                "did not match any element in the active DOM before timing out."
            ),
            suggested_fix=(
                "Inspect the captured failure screenshot to see if the page rendered. Check the DOM selector "
                "for changes, and ensure dynamic elements have finished loading."
            ),
            evidence_used=evidence_signals,
            analysis_source="heuristic_engine",
            analyzed_at=datetime.now(UTC),
        )

    # 5. Execution Timeout
    if "timeouterror" in combined_text.lower() or "timed out" in combined_text.lower():
        return FailureAnalysis(
            test_case_id=result.test_case_id,
            test_case_title=title,
            result_id=result.id,
            status=result.status,
            root_cause="Operation exceeded execution timeout threshold.",
            failure_category="Timeout",
            confidence=0.85,
            explanation=(
                "The verification run exceeded the maximum allowed time waiting for a response, page navigation, "
                "or DOM state transition."
            ),
            suggested_fix=(
                "Check server responsiveness and network latency. Consider increasing the step timeout or optimizing "
                "slow database queries/API endpoints involved in the test."
            ),
            evidence_used=evidence_signals,
            analysis_source="heuristic_engine",
            analyzed_at=datetime.now(UTC),
        )

    # 6. Database Failure
    if any(
        kw in combined_text.lower()
        for kw in ["sqlalchemyerror", "operationalerror", "database connection failed", "psycopg", "postgresql"]
    ):
        return FailureAnalysis(
            test_case_id=result.test_case_id,
            test_case_title=title,
            result_id=result.id,
            status=result.status,
            root_cause="Database connection error or query execution failure.",
            failure_category="Database Failure",
            confidence=0.91,
            explanation="The application failed to communicate with the PostgreSQL database during test execution.",
            suggested_fix="Ensure PostgreSQL container is running, check DATABASE_URL credentials, and run pending Alembic migrations.",
            evidence_used=evidence_signals,
            analysis_source="heuristic_engine",
            analyzed_at=datetime.now(UTC),
        )

    # 7. Network / Connection Refused
    if any(
        kw in combined_text.lower()
        for kw in ["connectionrefused", "failed to connect", "net::err_", "econnrefused"]
    ):
        return FailureAnalysis(
            test_case_id=result.test_case_id,
            test_case_title=title,
            result_id=result.id,
            status=result.status,
            root_cause="Network connection refused: target host or port is unreachable.",
            failure_category="Network Error",
            confidence=0.89,
            explanation="The test client or browser failed to establish a TCP/IP connection with the target web address.",
            suggested_fix="Verify that the target server is online and accepting connections on the specified host and port.",
            evidence_used=evidence_signals,
            analysis_source="heuristic_engine",
            analyzed_at=datetime.now(UTC),
        )

    # 8. Generic / Application Error
    return FailureAnalysis(
        test_case_id=result.test_case_id,
        test_case_title=title,
        result_id=result.id,
        status=result.status,
        root_cause=failure_msg or "Test failed during verification execution.",
        failure_category="Application Error" if failure_msg else "Unknown",
        confidence=0.70 if failure_msg else 0.40,
        explanation=(
            f"The test failed with error: {failure_msg or 'No specific failure message provided'}. "
            f"Review the stack trace and execution logs for deeper inspection."
        ),
        suggested_fix="Inspect the error traceback, verify test environment configuration, and check recent application changes.",
        evidence_used=evidence_signals,
        analysis_source="heuristic_engine",
        analyzed_at=datetime.now(UTC),
    )


async def _query_llm_analysis(
    result: VerificationResult,
    test_case: TestCase | None,
    evidence_signals: list[str],
) -> FailureAnalysis | None:
    """
    Attempts to generate structured failure analysis via configured external LLM (Gemini or OpenAI).
    Returns None if no API key is configured or if the query encounters an error.
    """
    api_key = settings.gemini_api_key or settings.openai_api_key
    if not api_key:
        return None

    title = test_case.title if test_case else f"Test case {result.test_case_id}"
    prompt_payload = {
        "test_title": title,
        "test_description": test_case.description if test_case else None,
        "expected_result": test_case.expected_result if test_case else None,
        "actual_result": result.actual_result,
        "failure_message": result.failure_message,
        "stack_trace": result.stack_trace[:1500] if result.stack_trace else None,
        "steps": test_case.steps if test_case else None,
    }

    system_instruction = (
        "You are an expert QA and Software Verification Failure Detective. "
        "Analyze the provided test failure and output strict JSON with fields:\n"
        "- root_cause: concise 1-2 sentence root cause\n"
        "- failure_category: one of ['Assertion Failure', 'Element Not Found', 'Timeout', "
        "'Authentication Failure', 'API Failure', 'Database Failure', 'Configuration Error', "
        "'Network Error', 'Application Error', 'Test Environment Error', 'Unknown']\n"
        "- confidence: float between 0.0 and 1.0\n"
        "- explanation: clear explanation of why it failed\n"
        "- suggested_fix: actionable instructions to fix the issue\n"
        "Return ONLY the JSON object."
    )

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            if settings.gemini_api_key:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
                )
                body = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": f"{system_instruction}\n\nFailure Data:\n{json.dumps(prompt_payload)}"
                                }
                            ]
                        }
                    ],
                    "generationConfig": {"responseMimeType": "application/json"},
                }
                resp = await client.post(url, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    content_text = (
                        data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    parsed = json.loads(content_text)
                    return FailureAnalysis(
                        test_case_id=result.test_case_id,
                        test_case_title=title,
                        result_id=result.id,
                        status=result.status,
                        root_cause=parsed["root_cause"],
                        failure_category=parsed["failure_category"],
                        confidence=float(parsed.get("confidence", 0.90)),
                        explanation=parsed["explanation"],
                        suggested_fix=parsed["suggested_fix"],
                        evidence_used=evidence_signals,
                        analysis_source="llm",
                        analyzed_at=datetime.now(UTC),
                    )

            elif settings.openai_api_key:
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
                body = {
                    "model": settings.openai_model,
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": json.dumps(prompt_payload)},
                    ],
                    "response_format": {"type": "json_object"},
                }
                resp = await client.post(url, headers=headers, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = json.loads(data["choices"][0]["message"]["content"])
                    return FailureAnalysis(
                        test_case_id=result.test_case_id,
                        test_case_title=title,
                        result_id=result.id,
                        status=result.status,
                        root_cause=parsed["root_cause"],
                        failure_category=parsed["failure_category"],
                        confidence=float(parsed.get("confidence", 0.90)),
                        explanation=parsed["explanation"],
                        suggested_fix=parsed["suggested_fix"],
                        evidence_used=evidence_signals,
                        analysis_source="llm",
                        analyzed_at=datetime.now(UTC),
                    )
    except Exception as exc:
        logger.warning(
            "External LLM query for failure analysis failed, falling back to heuristic engine: %s",
            exc,
        )

    return None


async def analyze_failed_result(
    result: VerificationResult,
    test_case: TestCase | None = None,
) -> FailureAnalysis:
    evidence_signals = _extract_evidence_signals(result, test_case)

    # Attempt LLM diagnosis if configured
    llm_result = await _query_llm_analysis(result, test_case, evidence_signals)
    if llm_result is not None:
        return llm_result

    # Fallback to intelligent deterministic heuristic analysis
    return _heuristic_analyze_result(result, test_case, evidence_signals)


async def analyze_verification_run(
    verification_run: VerificationRun,
    target_result_id: Any | None = None,
) -> VerificationRunAnalysisResponse:
    failed_results = [
        res
        for res in verification_run.results
        if res.status in {"failed", "blocked"}
    ]

    if target_result_id:
        failed_results = [
            res for res in failed_results if str(res.id) == str(target_result_id)
        ]

    if not failed_results:
        return VerificationRunAnalysisResponse(
            verification_run_id=verification_run.id,
            verification_run_name=verification_run.name,
            status=verification_run.status,
            has_failures=False,
            summary="No failed test cases detected in this verification run. All cases passed or are pending.",
            analyses=[],
        )

    analyses: list[FailureAnalysis] = []
    for res in failed_results:
        analysis = await analyze_failed_result(res, res.test_case)
        analyses.append(analysis)

    return VerificationRunAnalysisResponse(
        verification_run_id=verification_run.id,
        verification_run_name=verification_run.name,
        status=verification_run.status,
        has_failures=True,
        summary=f"Diagnosed {len(analyses)} failure(s) in verification run '{verification_run.name}'.",
        analyses=analyses,
    )
