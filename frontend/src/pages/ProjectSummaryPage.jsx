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
import { dashboardApi, githubApi, projectMembersApi, projectsApi, qualityGatesApi } from '../api/client'
import { useAuth } from '../auth/useAuth'

export function ProjectSummaryPage() {
  const { projectId } = useParams()
  const { user, isAdmin } = useAuth()
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
  const [qualityGate, setQualityGate] = useState(null)
  const [gateDraft, setGateDraft] = useState(null)
  const [gateError, setGateError] = useState('')
  const [savingGate, setSavingGate] = useState(false)
  const [canEditGate, setCanEditGate] = useState(false)

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

    qualityGatesApi.get(projectId).then((gate) => {
      if (active) { setQualityGate(gate); setGateDraft(gate || { enabled: true, min_pass_rate_enabled: false, min_pass_rate: 80, critical_tests_enabled: false, critical_priorities: ['critical'], critical_issues_enabled: false, min_executed_tests_enabled: false, min_executed_tests: 1, treat_blocked_as_failure: true }) }
    }).catch(() => { if (active) setGateError('Unable to load quality gate settings.') })
      .catch(() => {
        // Silently tolerate if config load fails or not yet supported
      })

    Promise.all([projectsApi.read(projectId), projectMembersApi.list(projectId)]).then(([project, members]) => {
      const role = members.find((member) => member.user_id === user?.id)?.role
      if (active) setCanEditGate(Boolean(isAdmin || project.owner_id === user?.id || ['manager', 'qa_lead'].includes(role)))
    }).catch(() => { if (active) setCanEditGate(false) })

    return () => {
      active = false
    }
  }, [projectId, user?.id, isAdmin])

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

  async function saveQualityGate(e) {
    e.preventDefault(); if (!gateDraft) return
    setSavingGate(true); setGateError('')
    try { const saved = await qualityGatesApi.update(projectId, { ...gateDraft, min_pass_rate: gateDraft.min_pass_rate_enabled ? Number(gateDraft.min_pass_rate) : null, min_executed_tests: Number(gateDraft.min_executed_tests || 1) }); setQualityGate(saved); setGateDraft(saved) }
    catch (err) { setGateError(err.status === 403 ? 'You have read-only access to this quality gate.' : err.message) }
    finally { setSavingGate(false) }
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

  const backendBaseUrl = (import.meta.env.VITE_API_URL || 'https://verigate-ppkr.onrender.com').replace(/\/$/, '')
  const webhookUrl =
    githubConfig?.webhook_url ||
    `${backendBaseUrl}/api/v1/github/webhook`

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
          ['Pass rate', `${summary.verification_results.pass_rate}%`],
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
            {Object.entries(summary.verification_results)
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

      <section className="github-config-section">
        <article className="report-panel github-panel">
          <h3>Quality gate</h3>
          <p className="panel-description">Set release criteria evaluated whenever a verification run completes.</p>
          {!gateDraft ? <p>Loading quality gate…</p> : <form onSubmit={saveQualityGate} className={`github-config-form quality-gate-settings${canEditGate ? '' : ' quality-gate-settings--readonly'}`}>
            {!canEditGate && <p className="quality-gate-readonly" role="status">Read-only: only owners, managers, and QA leads can change release criteria.</p>}
            <label className="checkbox-label quality-gate-toggle"><input disabled={!canEditGate} type="checkbox" checked={gateDraft.enabled} onChange={(e) => setGateDraft({ ...gateDraft, enabled: e.target.checked })} /> Enable quality gate</label>
            <fieldset disabled={!canEditGate}>
            <RuleSetting label="Minimum pass rate" helper="Require a minimum percentage of executed tests to pass." checked={gateDraft.min_pass_rate_enabled} onChange={(checked) => setGateDraft({ ...gateDraft, min_pass_rate_enabled: checked })}><div className="quality-gate-input"><input aria-label="Minimum pass rate" type="number" min="0" max="100" required value={gateDraft.min_pass_rate ?? ''} onChange={(e) => setGateDraft({ ...gateDraft, min_pass_rate: e.target.value })} /><span>%</span></div><small>Enter a whole or decimal percentage from 0 to 100.</small></RuleSetting>
            <RuleSetting label="No failed critical tests" helper="Fail the gate when a configured critical-priority test fails or is blocked." checked={gateDraft.critical_tests_enabled} onChange={(checked) => setGateDraft({ ...gateDraft, critical_tests_enabled: checked })} />
            <RuleSetting label="No open critical issues" helper="Fail the gate if a critical issue remains open or in progress." checked={gateDraft.critical_issues_enabled} onChange={(checked) => setGateDraft({ ...gateDraft, critical_issues_enabled: checked })} />
            <RuleSetting label="Minimum executed tests" helper="Require a minimum number of completed test executions." checked={gateDraft.min_executed_tests_enabled} onChange={(checked) => setGateDraft({ ...gateDraft, min_executed_tests_enabled: checked })}><div className="quality-gate-input"><input aria-label="Minimum executed tests" type="number" min="1" step="1" required value={gateDraft.min_executed_tests ?? 1} onChange={(e) => setGateDraft({ ...gateDraft, min_executed_tests: e.target.value })} /><span>tests</span></div><small>Use a whole number of at least 1.</small></RuleSetting>
            <RuleSetting label="Treat blocked as failure" helper="Count blocked critical tests as failures when checking the gate." checked={gateDraft.treat_blocked_as_failure} onChange={(checked) => setGateDraft({ ...gateDraft, treat_blocked_as_failure: checked })} />
            </fieldset>
            {gateError && <div className="form-alert" role="alert">{gateError}</div>}
            {canEditGate && <button className="primary-button" disabled={savingGate}>{savingGate ? 'Saving…' : qualityGate ? 'Save quality gate' : 'Create quality gate'}</button>}
          </form>}
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
              <strong>GitHub Webhook URL:</strong> GitHub requires an HTTPS reachable URL. Your backend webhook URL is{' '}
              <code>{backendBaseUrl}/api/v1/github/webhook</code>.
            </div>
          </div>
        </article>
      </section>
    </main>
  )
}

function RuleSetting({ label, helper, checked, onChange, children }) {
  return <div className={`quality-gate-rule${checked ? ' quality-gate-rule--enabled' : ''}`}>
    <label className="checkbox-label"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /><span>{label}</span></label>
    <p>{helper}</p>
    {checked && <div className="quality-gate-rule__threshold">{children}</div>}
  </div>
}
