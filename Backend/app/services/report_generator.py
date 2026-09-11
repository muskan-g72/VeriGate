import asyncio
import datetime
import html
import re
import sys
import uuid
from typing import Any

from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun
from app.services.failure_analysis_service import analyze_failed_result


def sanitize_report_text(text: str | None) -> str | None:
    """Mask credentials, API keys, Bearer tokens, and secrets in report text."""
    if not text:
        return text

    # Redact Bearer tokens
    sanitized = re.sub(
        r"(?i)(bearer\s+)[A-Za-z0-9\-\._~+/]+=*",
        r"\1[REDACTED_TOKEN]",
        text,
    )
    # Redact JWT tokens (3 dot-separated base64 chunks)
    sanitized = re.sub(
        r"ey[A-Za-z0-9_-]{8,}\.ey[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+",
        "[REDACTED_JWT]",
        sanitized,
    )
    # Redact common credential/key assignments
    sanitized = re.sub(
        r'(?i)(["\']?(?:password|passwd|secret|api[_-]?key|access[_-]?token)["\']?\s*[:=]\s*["\']?)([^"\'\s,;]+)(["\']?)',
        r"\1[REDACTED]\3",
        sanitized,
    )
    return sanitized


async def build_verification_run_report_data(
    database_session: Session,
    run: VerificationRun,
    current_user: Any,
) -> dict[str, Any]:
    """Compile comprehensive Proof of Verification report data."""
    suite = run.test_suite
    project = suite.project if suite else None

    total_cases = len(run.results)
    passed_cases = run.passed_count
    failed_cases = run.failed_count
    blocked_cases = run.blocked_count
    skipped_cases = run.skipped_count
    pending_cases = run.pending_count
    completed_cases = (
        passed_cases + failed_cases + blocked_cases + skipped_cases
    )

    pass_rate = (
        round((passed_cases / completed_cases) * 100, 1)
        if completed_cases
        else 0.0
    )

    durations = [r.duration for r in run.results if r.duration is not None]
    if durations:
        total_duration = round(sum(durations), 2)
    elif run.started_at and run.completed_at:
        total_duration = round(
            (run.completed_at - run.started_at).total_seconds(), 2
        )
    else:
        total_duration = None

    is_passed = (
        failed_cases == 0
        and blocked_cases == 0
        and run.status == "completed"
        and total_cases > 0
    )
    overall_status = "PASSED" if is_passed else "FAILED"
    if run.status in {"pending", "in_progress"}:
        overall_status = run.status.upper()

    # Timeline events
    timeline: list[dict[str, Any]] = []
    if run.created_at:
        timeline.append(
            {
                "event": "Verification Run Initialized",
                "timestamp": run.created_at.isoformat(),
                "details": f"Run '{run.name}' was queued by {run.created_by.full_name if run.created_by else 'system'}.",
            }
        )
    if run.started_at:
        timeline.append(
            {
                "event": "Execution Started",
                "timestamp": run.started_at.isoformat(),
                "details": "Automated and manual test execution began.",
            }
        )

    test_case_reports: list[dict[str, Any]] = []

    for result in run.results:
        tc = result.test_case
        title = tc.title if tc else f"Test Case {result.test_case_id}"

        if result.executed_at:
            timeline.append(
                {
                    "event": f"Executed: {title}",
                    "timestamp": result.executed_at.isoformat(),
                    "details": f"Status: {result.status.upper()} (duration: {result.duration or 0}s)",
                }
            )

        # AI Failure Detective Diagnosis for failed cases
        ai_diagnosis = None
        if result.status == "failed":
            timeline.append(
                {
                    "event": f"Failure Encountered: {title}",
                    "timestamp": (
                        result.executed_at or run.created_at
                    ).isoformat(),
                    "details": sanitize_report_text(result.failure_message)
                    or "Verification assertion failed",
                }
            )
            try:
                diag = await analyze_failed_result(result, tc)
                cat_val = (
                    diag.failure_category.value
                    if hasattr(diag.failure_category, "value")
                    else str(diag.failure_category)
                )
                if isinstance(diag.confidence, (int, float)):
                    conf_str = "High" if diag.confidence >= 0.85 else ("Medium" if diag.confidence >= 0.70 else "Low")
                else:
                    conf_str = str(diag.confidence)

                ai_diagnosis = {
                    "category": cat_val,
                    "root_cause": sanitize_report_text(diag.root_cause),
                    "explanation": sanitize_report_text(diag.explanation),
                    "suggested_fix": sanitize_report_text(diag.suggested_fix),
                    "confidence": conf_str,
                    "analysis_source": diag.analysis_source,
                    "evidence_used": diag.evidence_used,
                }
                timeline.append(
                    {
                        "event": f"AI Failure Analysis Generated: {title}",
                        "timestamp": (
                            result.executed_at or run.created_at
                        ).isoformat(),
                        "details": f"Identified category: {ai_diagnosis['category']} with {ai_diagnosis['confidence']} confidence",
                    }
                )
            except Exception as e:
                ai_diagnosis = {
                    "category": "Unhandled Exception",
                    "root_cause": "Automatic diagnosis could not be completed.",
                    "explanation": str(e),
                    "suggested_fix": "Review failure message and stack trace directly.",
                    "confidence": "Low",
                    "analysis_source": "fallback",
                    "evidence_used": [],
                }

        evidence_reports: list[dict[str, Any]] = []
        for ev in result.evidence_items:
            if ev.created_at:
                timeline.append(
                    {
                        "event": f"Evidence Captured: {ev.name}",
                        "timestamp": ev.created_at.isoformat(),
                        "details": f"Attached {ev.type} to '{title}'",
                    }
                )
            evidence_reports.append(
                {
                    "id": str(ev.id),
                    "name": ev.name,
                    "type": ev.type,
                    "description": sanitize_report_text(ev.description),
                    "content": ev.content if ev.type == "screenshot" else sanitize_report_text(ev.content),
                    "created_at": ev.created_at.isoformat()
                    if ev.created_at
                    else None,
                }
            )

        test_case_reports.append(
            {
                "result_id": str(result.id),
                "test_case_id": str(result.test_case_id),
                "title": title,
                "description": tc.description if tc else None,
                "priority": tc.priority if tc else "medium",
                "execution_mode": getattr(tc, "execution_mode", "manual"),
                "steps": tc.steps if tc else None,
                "expected_result": sanitize_report_text(tc.expected_result)
                if tc
                else None,
                "actual_result": sanitize_report_text(result.actual_result),
                "notes": sanitize_report_text(result.notes),
                "status": result.status,
                "duration": result.duration,
                "executed_at": result.executed_at.isoformat()
                if result.executed_at
                else None,
                "failure_message": sanitize_report_text(result.failure_message),
                "stack_trace": sanitize_report_text(result.stack_trace),
                "ai_diagnosis": ai_diagnosis,
                "evidence": evidence_reports,
            }
        )

    if run.completed_at:
        timeline.append(
            {
                "event": "Run Completed",
                "timestamp": run.completed_at.isoformat(),
                "details": f"All verification steps finished with status {run.status.upper()}.",
            }
        )

    timeline.sort(key=lambda item: item.get("timestamp") or "")

    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return {
        "report_id": str(uuid.uuid4()),
        "generated_at": generated_at,
        "verification_run": {
            "id": str(run.id),
            "name": run.name,
            "status": run.status,
            "overall_status": overall_status,
            "started_at": run.started_at.isoformat()
            if run.started_at
            else None,
            "completed_at": run.completed_at.isoformat()
            if run.completed_at
            else None,
            "created_at": run.created_at.isoformat()
            if run.created_at
            else None,
            "created_by": run.created_by.full_name
            if run.created_by
            else "VeriGate User",
        },
        "project": {
            "id": str(project.id) if project else None,
            "name": project.name if project else "Project",
            "description": project.description if project else None,
        },
        "test_suite": {
            "id": str(suite.id) if suite else None,
            "name": suite.name if suite else "Test Suite",
        },
        "summary": {
            "total_tests": total_cases,
            "passed_tests": passed_cases,
            "failed_tests": failed_cases,
            "blocked_tests": blocked_cases,
            "skipped_tests": skipped_cases,
            "pending_tests": pending_cases,
            "pass_rate": pass_rate,
            "total_duration": total_duration,
        },
        "timeline": timeline,
        "test_cases": test_case_reports,
    }


