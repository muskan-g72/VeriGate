import {
  ArrowRight,
  FolderKanban,
  GitPullRequest,
  LoaderCircle,
  Play,
  RefreshCw,
  ShieldCheck,
  TestTube2,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { dashboardApi, projectsApi } from '../api/client'
import { useAuth } from '../auth/useAuth'

const formatTime = (value) => {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function UserDashboardPage() {
  const { user } = useAuth()
  const [projects, setProjects] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  async function loadData(isBackground = false) {
    if (isBackground) setRefreshing(true)
    else setLoading(true)
    setError('')
    try {
      const [projectsList, summaryData] = await Promise.all([
        projectsApi.list(),
        dashboardApi.summary(),
      ])
      setProjects(projectsList || [])
      setSummary(summaryData)
    } catch (err) {
      setError(err.message || 'Failed to load user workspace telemetry.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  return (
    <main className="command-center" aria-label="User Verification Workspace">
      {/* Workspace Header */}
      <section className="command-center-header">
        <div>
          <p className="eyebrow">
            <span className="live-dot" /> VERIFICATION WORKSPACE
          </p>
          <h2>Welcome back, {user?.full_name || user?.email?.split('@')[0] || 'User'}</h2>
          <p className="command-subtitle">
            Manage your assigned software projects, execute automated verification runs, and triage issues.
          </p>
        </div>

        <div className="command-controls">
          <button
            type="button"
            className="secondary-button icon-btn"
            onClick={() => loadData(true)}
            disabled={refreshing || loading}
            title="Refresh dashboard"
            aria-label="Refresh workspace"
          >
            <RefreshCw className={refreshing ? 'spinner-fast' : ''} size={15} />
          </button>
          <Link to="/app/runs" className="primary-button">
            <Play size={15} />
            <span>Launch Run</span>
          </Link>
        </div>
      </section>

      {/* Error Notice */}
      {error && (
        <div className="form-alert" role="alert" style={{ marginBottom: '16px' }}>
          <span>{error}</span>
          <button type="button" className="link-button" onClick={() => loadData(false)}>
            Retry
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && !summary && (
        <div className="projects-state" role="status">
          <LoaderCircle className="spinner" />
          <p>Loading your verification workspace...</p>
        </div>
      )}

      {summary && (
        <>
          {/* Summary Metric Cards */}
          <section className="status-grid" style={{ marginBottom: '24px' }}>
            <article className="status-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <p className="eyebrow" style={{ margin: 0 }}>My Projects</p>
                <FolderKanban size={16} style={{ color: '#60a5fa' }} />
              </div>
              <h3>{projects.length}</h3>
              <p className="status-meta">Assigned &amp; accessible</p>
              <div style={{ marginTop: '12px' }}>
                <Link to="/app/projects" style={{ fontSize: '11px', color: '#60a5fa', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  Explore projects <ArrowRight size={12} />
                </Link>
              </div>
            </article>

            <article className="status-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <p className="eyebrow" style={{ margin: 0 }}>Verification Health</p>
                <ShieldCheck size={16} style={{ color: summary.health_score_status === 'healthy' ? '#4ade80' : '#c084fc' }} />
              </div>
              <h3>{summary.health_score !== null ? `${summary.health_score}%` : 'Unverified'}</h3>
              <p className="status-meta">{summary.health_score_status?.toUpperCase() || 'STANDBY'}</p>
              <div style={{ marginTop: '12px' }}>
                <Link to="/app/insights" style={{ fontSize: '11px', color: '#c084fc', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  View detailed insights <ArrowRight size={12} />
                </Link>
              </div>
            </article>

            <article className="status-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <p className="eyebrow" style={{ margin: 0 }}>Test Suites &amp; Cases</p>
                <TestTube2 size={16} style={{ color: '#34d399' }} />
              </div>
              <h3>{summary.test_cases?.total || 0}</h3>
              <p className="status-meta">{summary.test_cases?.automated || 0} automated tests</p>
              <div style={{ marginTop: '12px' }}>
                <Link to="/app/test-library" style={{ fontSize: '11px', color: '#34d399', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  Test asset library <ArrowRight size={12} />
                </Link>
              </div>
            </article>

            <article className="status-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <p className="eyebrow" style={{ margin: 0 }}>GitHub PR Checks</p>
                <GitPullRequest size={16} style={{ color: '#f472b6' }} />
              </div>
              <h3>{summary.runs?.filter ? summary.runs.length : 'Live'}</h3>
              <p className="status-meta">Continuous CI/CD verification</p>
              <div style={{ marginTop: '12px' }}>
                <Link to="/app/github-prs" style={{ fontSize: '11px', color: '#f472b6', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  PR verifications <ArrowRight size={12} />
                </Link>
              </div>
            </article>
          </section>

          {/* Accessible Projects List */}
          <section className="report-panel" style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div>
                <h3 style={{ margin: 0 }}>My Projects</h3>
                <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-3)' }}>
                  Projects configured for verification testing
                </p>
              </div>
              <Link to="/app/projects" className="secondary-button" style={{ fontSize: '12px', padding: '4px 10px' }}>
                View All
              </Link>
            </div>

            {projects.length === 0 ? (
              <p style={{ color: 'var(--text-3)', fontSize: '13px' }}>
                No projects assigned yet. Contact your administrator or create a new project.
              </p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                {projects.map((proj) => (
                  <Link
                    key={proj.id}
                    to={`/app/projects/${proj.id}`}
                    style={{
                      display: 'block',
                      padding: '16px',
                      borderRadius: '10px',
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid rgba(255,255,255,0.06)',
                      textDecoration: 'none',
                      transition: 'border-color 0.15s, background 0.15s',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <strong style={{ color: '#f3eef8', fontSize: '14px' }}>{proj.name}</strong>
                      <span style={{
                        padding: '2px 7px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: 500,
                        textTransform: 'uppercase',
                        background: 'rgba(96,165,250,0.12)',
                        color: '#93c5fd',
                      }}>
                        {proj.role || 'Member'}
                      </span>
                    </div>
                    <p style={{ color: 'var(--text-3)', fontSize: '12px', margin: '0 0 12px', lineHeight: '1.4' }}>
                      {proj.description || 'No description provided.'}
                    </p>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-3)' }}>
                      <span>Created {formatTime(proj.created_at)}</span>
                      <span style={{ color: '#c084fc', display: 'flex', alignItems: 'center', gap: '3px' }}>
                        Open <ArrowRight size={11} />
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>

          {/* Quick Actions Shortcuts */}
          <section className="access-grid">
            <article className="report-panel">
              <h3 style={{ marginBottom: '12px' }}>Quick Actions</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <Link
                  to="/app/runs"
                  className="secondary-button"
                  style={{ justifyContent: 'space-between', padding: '10px 14px', textDecoration: 'none' }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Play size={14} style={{ color: '#34d399' }} />
                    Execute Verification Run
                  </span>
                  <ArrowRight size={13} />
                </Link>

                <Link
                  to="/app/test-cases"
                  className="secondary-button"
                  style={{ justifyContent: 'space-between', padding: '10px 14px', textDecoration: 'none' }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <TestTube2 size={14} style={{ color: '#60a5fa' }} />
                    View &amp; Author Test Cases
                  </span>
                  <ArrowRight size={13} />
                </Link>

                <Link
                  to="/app/github-prs"
                  className="secondary-button"
                  style={{ justifyContent: 'space-between', padding: '10px 14px', textDecoration: 'none' }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <GitPullRequest size={14} style={{ color: '#f472b6' }} />
                    Check PR Verification Status
                  </span>
                  <ArrowRight size={13} />
                </Link>
              </div>
            </article>

            <article className="report-panel">
              <h3 style={{ marginBottom: '8px' }}>Account Information</h3>
              <p style={{ color: 'var(--text-3)', fontSize: '12px', marginBottom: '16px' }}>
                Current credentials and system identity
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '8px' }}>
                  <span style={{ color: 'var(--text-3)' }}>Full Name</span>
                  <span style={{ color: '#f3eef8', fontWeight: 500 }}>{user?.full_name || '—'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '8px' }}>
                  <span style={{ color: 'var(--text-3)' }}>Email Address</span>
                  <span style={{ color: '#f3eef8', fontWeight: 500 }}>{user?.email}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '8px' }}>
                  <span style={{ color: 'var(--text-3)' }}>System Role</span>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 500,
                    textTransform: 'uppercase',
                    background: 'rgba(255,255,255,0.08)',
                    color: 'var(--text-2)',
                  }}>
                    {user?.role || user?.system_role || 'USER'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-3)' }}>Member Since</span>
                  <span style={{ color: 'var(--text-2)' }}>{formatTime(user?.created_at)}</span>
                </div>
              </div>
            </article>
          </section>
        </>
      )}
    </main>
  )
}
