import {
  AlertOctagon,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  Clock,
  ExternalLink,
  FolderKanban,
  Info,
  LoaderCircle,
  Play,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { dashboardApi, projectsApi } from '../api/client'
import { VerificationStatusBadge } from '../components/VerificationRuns'
import { formatRunDate } from '../verification'

function formatRelativeTime(dateStr) {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  const now = new Date()
  const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (diffSec < 5) return 'Just now'
  if (diffSec < 60) return `${diffSec}s ago`
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  return date.toLocaleDateString()
}

export function OverviewPage() {
  const [projects, setProjects] = useState([])
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [showFormula, setShowFormula] = useState(false)

  // Load project options
  useEffect(() => {
    projectsApi
      .list()
      .then((items) => setProjects(items || []))
      .catch(() => {})
  }, [])

  // Initial and project change fetch
  useEffect(() => {
    let active = true
    dashboardApi
      .summary(selectedProjectId || null)
      .then((data) => {
        if (active) setSummary(data)
      })
      .catch((err) => {
        if (active) setError(err.message || 'Failed to load dashboard telemetry.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [selectedProjectId])

  async function reload(isBackground = false) {
    if (isBackground) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError('')
    try {
      const data = await dashboardApi.summary(selectedProjectId || null)
      setSummary(data)
    } catch (err) {
      setError(err.message || 'Failed to load dashboard telemetry.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  // Periodic Auto-refresh (every 20s while tab is active and autoRefresh enabled)
  useEffect(() => {
    if (!autoRefresh) return
    const timer = setInterval(() => {
      setRefreshing(true)
      dashboardApi.summary(selectedProjectId || null)
        .then((data) => setSummary(data))
        .catch((err) => setError(err.message || 'Failed to refresh dashboard telemetry.'))
        .finally(() => setRefreshing(false))
    }, 20000)
    return () => clearInterval(timer)
  }, [autoRefresh, selectedProjectId])

  const healthScore = summary?.health_score
  const healthStatus = summary?.health_score_status || 'unverified'
  const breakdown = summary?.health_breakdown

  return (
    <main className="command-center" aria-label="Verification Command Center">
      {/* Header & Controls */}
      <section className="command-center-header">
        <div>
          <p className="eyebrow">
            <span className="live-dot" /> VERIFICATION COMMAND CENTER
          </p>
          <h2>Command Center</h2>
          <p className="command-subtitle">
            Real-time verification telemetry, quality health, and failure triage.
          </p>
        </div>

        <div className="command-controls">
          <div className="field-inline">
            <label htmlFor="project-scope-select">Project</label>
            <select
              id="project-scope-select"
              value={selectedProjectId}
              onChange={(e) => {
                setLoading(true)
                setSelectedProjectId(e.target.value)
              }}
            >
              <option value="">All Projects</option>
              {projects.map((proj) => (
                <option key={proj.id} value={proj.id}>
                  {proj.name}
                </option>
              ))}
            </select>
          </div>

          <div className="command-actions-inline">
            <label className="auto-refresh-toggle">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              <span>Live update</span>
              {autoRefresh && <span className="pulse-dot" title="Live update active (every 20s)" />}
            </label>

            <button
              type="button"
              className="secondary-button icon-btn"
              onClick={() => reload(true)}
              disabled={refreshing || loading}
              title="Refresh telemetry"
              aria-label="Refresh telemetry"
            >
              <RefreshCw className={refreshing ? 'spinner-fast' : ''} size={15} />
            </button>
          </div>
        </div>
      </section>

      {/* Error Banner */}
      {error && (
        <div className="form-alert" role="alert">
          <AlertOctagon size={16} />
          <span>Dashboard telemetry error: {error}</span>
          <button type="button" className="link-button" onClick={() => reload(false)}>
            Retry
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && !summary && (
        <div className="projects-state" role="status">
          <LoaderCircle className="spinner" />
          <p>Initializing Command Center telemetry...</p>
        </div>
      )}

      {/* Empty Projects State */}
      {!loading && projects.length === 0 && (
        <section className="empty-workspace">
          <div className="empty-visual" aria-hidden="true">
            <FolderKanban />
            <span />
            <span />
          </div>
          <div>
            <p className="eyebrow">Workspace setup</p>
            <h3>No projects in workspace</h3>
            <p>Create your first project to activate the Verification Command Center.</p>
            <Link className="workspace-action" to="/app/projects">
              Create Project <ArrowUpRight />
            </Link>
          </div>
        </section>
      )}

      {/* Loaded Dashboard Content */}
      {summary && (
        <>
          {/* Row 1: Verification Health & Test Counts Ticker */}
          <section className="command-hero-grid">
            {/* Health Score Gauge */}
            <article className={`health-gauge-card health-gauge--${healthStatus}`}>
              <header className="health-gauge-header">
                <div>
                  <span className="gauge-label">Verification Health</span>
                  <div className="gauge-score-wrap">
                    {healthScore !== null ? (
                      <span className="gauge-score-value">{healthScore}%</span>
                    ) : (
                      <span className="gauge-score-unverified">Unverified</span>
                    )}
                    <span className={`health-status-badge badge--${healthStatus}`}>
                      {healthStatus.toUpperCase()}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  className="formula-info-btn"
                  onClick={() => setShowFormula((prev) => !prev)}
                  title="View Health Score calculation formula"
                  aria-expanded={showFormula}
                  aria-label="Health score formula info"
                >
                  <Info size={16} />
                </button>
              </header>

              <p className="health-gauge-explanation">
                {summary.health_score_explanation}
              </p>

              {breakdown && healthScore !== null && (
                <div className="health-breakdown-bar">
                  <div className="breakdown-item">
                    <span>Pass Rate</span>
                    <strong>{breakdown.pass_rate_points}/60 pts</strong>
                  </div>
                  <div className="breakdown-item">
                    <span>Reliability</span>
                    <strong>{breakdown.reliability_points}/25 pts</strong>
                  </div>
                  <div className="breakdown-item">
                    <span>Defect Density</span>
                    <strong>{breakdown.defect_points}/15 pts</strong>
                  </div>
                </div>
              )}

              {showFormula && (
                <div className="formula-popover" role="region" aria-label="Score calculation details">
                  <p>
                    <strong>Deterministic Health Formula (0–100):</strong>
                  </p>
                  <ul>
                    <li>
                      <strong>Pass Rate (60 pts max):</strong> (Passed Results / Completed Results) × 60
                    </li>
                    <li>
                      <strong>Recent Reliability (25 pts max):</strong> Evaluates recent runs (-5 pts per failed run)
                    </li>
                    <li>
                      <strong>Defect Density (15 pts max):</strong> -3 pts per unresolved issue linked to verification
                    </li>
                  </ul>
                  <small>No machine learning heuristics or fabricated zeros are used.</small>
                </div>
              )}
            </article>

            {/* Test Outcomes Ticker */}
            <div className="metrics-ticker-grid" aria-label="Verification execution counts">
              <article className="ticker-card">
                <span className="ticker-label">Total Tests</span>
                <strong className="ticker-value">{summary.total_results}</strong>
                <small className="ticker-sub">{summary.total_runs} verification runs</small>
              </article>

              <article className="ticker-card ticker-card--passed">
                <span className="ticker-label">Passed</span>
                <strong className="ticker-value text-green">{summary.passed_results}</strong>
                <small className="ticker-sub">{summary.pass_rate}% pass rate</small>
              </article>

              <article className="ticker-card ticker-card--failed">
                <span className="ticker-label">Failed</span>
                <strong className="ticker-value text-red">{summary.failed_results}</strong>
                <small className="ticker-sub">{summary.failure_rate}% failure rate</small>
              </article>

              <article className="ticker-card ticker-card--running">
                <span className="ticker-label">Running / Pending</span>
                <strong className="ticker-value text-cyan">
                  {summary.pending_results + summary.running_runs}
                </strong>
                <small className="ticker-sub">{summary.running_runs} active runs</small>
              </article>
            </div>
          </section>

          {/* Row 2: Verification Trend & Quality Health Metrics */}
          <section className="command-telemetry-grid">
            {/* Trend Chart */}
            <article className="telemetry-panel trend-panel">
              <header className="panel-header">
                <div>
                  <span className="panel-eyebrow">ACTIVITY TELEMETRY</span>
                  <h3>Verification Trend</h3>
                </div>
                <span className="panel-meta">Daily execution volume & outcomes</span>
              </header>

              {summary.trend && summary.trend.length > 0 ? (
                <div className="trend-chart-wrapper">
                  <div className="trend-bar-chart">
                    {summary.trend.map((point) => {
                      const total = point.passed + point.failed + point.blocked || point.runs || 1
                      const passPct = Math.round((point.passed / total) * 100)
                      const failPct = Math.round((point.failed / total) * 100)
                      const blockPct = Math.max(0, 100 - passPct - failPct)

                      return (
                        <div
                          key={point.date}
                          className="trend-bar-col"
                          title={`${point.date}: ${point.runs} runs (${point.passed} passed, ${point.failed} failed, ${point.blocked} blocked)`}
                        >
                          <div className="trend-bar-stack">
                            {point.failed > 0 && (
                              <div
                                className="bar-segment bar-failed"
                                style={{ height: `${failPct}%` }}
                              />
                            )}
                            {point.blocked > 0 && (
                              <div
                                className="bar-segment bar-blocked"
                                style={{ height: `${blockPct}%` }}
                              />
                            )}
                            {point.passed > 0 && (
                              <div
                                className="bar-segment bar-passed"
                                style={{ height: `${passPct}%` }}
                              />
                            )}
                            {total === 0 && <div className="bar-segment bar-empty" style={{ height: '10%' }} />}
                          </div>
                          <span className="trend-date-label">
                            {point.date.slice(5)}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                  <div className="trend-legend">
                    <span>
                      <i className="legend-dot dot-passed" /> Passed
                    </span>
                    <span>
                      <i className="legend-dot dot-failed" /> Failed
                    </span>
                    <span>
                      <i className="legend-dot dot-blocked" /> Blocked
                    </span>
                  </div>
                </div>
              ) : (
                <div className="panel-empty-state">
                  <BarChart3 size={32} />
                  <p>No verification trend recorded yet.</p>
                  <small>Execute automated or manual verification runs to populate trend telemetry.</small>
                </div>
              )}
            </article>

            {/* Quality Health Metrics Panel */}
            <article className="telemetry-panel metrics-panel">
              <header className="panel-header">
                <div>
                  <span className="panel-eyebrow">QUALITY AUDIT</span>
                  <h3>Project Health</h3>
                </div>
              </header>

              <div className="health-metrics-list">
                <div className="metric-row">
                  <span className="metric-name">Pass Rate</span>
                  <strong className="metric-val">{summary.pass_rate}%</strong>
                </div>

                <div className="metric-row">
                  <span className="metric-name">Failure Rate</span>
                  <strong className="metric-val text-red">{summary.failure_rate}%</strong>
                </div>

                <div className="metric-row">
                  <span className="metric-name">Average Execution</span>
                  <strong className="metric-val">
                    {summary.average_duration !== null ? `${summary.average_duration}s` : '—'}
                  </strong>
                </div>

                <div className="metric-row">
                  <span className="metric-name">Open Issues</span>
                  <strong className="metric-val">
                    <Link to="/app/issues" className="issues-link">
                      {summary.open_issues} open
                    </Link>
                  </strong>
                </div>

                <div className="metric-row">
                  <span className="metric-name">Active Test Suites</span>
                  <strong className="metric-val">{summary.total_test_suites}</strong>
                </div>

                <div className="metric-row">
                  <span className="metric-name">Documented Test Cases</span>
                  <strong className="metric-val">{summary.total_test_cases}</strong>
                </div>
              </div>
            </article>
          </section>

          {/* Row 3: Recent Verification Runs */}
          <section className="command-section">
            <div className="section-header">
              <div>
                <span className="panel-eyebrow">EXECUTION LOG</span>
                <h3>Recent Verification Runs</h3>
              </div>
              <Link to="/app/runs" className="section-link">
                View all runs <ArrowUpRight size={14} />
              </Link>
            </div>

            {summary.recent_runs && summary.recent_runs.length > 0 ? (
              <div className="command-runs-table-wrap">
                <table className="command-runs-table">
                  <thead>
                    <tr>
                      <th>Run / Suite</th>
                      <th>Status</th>
                      <th>Duration</th>
                      <th>Executed</th>
                      <th>Outcomes</th>
                      <th className="text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.recent_runs.map((run) => (
                      <tr key={run.id} className={run.has_failures ? 'row-has-failure' : ''}>
                        <td>
                          <div className="run-title-cell">
                            <strong>{run.name}</strong>
                            <small>
                              {run.project_name} / {run.suite_name}
                            </small>
                          </div>
                        </td>
                        <td>
                          <VerificationStatusBadge status={run.status} />
                        </td>
                        <td>
                          <span className="duration-pill">
                            <Clock size={11} />
                            {run.duration !== null ? `${run.duration}s` : '—'}
                          </span>
                        </td>
                        <td>
                          <span title={formatRunDate(run.started_at || run.created_at)}>
                            {formatRelativeTime(run.started_at || run.created_at)}
                          </span>
                        </td>
                        <td>
                          <div className="outcomes-mini-bar">
                            <span className="count-tag count-pass">{run.passed}P</span>
                            {run.failed > 0 && (
                              <span className="count-tag count-fail">{run.failed}F</span>
                            )}
                            <span className="count-total">{run.total} total</span>
                          </div>
                        </td>
                        <td className="text-right">
                          <div className="run-actions-cell">
                            {run.has_failures && (
                              <Link
                                to={`/app/verification-runs/${run.id}?analyze=true`}
                                className="ai-detective-quick-btn"
                                title="Run AI Failure Detective"
                              >
                                <Sparkles size={12} />
                                <span>AI Analysis</span>
                              </Link>
                            )}
                            <Link
                              to={`/app/verification-runs/${run.id}`}
                              className="secondary-button btn-xs"
                            >
                              Open Run
                            </Link>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="panel-empty-state">
                <Play size={28} />
                <p>No verification runs yet.</p>
                <Link to="/app/test-library" className="secondary-button">
                  Start Verification in Test Library
                </Link>
              </div>
            )}
          </section>

          {/* Row 4: Failed Tests Spotlight */}
          <section className="command-section">
            <div className="section-header">
              <div className="spotlight-title-group">
                <span className="panel-eyebrow">DEFECT TRIAGE</span>
                <h3>
                  Failed Tests Spotlight
                  {summary.recent_failures?.length > 0 && (
                    <span className="failure-counter-badge">
                      {summary.recent_failures.length} active
                    </span>
                  )}
                </h3>
              </div>
            </div>

            {summary.recent_failures && summary.recent_failures.length > 0 ? (
              <div className="failed-spotlight-grid">
                {summary.recent_failures.map((fail) => (
                  <article key={fail.result_id} className="failed-spotlight-card">
                    <header className="spotlight-card-header">
                      <div>
                        <span className="context-tag">
                          {fail.project_name} · {fail.suite_name}
                        </span>
                        <h4>{fail.test_case_title}</h4>
                      </div>
                      {fail.duration !== null && (
                        <span className="duration-pill duration-fail">
                          {fail.duration}s
                        </span>
                      )}
                    </header>

                    <div className="failure-snippet-box">
                      <AlertTriangle size={14} className="fail-icon" />
                      <p className="failure-text">{fail.failure_message}</p>
                    </div>

                    <footer className="spotlight-card-footer">
                      <span className="time-subtext">
                        Failed {formatRelativeTime(fail.executed_at || fail.created_at)}
                      </span>

                      <div className="spotlight-actions">
                        <Link
                          to={`/app/verification-runs/${fail.run_id}#result-${fail.result_id}`}
                          className="secondary-button btn-xs"
                        >
                          View Failure <ExternalLink size={11} />
                        </Link>

                        <Link
                          to={`/app/verification-runs/${fail.run_id}?analyze=true#result-${fail.result_id}`}
                          className="ai-detective-quick-btn"
                        >
                          <Sparkles size={12} />
                          <span>AI Analysis</span>
                        </Link>
                      </div>
                    </footer>
                  </article>
                ))}
              </div>
            ) : (
              <div className="clean-failures-state">
                <CheckCircle2 size={28} className="clean-icon" />
                <div>
                  <strong>Zero test failures detected</strong>
                  <p>All recent verifications across this scope have completed successfully without errors.</p>
                </div>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  )
}