def generate_verification_report_html(report_data: dict[str, Any]) -> str:
    """Generate professional, print-optimized HTML report."""
    run = report_data["verification_run"]
    proj = report_data["project"]
    suite = report_data["test_suite"]
    summary = report_data["summary"]
    cases = report_data["test_cases"]
    timeline = report_data["timeline"]

    status_class = (
        "status-passed"
        if run["overall_status"] == "PASSED"
        else "status-failed"
    )
    status_bg = "#2ecc71" if run["overall_status"] == "PASSED" else "#e74c3c"

    # Build test cases table rows
    table_rows = []
    for c in cases:
        c_status = c["status"].upper()
        c_status_class = f"badge-{c['status']}"
        dur_str = f"{c['duration']}s" if c["duration"] is not None else "—"
        table_rows.append(
            f"""
        <tr>
          <td><strong>{html.escape(c['title'])}</strong><br><small style="color:#666;">{html.escape(c.get('execution_mode', 'manual').upper())} · Priority: {html.escape(str(c['priority']).upper())}</small></td>
          <td><span class="status-badge {c_status_class}">{c_status}</span></td>
          <td>{dur_str}</td>
          <td>{html.escape(str(c.get('expected_result') or '—'))}</td>
          <td>{html.escape(str(c.get('actual_result') or '—'))}</td>
        </tr>
        """
        )
    test_cases_table_html = "\n".join(table_rows)

    # Build Failure & AI Detective Section
    failed_cases = [c for c in cases if c["status"] == "failed"]
    failure_sections = []
    if failed_cases:
        for fc in failed_cases:
            diag = fc.get("ai_diagnosis")
            ai_diag_html = ""
            if diag:
                evidence_used_html = ""
                if diag.get("evidence_used"):
                    evidence_pills = "".join(
                        f"<code>{html.escape(str(s))}</code>"
                        for s in diag["evidence_used"]
                    )
                    evidence_used_html = f"""
                    <div style="margin-top: 8px;">
                      <strong>Signals Analyzed:</strong>
                      <div class="evidence-pills">{evidence_pills}</div>
                    </div>
                    """

                ai_diag_html = f"""
                <div class="ai-box">
                  <div class="ai-box-header">
                    <span class="ai-badge">AI FAILURE DETECTIVE</span>
                    <span class="ai-category">{html.escape(str(diag['category']))}</span>
                    <span class="ai-confidence">{html.escape(str(diag['confidence']))} Confidence ({html.escape(str(diag['analysis_source']).upper())})</span>
                  </div>
                  <div class="ai-field">
                    <strong>Root Cause:</strong>
                    <p>{html.escape(str(diag['root_cause']))}</p>
                  </div>
                  <div class="ai-field">
                    <strong>Why This Failed:</strong>
                    <p>{html.escape(str(diag['explanation']))}</p>
                  </div>
                  <div class="ai-field">
                    <strong>Suggested Remediation:</strong>
                    <pre class="fix-code">{html.escape(str(diag['suggested_fix']))}</pre>
                  </div>
                  {evidence_used_html}
                </div>
                """
            else:
                ai_diag_html = """
                <div class="ai-box ai-box-empty">
                  <em>AI failure analysis was not generated for this test run.</em>
                </div>
                """

            stack_html = ""
            if fc.get("stack_trace"):
                stack_html = f"""
                <div class="stack-box">
                  <strong>Stack Trace:</strong>
                  <pre>{html.escape(fc['stack_trace'])}</pre>
                </div>
                """

            failure_sections.append(
                f"""
            <div class="failure-card">
              <h4>{html.escape(fc['title'])}</h4>
              <div class="failure-alert">
                <strong>Failure Message:</strong>
                <span>{html.escape(fc.get('failure_message') or 'Assertion failed')}</span>
              </div>
              {ai_diag_html}
              {stack_html}
            </div>
            """
            )
        failures_html = "\n".join(failure_sections)
    else:
        failures_html = """
        <div class="clean-box">
          <h3 style="color: #27ae60; margin: 0 0 6px;">Zero Test Failures</h3>
          <p style="margin: 0; color: #555;">All test cases in this verification run passed successfully. No defects were encountered.</p>
        </div>
        """

    # Build Evidence Gallery
    all_evidence = []
    for c in cases:
        for ev in c.get("evidence", []):
            all_evidence.append((c["title"], ev))

    evidence_cards = []
    for test_title, ev in all_evidence:
        content_html = ""
        if ev["type"] == "screenshot" and ev.get("content"):
            content_html = f"""
            <div class="screenshot-wrap">
              <img src="data:image/png;base64,{ev['content']}" alt="{html.escape(ev['name'])}" />
            </div>
            """
        elif ev.get("content"):
            content_html = f"""
            <pre class="log-wrap">{html.escape(str(ev['content']))}</pre>
            """

        evidence_cards.append(
            f"""
        <div class="evidence-card">
          <div class="evidence-header">
            <strong>{html.escape(ev['name'])}</strong>
            <span class="evidence-type">{html.escape(ev['type'].upper())}</span>
          </div>
          <small style="color:#666;">Associated with test: <em>{html.escape(test_title)}</em></small>
          {f'<p style="margin: 4px 0 8px; font-size: 11px;">{html.escape(ev["description"])}</p>' if ev.get("description") else ''}
          {content_html}
        </div>
        """
        )

    evidence_html = (
        "\n".join(evidence_cards)
        if evidence_cards
        else "<p style='color:#777;'>No evidence artifacts were attached to this run.</p>"
    )

    # Build Timeline Section
    timeline_items = []
    for t in timeline:
        timeline_items.append(
            f"""
        <div class="timeline-step">
          <div class="timeline-marker"></div>
          <div class="timeline-body">
            <span class="timeline-time">{html.escape(t.get('timestamp') or '')}</span>
            <strong>{html.escape(t.get('event') or '')}</strong>
            <p>{html.escape(t.get('details') or '')}</p>
          </div>
        </div>
        """
        )
    timeline_html = (
        "\n".join(timeline_items)
        if timeline_items
        else "<p style='color:#777;'>No execution timeline events recorded.</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>VeriGate Proof of Verification - {html.escape(run['name'])}</title>
  <style>
    @page {{
      size: A4;
      margin: 12mm;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: #1a1a1a;
      line-height: 1.5;
      margin: 0;
      padding: 0;
      background: #ffffff;
      font-size: 12px;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid #09bbc8;
      padding-bottom: 12px;
      margin-bottom: 18px;
    }}
    .brand-title {{
      font-size: 22px;
      font-weight: 800;
      color: #060908;
      letter-spacing: -0.02em;
    }}
    .brand-title span {{
      color: #09bbc8;
    }}
    .doc-type {{
      font-size: 11px;
      font-family: monospace;
      color: #555;
      text-transform: uppercase;
      letter-spacing: 0.1em;
    }}
    .status-banner {{
      background: {status_bg};
      color: #ffffff;
      padding: 10px 16px;
      border-radius: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }}
    .status-banner h2 {{
      margin: 0;
      font-size: 18px;
      letter-spacing: 0.05em;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      background: #f8f9fa;
      border: 1px solid #e9ecef;
      border-radius: 6px;
      padding: 12px 14px;
      margin-bottom: 20px;
    }}
    .meta-item {{
      display: grid;
      gap: 2px;
    }}
    .meta-item span {{
      font-size: 10px;
      font-weight: 600;
      color: #777;
      text-transform: uppercase;
    }}
    .meta-item strong {{
      font-size: 13px;
      color: #222;
    }}
    .summary-cards {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 10px;
      margin-bottom: 24px;
    }}
    .summary-card {{
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 10px 12px;
      text-align: center;
      background: #ffffff;
    }}
    .summary-card span {{
      font-size: 10px;
      text-transform: uppercase;
      color: #64748b;
      font-weight: 600;
      display: block;
    }}
    .summary-card strong {{
      font-size: 20px;
      color: #0f172a;
      display: block;
      margin-top: 4px;
    }}
    .card-passed strong {{ color: #2ecc71; }}
    .card-failed strong {{ color: #e74c3c; }}
    .card-rate strong {{ color: #09bbc8; }}

    h3.section-heading {{
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      border-bottom: 1px solid #cbd5e1;
      padding-bottom: 6px;
      margin: 24px 0 12px;
      color: #334155;
    }}

    table.report-table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 20px;
      font-size: 11px;
    }}
    table.report-table th {{
      background: #f1f5f9;
      color: #475569;
      text-align: left;
      padding: 8px 10px;
      border: 1px solid #cbd5e1;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 10px;
    }}
    table.report-table td {{
      padding: 8px 10px;
      border: 1px solid #e2e8f0;
      vertical-align: top;
    }}
    table.report-table tr:nth-child(even) td {{
      background: #f8fafc;
    }}
    .status-badge {{
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 9px;
      font-weight: bold;
      font-family: monospace;
    }}
    .badge-passed {{ background: #dcfce7; color: #166534; }}
    .badge-failed {{ background: #fee2e2; color: #991b1b; }}
    .badge-blocked {{ background: #fef3c7; color: #92400e; }}
    .badge-skipped {{ background: #f1f5f9; color: #475569; }}
    .badge-pending {{ background: #e0f2fe; color: #075985; }}

    .failure-card {{
      border: 1px solid #fca5a5;
      border-radius: 6px;
      background: #fff5f5;
      padding: 12px 14px;
      margin-bottom: 14px;
      page-break-inside: avoid;
    }}
    .failure-card h4 {{
      margin: 0 0 8px;
      font-size: 13px;
      color: #991b1b;
    }}
    .failure-alert {{
      background: #fee2e2;
      border: 1px solid #f87171;
      border-radius: 4px;
      padding: 8px 10px;
      font-size: 11px;
      color: #7f1d1d;
      margin-bottom: 10px;
    }}
    .ai-box {{
      border: 1px solid #7dd3fc;
      background: #f0f9ff;
      border-radius: 6px;
      padding: 10px 12px;
      margin-bottom: 10px;
    }}
    .ai-box-header {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }}
    .ai-badge {{
      font-size: 9px;
      font-weight: bold;
      font-family: monospace;
      background: #0284c7;
      color: #ffffff;
      padding: 2px 6px;
      border-radius: 4px;
    }}
    .ai-category {{
      font-size: 10px;
      font-weight: bold;
      color: #0369a1;
    }}
    .ai-confidence {{
      font-size: 9px;
      color: #64748b;
      margin-left: auto;
    }}
    .ai-field {{
      margin-bottom: 6px;
      font-size: 11px;
    }}
    .ai-field strong {{
      color: #0c4a6e;
      display: block;
      margin-bottom: 2px;
    }}
    .ai-field p {{
      margin: 0;
      color: #1e293b;
    }}
    .fix-code {{
      background: #0f172a;
      color: #a7f3d0;
      padding: 8px 10px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 10px;
      white-space: pre-wrap;
      margin: 4px 0 0;
    }}
    .evidence-pills code {{
      background: #e0f2fe;
      color: #0369a1;
      padding: 2px 5px;
      border-radius: 3px;
      font-size: 10px;
      margin-right: 4px;
    }}
    .stack-box {{
      background: #1e293b;
      color: #cbd5e1;
      padding: 8px 10px;
      border-radius: 4px;
      font-size: 10px;
      margin-top: 8px;
      overflow-x: auto;
    }}
    .stack-box pre {{
      margin: 4px 0 0;
      font-family: monospace;
      white-space: pre-wrap;
    }}
    .clean-box {{
      border: 1px solid #86efac;
      background: #f0fdf4;
      border-radius: 6px;
      padding: 16px;
      text-align: center;
      margin-bottom: 20px;
    }}

    .evidence-card {{
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 10px;
      margin-bottom: 12px;
      background: #ffffff;
      page-break-inside: avoid;
    }}
    .evidence-header {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 4px;
    }}
    .evidence-type {{
      font-family: monospace;
      font-size: 9px;
      background: #f1f5f9;
      padding: 2px 6px;
      border-radius: 3px;
    }}
    .screenshot-wrap {{
      margin-top: 8px;
      text-align: center;
      background: #0f172a;
      padding: 8px;
      border-radius: 4px;
    }}
    .screenshot-wrap img {{
      max-width: 100%;
      max-height: 280px;
      border-radius: 4px;
      border: 1px solid #334155;
    }}
    .log-wrap {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      padding: 8px;
      font-family: monospace;
      font-size: 10px;
      border-radius: 4px;
      white-space: pre-wrap;
      max-height: 180px;
      overflow-y: auto;
    }}

    .timeline {{
      display: grid;
      gap: 8px;
      margin-bottom: 20px;
      position: relative;
      padding-left: 14px;
      border-left: 2px solid #e2e8f0;
    }}
    .timeline-step {{
      position: relative;
      font-size: 11px;
    }}
    .timeline-marker {{
      position: absolute;
      left: -19px;
      top: 4px;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #09bbc8;
    }}
    .timeline-body {{
      display: grid;
      gap: 1px;
    }}
    .timeline-time {{
      font-family: monospace;
      font-size: 9px;
      color: #94a3b8;
    }}
    .timeline-body p {{
      margin: 0;
      color: #64748b;
    }}

    .footer {{
      margin-top: 30px;
      border-top: 1px solid #cbd5e1;
      padding-top: 12px;
      display: flex;
      justify-content: space-between;
      color: #94a3b8;
      font-size: 10px;
    }}
    .footer-confidential {{
      color: #64748b;
      font-weight: 500;
    }}
  </style>
</head>
<body>

  <div class="header">
    <div>
      <div class="brand-title">Veri<span>Gate</span></div>
      <div class="doc-type">Proof of Verification · Quality Audit Certificate</div>
    </div>
    <div style="text-align: right;">
      <small style="color:#777;">Report Reference</small><br>
      <code style="font-size: 10px; color: #334155;">{report_data['report_id'][:16]}</code><br>
      <small style="color:#777;">Generated: {report_data['generated_at'][:19].replace('T', ' ')} UTC</small>
    </div>
  </div>

  <div class="status-banner">
    <div>
      <small style="text-transform:uppercase; font-size:10px; opacity:0.9;">Verification Outcome</small>
      <h2>VERIFICATION STATUS: {run['overall_status']}</h2>
    </div>
    <div style="text-align:right;">
      <span style="font-size: 16px; font-weight: bold;">{summary['pass_rate']}% Pass Rate</span><br>
      <small style="opacity:0.9;">{summary['passed_tests']} of {summary['total_tests']} tests passing</small>
    </div>
  </div>

  <div class="meta-grid">
    <div class="meta-item">
      <span>Project</span>
      <strong>{html.escape(proj['name'])}</strong>
    </div>
    <div class="meta-item">
      <span>Test Suite</span>
      <strong>{html.escape(suite['name'])}</strong>
    </div>
    <div class="meta-item">
      <span>Verification Run</span>
      <strong>{html.escape(run['name'])}</strong>
    </div>
    <div class="meta-item">
      <span>Triggered By</span>
      <strong>{html.escape(run['created_by'])}</strong>
    </div>
  </div>

  <div class="summary-cards">
    <div class="summary-card">
      <span>Total Tests</span>
      <strong>{summary['total_tests']}</strong>
    </div>
    <div class="summary-card card-passed">
      <span>Passed</span>
      <strong>{summary['passed_tests']}</strong>
    </div>
    <div class="summary-card card-failed">
      <span>Failed</span>
      <strong>{summary['failed_tests']}</strong>
    </div>
    <div class="summary-card card-rate">
      <span>Pass Rate</span>
      <strong>{summary['pass_rate']}%</strong>
    </div>
    <div class="summary-card">
      <span>Duration</span>
      <strong>{summary['total_duration'] if summary['total_duration'] is not None else '—'}{'s' if summary['total_duration'] is not None else ''}</strong>
    </div>
  </div>

  <h3 class="section-heading">1. Verification Execution Record</h3>
  <table class="report-table">
    <thead>
      <tr>
        <th style="width: 35%;">Test Case</th>
        <th style="width: 12%;">Status</th>
        <th style="width: 10%;">Duration</th>
        <th style="width: 21%;">Expected Result</th>
        <th style="width: 22%;">Actual Result</th>
      </tr>
    </thead>
    <tbody>
      {test_cases_table_html}
    </tbody>
  </table>

  <h3 class="section-heading">2. Failure Analysis & Remediation</h3>
  {failures_html}

  <h3 class="section-heading">3. Evidence & Proof Artifacts</h3>
  {evidence_html}

  <h3 class="section-heading">4. Execution Timeline</h3>
  <div class="timeline">
    {timeline_html}
  </div>

  <div class="footer">
    <div class="footer-confidential">
      VeriGate Automated Quality Assurance System · Proof of Verification Certificate
    </div>
    <div>
      All sensitive credentials, tokens, and secrets have been automatically redacted.
    </div>
  </div>

</body>
</html>
"""


async def _render_pdf_playwright(html_content: str) -> bytes:
    """Render HTML content into a PDF using Playwright Chromium."""
    browser = None
    try:
        async with async_playwright() as playwright:
            try:
                browser = await playwright.chromium.launch(headless=True)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to launch Playwright Chromium: {exc}"
                ) from exc

            page = await browser.new_page()
            await page.set_content(html_content, wait_until="load")
            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                margin={
                    "top": "10mm",
                    "bottom": "10mm",
                    "left": "10mm",
                    "right": "10mm",
                },
            )
            await browser.close()
            browser = None
            return pdf_bytes
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass


def _run_pdf_in_proactor_thread(html_content: str) -> bytes:
    """Execute Playwright PDF rendering inside a dedicated ProactorEventLoop thread on Windows."""
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_render_pdf_playwright(html_content))
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()


async def generate_verification_report_pdf(
    report_data: dict[str, Any],
) -> bytes:
    """Render the report HTML into a high-resolution A4 PDF using Playwright Chromium."""
    html_content = generate_verification_report_html(report_data)

    if sys.platform == "win32":
        loop = asyncio.get_running_loop()
        if not isinstance(loop, getattr(asyncio, "ProactorEventLoop", ())):
            return await loop.run_in_executor(
                None, _run_pdf_in_proactor_thread, html_content
            )
        try:
            return await _render_pdf_playwright(html_content)
        except NotImplementedError:
            return await loop.run_in_executor(
                None, _run_pdf_in_proactor_thread, html_content
            )

    return await _render_pdf_playwright(html_content)
