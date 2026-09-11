import {
  Check,
  GitBranch,
  GitPullRequest,
  Key,
  LoaderCircle,
  Save,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { dashboardApi, githubApi } from '../api/client'

export function ProjectSummaryPage() {
  const { projectId } = useParams()
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')

  // GitHub Config state
  const [githubConfig, setGithubConfig] = useState(null)
  const [githubRepo, setGithubRepo] = useState('')
  const [githubBranch, setGithubBranch] = useState('main')
  const [githubEnabled, setGithubEnabled] = useState(true)
  const [githubSecret, setGithubSecret] = useState('')
  const [savingGithub, setSavingGithub] = useState(false)
  const [githubSuccess, setGithubSuccess] = useState('')
  const [githubError, setGithubError] = useState('')

  useEffect(() => {
    let active = true

    dashboardApi
      .projectSummary(projectId)
      .then((data) => {
        if (active) setSummary(data)
      })
      .catch((err) => {
        if (active) setError(err.message)
      })

    githubApi
      .getProjectConfig(projectId)
      .then((cfg) => {
        if (active) {
          setGithubConfig(cfg)
          setGithubRepo(cfg.github_repo || '')
          setGithubBranch(cfg.github_default_branch || 'main')
          setGithubEnabled(cfg.github_verification_enabled ?? true)
        }
      })
      .catch(() => {
        // Silently tolerate if config load fails or not yet supported
      })

    return () => {
      active = false
    }
  }, [projectId])

  async function handleSaveGithubConfig(e) {
    e.preventDefault()
    setSavingGithub(true)
    setGithubSuccess('')
    setGithubError('')

    try {
      const payload = {
        github_repo: githubRepo.trim() || null,
        github_default_branch: githubBranch.trim() || 'main',
        github_verification_enabled: githubEnabled,
      }
      if (githubSecret.trim()) {
        payload.github_webhook_secret = githubSecret.trim()
      }

      const updated = await githubApi.updateProjectConfig(projectId, payload)
      setGithubConfig(updated)
      setGithubRepo(updated.github_repo || '')
      setGithubBranch(updated.github_default_branch || 'main')
      setGithubEnabled(updated.github_verification_enabled)
      setGithubSecret('')
      setGithubSuccess('GitHub configuration saved successfully.')
      setTimeout(() => setGithubSuccess(''), 4000)
    } catch (err) {
      setGithubError(err.message || 'Failed to save GitHub settings.')
    } finally {
      setSavingGithub(false)
    }
  }

  if (error) {
    return (
      <main className="library-page">
        <div className="projects-state projects-state--error">
          <p>{error}</p>
          <Link className="secondary-button" to="/app/projects">
            Back to Projects
          </Link>
        </div>
      </main>
    )
  }

  if (!summary) {
    return (
      <main className="library-page">
        <div className="projects-state">
          <LoaderCircle className="spinner" />
          <p>Loading project summary...</p>
        </div>
      </main>
    )
  }

  const result = summary.verification_results
  const webhookUrl =
    githubConfig?.webhook_url ||
    (window.location.port === '5173'
      ? `${window.location.protocol}//${window.location.hostname}:8000/api/v1/github/webhook`
      : `${window.location.origin}/api/v1/github/webhook`)

  return (
    <main className="library-page project-summary-page">
      <section className="library-heading">
        <div>
          <p className="eyebrow">Project dashboard</p>
          <h2>{summary.project.name}</h2>
          <p>{summary.project.description || 'No description provided.'}</p>
        </div>
        <div className="heading-actions">
          <Link className="secondary-button" to="/app/projects">
            Back to Projects
          </Link>
        </div>
      </section>

      <section className="runs-metrics">
        {[
          ['Test suites', summary.test_suites],
          ['Test cases', summary.test_cases],
          ['Verification runs', summary.verification_runs],
          ['Pass rate', `${result.pass_rate}%`],
        ].map(([label, value]) => (
          <article key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <section className="access-grid">
        <article className="report-panel">
          <h3>Verification results</h3>
          <ul className="simple-list">
            {Object.entries(result)
              .filter(([key]) => key !== 'pass_rate' && key !== 'total')
              .map(([key, value]) => (
                <li key={key}>
                  <strong>{key}</strong>
                  <span>{value}</span>
                </li>
              ))}
          </ul>
        </article>

        <article className="report-panel">
          <h3>Issues</h3>
          <ul className="simple-list">
            <li>
              <strong>Open</strong>
              <span>{summary.issues.open}</span>
            </li>
            <li>
              <strong>Resolved</strong>
              <span>{summary.issues.resolved}</span>
            </li>
          </ul>
          {summary.latest_run && (
            <p style={{ marginTop: '1rem', fontSize: '0.875rem', color: 'var(--muted)' }}>
              Latest run: {summary.latest_run.name} ({summary.latest_run.status})
            </p>
          )}
        </article>
      </section>

      {/* GitHub Integration Panel */}
      <section className="github-config-section">
        <article className="report-panel github-panel">
          <div className="panel-header-with-status">
            <div className="panel-title-group">
              <GitPullRequest size={20} />
              <h3>GitHub PR Verification Integration</h3>
            </div>
            {githubConfig?.is_connected ? (
              <span className="connection-badge connected">
                <Check size={13} /> Connected
              </span>
            ) : (
              <span className="connection-badge disconnected">Not Connected</span>
            )}
          </div>

          <p className="panel-description">
            Connect this project with your GitHub repository to automatically trigger verification
            runs when Pull Requests are opened or updated.
          </p>

          <form onSubmit={handleSaveGithubConfig} className="github-config-form">
            <div className="form-row-grid">
              <div className="form-field">
                <label htmlFor="github-repo-input">Repository (owner/repo):</label>
                <input
                  id="github-repo-input"
                  type="text"
                  placeholder="e.g. muskan-g72/VeriGate"
                  value={githubRepo}
                  onChange={(e) => setGithubRepo(e.target.value)}
                />
              </div>

              <div className="form-field">
                <label htmlFor="github-branch-input">Default Branch:</label>
                <div className="input-with-icon">
                  <GitBranch size={16} />
                  <input
                    id="github-branch-input"
                    type="text"
                    placeholder="main"
                    value={githubBranch}
                    onChange={(e) => setGithubBranch(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="form-row-grid">
              <div className="form-field">
                <label htmlFor="github-secret-input">Webhook Secret (HMAC-SHA256):</label>
                <div className="input-with-icon">
                  <Key size={16} />
                  <input
                    id="github-secret-input"
                    type="password"
                    placeholder={
                      githubConfig?.webhook_configured
                        ? '•••••••• (secret is set; leave blank to keep)'
                        : 'Enter secret token'
                    }
                    value={githubSecret}
                    onChange={(e) => setGithubSecret(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-field checkbox-field">
                <label className="checkbox-label" htmlFor="github-enabled-toggle">
                  <input
                    id="github-enabled-toggle"
                    type="checkbox"
                    checked={githubEnabled}
                    onChange={(e) => setGithubEnabled(e.target.checked)}
                  />
                  <span>Enable GitHub Pull Request Verification</span>
                </label>
              </div>
            </div>

            {githubSuccess && <div className="form-success" role="status">{githubSuccess}</div>}
            {githubError && <div className="form-alert" role="alert">{githubError}</div>}

            <div className="github-form-actions">
              <button
                type="submit"
                className="primary-button"
                disabled={savingGithub}
              >
                {savingGithub ? <LoaderCircle size={15} className="spin" /> : <Save size={15} />}
                <span>{savingGithub ? 'Saving...' : 'Save GitHub Settings'}</span>
              </button>

              {githubConfig?.github_repo && (
                <Link
                  to={`/app/github-prs?project_id=${projectId}`}
                  className="secondary-button"
                >
                  <GitPullRequest size={15} />
                  <span>View Project PR Verifications</span>
                </Link>
              )}
            </div>
          </form>

          {/* Webhook setup instructions */}
          <div className="webhook-instructions-card">
            <h4>Webhook Setup Instructions:</h4>
            <p>
              In your GitHub repository (<code>Settings &rarr; Webhooks &rarr; Add webhook</code>),
              configure:
            </p>
            <ul>
              <li>
                <strong>Payload URL:</strong> <code>{webhookUrl}</code>
              </li>
              <li>
                <strong>Content type:</strong> <code>application/json</code>
              </li>
              <li>
                <strong>Secret:</strong> Must match the secret entered above.
              </li>
              <li>
                <strong>Which events would you like to trigger this webhook?</strong> Select{' '}
                <em>"Let me select individual events"</em> and check{' '}
                <strong>Pull requests</strong>.
              </li>
            </ul>
            <div className="webhook-tip" style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--muted)' }}>
              <strong>Local Development Tip:</strong> Because GitHub requires an HTTPS reachable URL, run{' '}
              <code>ngrok http 8000</code> and set Payload URL to{' '}
              <code>https://&lt;subdomain&gt;.ngrok-free.app/api/v1/github/webhook</code>.
            </div>
          </div>
        </article>
      </section>
    </main>
  )
}
