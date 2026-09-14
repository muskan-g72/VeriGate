import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FolderKanban,
  LoaderCircle,
  Play,
  RefreshCw,
  Users,
  XCircle,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminApi } from '../../api/client'

const formatTime = (value) => {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function AdminDashboardPage() {
  const [stats, setStats] = useState(null)
  const [runs, setRuns] = useState([])
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  async function loadData(isBackground = false) {
    if (isBackground) setRefreshing(true)
    else setLoading(true)
    setError('')
    try {
      const [statsData, runsData, logsData] = await Promise.all([
        adminApi.statistics(),
        adminApi.runs(),
        adminApi.auditLogs(),
      ])
      setStats(statsData)
      setRuns(runsData || [])
      setLogs(logsData || [])
    } catch (err) {
      setError(err.message || 'Failed to load admin telemetry.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  return (
    <main className="command-center" aria-label="Admin Control Center">
      {/* Header */}
      <section className="command-center-header">
        <div>
          <p className="eyebrow">
            <span className="live-dot" /> SYSTEM MONITORING &amp; GOVERNANCE
          </p>
          <h2>Admin Control Center</h2>
          <p className="command-subtitle">
            Global system health, tenant statistics, user access, and cross-project verification operations.
          </p>
        </div>

        <div className="command-controls">
          <div className="command-actions-inline">
            <button
              type="button"
              className="secondary-button icon-btn"
              onClick={() => loadData(true)}
              disabled={refreshing || loading}
              title="Refresh system metrics"
              aria-label="Refresh telemetry"
            >
              <RefreshCw className={refreshing ? 'spinner-fast' : ''} size={15} />
            </button>
            <Link to="/admin/users" className="primary-button">
              <Users size={15} />
              <span>Manage Users</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Error Banner */}
      {error && (
        <div className="form-alert" role="alert">
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button type="button" className="link-button" onClick={() => loadData(false)}>
            Retry
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && !stats && (
        <div className="projects-state" role="status">
          <LoaderCircle className="spinner" />
          <p>Aggregating global system telemetry...</p>
        </div>
      )}

      {/* Dashboard Stats */}
      {stats && (
        <>
          <section className="status-grid" style={{ marginBottom: '24px' }}>
            <article className="status-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <p className="eyebrow" style={{ margin: 0 }}>System Users</p>
                <Users size={16} style={{ color: '#c084fc' }} />
              </div>
              <h3>{stats.total_users}</h3>
              <p className="status-meta">Active accounts &amp; admins</p>
              <div style={{ marginTop: '12px' }}>
                <Link to="/admin/users" style={{ fontSize: '11px', color: '#c084fc', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  View user directory <ArrowRight size={12} />
                </Link>
              </div>
            </article>

            <article className="status-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <p className="eyebrow" style={{ margin: 0 }}>Active Projects</p>
                <FolderKanban size={16} style={{ color: '#60a5fa' }} />
              </div>
              <h3>{stats.total_projects}</h3>
              <p className="status-meta">{stats.total_test_cases} test cases registered</p>
              <div style={{ marginTop: '12px' }}>
                <Link to="/admin/projects" style={{ fontSize: '11px', color: '#60a5fa', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  Inspect all projects <ArrowRight size={12} />
                </Link>
              </div>
            </article>

            <article className="status-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <p className="eyebrow" style={{ margin: 0 }}>Verification Runs</p>
                <Play size={16} style={{ color: '#34d399' }} />
              </div>
              <h3>{stats.total_verification_runs}</h3>
              <p className="status-meta">Automated &amp; CI/CD runs</p>
              <div style={{ marginTop: '12px' }}>
                <Link to="/admin/verification-runs" style={{ fontSize: '11px', color: '#34d399', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  All runs history <ArrowRight size={12} />
                </Link>
              </div>
            </article>

            <article className="status-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <p className="eyebrow" style={{ margin: 0 }}>Success / Failure</p>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <CheckCircle2 size={15} style={{ color: '#4ade80' }} />
                  <XCircle size={15} style={{ color: '#f87171' }} />
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
                <h3 style={{ color: '#4ade80' }}>{stats.successful_verification_runs}</h3>
                <span style={{ color: 'var(--text-3)', fontSize: '14px' }}>/</span>
                <h3 style={{ color: '#f87171' }}>{stats.failed_verification_runs}</h3>
              </div>
              <p className="status-meta">{stats.failed_results} failed test assertions</p>
            </article>
          </section>

          {/* Activity & Runs Two-Column Layout */}
          <section className="access-grid" style={{ marginBottom: '24px' }}>
            {/* Recent Audit Activity */}
            <article className="report-panel">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ margin: 0 }}>System Audit Activity</h3>
                  <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-3)' }}>
                    Security, authentication, and governance event log
                  </p>
                </div>
                <Link to="/admin/audit-logs" className="secondary-button" style={{ fontSize: '12px', padding: '4px 10px' }}>
                  Full Log
                </Link>
              </div>

              {logs.length === 0 ? (
                <p style={{ color: 'var(--text-3)', fontSize: '13px' }}>No system events recorded yet.</p>
              ) : (
                <ul className="simple-list">
                  {logs.slice(0, 7).map((log) => (
                    <li key={log.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '10px',
                          fontFamily: 'var(--mono)',
                          letterSpacing: '0.05em',
                          textTransform: 'uppercase',
                          background: log.action.includes('login') ? 'rgba(96,165,250,0.15)' : log.action.includes('role') ? 'rgba(192,132,252,0.15)' : 'rgba(255,255,255,0.07)',
                          color: log.action.includes('failed') ? '#f87171' : log.action.includes('role') ? '#c084fc' : '#93c5fd',
                        }}>
                          {log.action}
                        </span>
                        <div>
                          <strong style={{ fontSize: '13px', fontWeight: 500, display: 'block' }}>
                            {log.description || `${log.action} on ${log.resource_type}`}
                          </strong>
                          <small style={{ color: 'var(--text-3)', fontSize: '11px' }}>
                            Actor: {log.user?.email || 'System'}
                          </small>
                        </div>
                      </div>
                      <span style={{ fontSize: '11px', color: 'var(--text-3)', whiteSpace: 'nowrap' }}>
                        {formatTime(log.created_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </article>

            {/* Cross-Project Runs */}
            <article className="report-panel">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ margin: 0 }}>Recent Global Runs</h3>
                  <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-3)' }}>
                    Verification executions across all projects
                  </p>
                </div>
                <Link to="/admin/verification-runs" className="secondary-button" style={{ fontSize: '12px', padding: '4px 10px' }}>
                  All Runs
                </Link>
              </div>

              {runs.length === 0 ? (
                <p style={{ color: 'var(--text-3)', fontSize: '13px' }}>No verification runs executed yet.</p>
              ) : (
                <ul className="simple-list">
                  {runs.slice(0, 7).map((run) => (
                    <li key={run.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <div>
                        <strong style={{ fontSize: '13px', fontWeight: 500, display: 'block' }}>
                          {run.project_name} · {run.suite_name}
                        </strong>
                        <small style={{ color: 'var(--text-3)', fontSize: '11px' }}>
                          Run ID: {run.id.slice(0, 8)}
                        </small>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 500,
                          textTransform: 'uppercase',
                          background: run.status === 'completed' ? 'rgba(34,197,94,0.15)' : run.status === 'failed' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
                          color: run.status === 'completed' ? '#4ade80' : run.status === 'failed' ? '#f87171' : '#fbbf24',
                        }}>
                          {run.status}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-3)' }}>
                          {formatTime(run.created_at)}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          </section>
        </>
      )}
    </main>
  )
}
