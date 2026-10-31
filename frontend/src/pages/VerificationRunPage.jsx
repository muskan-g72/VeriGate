import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { CheckCircle2, CircleMinus, ExternalLink, FileText, GitBranch, GitCommit, GitPullRequest, LoaderCircle, XCircle } from 'lucide-react'
import { projectsApi, reportsApi, testCasesApi, testSuitesApi, verificationRunsApi } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { formatRunDate } from '../verification'
import { VerificationStatusBadge } from '../components/VerificationRuns'
import { VerificationResultCard } from '../components/VerificationResultCard'
import { AiFailureDetective } from '../components/AiFailureDetective'

export function VerificationRunPage() {
  const { runId } = useParams()
  return <VerificationRun key={runId} runId={runId} />
}

function VerificationRun({ runId }) {
  const { logout } = useAuth()
  const { state } = useLocation()
  const [run, setRun] = useState(null)
  const [suite, setSuite] = useState(null)
  const [project, setProject] = useState(null)
  const [cases, setCases] = useState([])
  const [error, setError] = useState('')
  const [summaryError, setSummaryError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [savingId, setSavingId] = useState(null)
  const [generatingReport, setGeneratingReport] = useState(false)
  const [reportNotice, setReportNotice] = useState('')
  const [reportError, setReportError] = useState('')
  const busy = useRef(false)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  useEffect(() => {
    let active = true
    async function load() {
      try {
        const detail = await verificationRunsApi.read(runId)
        const [definition, testCases] = await Promise.all([testSuitesApi.read(detail.test_suite_id), testCasesApi.list(detail.test_suite_id)])
        const owner = await projectsApi.read(definition.project_id)
        if (active) { setRun(detail); setSuite(definition); setCases(testCases); setProject(owner) }
      } catch (error) {
        if (!active) return
        if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
        else setError(error.status === 422 ? 'Invalid verification run ID.' : error.message)
      }
    }
    load()
    return () => { active = false }
  }, [runId, attempt, logout])

  async function refreshSummary() {
    const updated = await verificationRunsApi.read(runId)
    if (mounted.current) { setRun(updated); setSummaryError('') }
  }
  async function saveResult(resultId, data) {
    if (busy.current) return
    busy.current = true; setSavingId(resultId)
    try {
      const saved = await verificationRunsApi.updateResult(resultId, data)
      if (!mounted.current) return
      setRun((current) => ({ ...current, results: current.results.map((result) => result.id === saved.id ? saved : result) }))
      try { await refreshSummary() }
      catch (error) {
        if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
        else if (mounted.current) setSummaryError(`Result saved, but run status could not be refreshed. ${error.message}`)
      }
    } catch (error) {
      if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
      throw error
    } finally { busy.current = false; if (mounted.current) setSavingId(null) }
  }
  async function retrySummary() {
    if (busy.current) return
    busy.current = true; setSavingId('summary')
    try { await refreshSummary() } catch (error) {
      if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
      else setSummaryError(error.message)
    } finally { busy.current = false; if (mounted.current) setSavingId(null) }
  }
  async function handleDownloadReport() {
    if (generatingReport) return
    setGeneratingReport(true)
    setReportError('')
    setReportNotice('Generating Proof of Verification PDF report...')
    try {
      const { blob, filename } = await reportsApi.downloadVerificationReport(runId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename || `verigate-proof-of-verification-${runId}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      if (mounted.current) {
        setReportNotice('Proof of Verification report downloaded.')
        setTimeout(() => { if (mounted.current) setReportNotice('') }, 4000)
      }
    } catch (err) {
      if (mounted.current) {
        if (err.code === 'unauthorized') logout('Your session expired. Sign in again.')
        else setReportError(err.message || 'Failed to generate verification report.')
        setReportNotice('')
      }
    } finally {
      if (mounted.current) setGeneratingReport(false)
    }
  }
  const back = suite ? `/app/test-library?projectId=${suite.project_id}&suiteId=${suite.id}` : '/app/test-library'
  return <main className="library-page verification-page">
    {error ? <div className="projects-state projects-state--error" role="alert"><p>{error}</p><button onClick={() => { setError(''); setAttempt((value) => value + 1) }}>Retry</button></div> : !run ? <div className="projects-state" role="status">Loading verification run...</div> : <>
      <section className="verification-summary"><div className="verification-back-links"><Link className="library-link-button" to={back}>Back to Test Library</Link><Link className="secondary-button" to={`/app/runs${typeof state?.runsSearch === 'string' && state.runsSearch ? `?${state.runsSearch}` : ''}`}>Back to Runs</Link><button type="button" className="secondary-button report-download-btn" disabled={generatingReport} onClick={handleDownloadReport} title="Generate and download official Proof of Verification PDF report">{generatingReport ? <LoaderCircle size={15} className="spin" /> : <FileText size={15} />}<span>{generatingReport ? 'Generating Report...' : 'Proof of Verification Report'}</span></button></div><p className="eyebrow">{project?.name} / {suite?.name}</p><div className="verification-title"><h2>{run.name}</h2><VerificationStatusBadge status={run.status} /></div>
        <div className="verification-dates"><span>Created: {formatRunDate(run.created_at)}</span>{run.started_at && <span>Started: {formatRunDate(run.started_at)}</span>}{run.completed_at && <span>Completed: {formatRunDate(run.completed_at)}</span>}</div>
        {run.quality_gate_evaluation && <QualityGateResult evaluation={run.quality_gate_evaluation} />}
        {run.trigger_source === 'github_pr' && (
          <div className="github-pr-banner">
            <div className="pr-banner-left">
              <GitPullRequest size={18} className="pr-banner-icon" />
              <div>
                <div className="pr-banner-title">
                  <strong>GitHub PR #{run.pr_number}: {run.pr_title}</strong>
                  {run.pr_url && (
                    <a href={run.pr_url} target="_blank" rel="noopener noreferrer" className="pr-github-link">
                      <span>View PR on GitHub</span>
                      <ExternalLink size={13} />
                    </a>
                  )}
                </div>
                <div className="pr-banner-meta">
                  <span><GitBranch size={13} /> <code>{run.pr_source_branch}</code> &rarr; <code>{run.pr_target_branch}</code></span>
                  {run.pr_commit_sha && <span><GitCommit size={13} /> <code>{run.pr_commit_sha.slice(0, 7)}</code></span>}
                  {run.pr_author && <span>by @{run.pr_author}</span>}
                  {run.pr_repository && <span>in <code>{run.pr_repository}</code></span>}
                </div>
              </div>
            </div>
          </div>
        )}
        <p aria-live="polite">{run.total_cases - run.pending_count} / {run.total_cases} completed</p><progress aria-label="Executed test cases" value={run.total_cases - run.pending_count} max={run.total_cases || 1} />
        <p>{run.passed_count} passed · {run.failed_count} failed · {run.blocked_count} blocked · {run.skipped_count} skipped · {run.pending_count} pending</p>
        {reportNotice && <div className="form-success" role="status" style={{ marginTop: '0.75rem' }}>{reportNotice}</div>}
        {reportError && <div className="form-alert" role="alert" style={{ marginTop: '0.75rem' }}>{reportError}</div>}
        {summaryError && <div className="form-alert" role="alert"><span>{summaryError}</span><button className="secondary-button" disabled={Boolean(savingId)} onClick={retrySummary}>Refresh status</button></div>}
      </section>
      <AiFailureDetective run={run} />
      <section className="verification-results" aria-label="Test execution results">{run.results.length === 0 && <p>This run has no results.</p>}{run.results.map((result) => <VerificationResultCard key={result.id} result={result} testCase={cases.find((item) => item.id === result.test_case_id)} saving={savingId === result.id} disabled={Boolean(savingId)} onSave={saveResult} />)}</section>
    </>}
  </main>
}

const gateRuleLabels = {
  min_pass_rate: 'Minimum pass rate',
  no_failed_critical_tests: 'No failed critical tests',
  no_open_critical_issues: 'No open critical issues',
  min_executed_tests: 'Minimum executed tests',
}

function QualityGateResult({ evaluation }) {
  const rules = evaluation.rule_results || []
  const failed = rules.filter((rule) => !rule.passed).length
  const outcome = evaluation.outcome || 'not_configured'
  const OutcomeIcon = outcome === 'passed' ? CheckCircle2 : outcome === 'failed' ? XCircle : CircleMinus
  const measure = (rule, value) => `${value ?? '—'}${rule.rule === 'min_pass_rate' && value !== null && value !== undefined ? '%' : ''}`
  return <section className="report-panel quality-gate-result" aria-label="Quality gate result">
    <div className="quality-gate-result__header"><div><p className="eyebrow">Release criteria</p><h3>Quality gate</h3><p>{rules.length ? `${failed} of ${rules.length} rule${rules.length === 1 ? '' : 's'} failed` : 'No quality gate rules were enabled for this run.'}</p></div><span className={`verification-badge verification-badge--${outcome}`}><OutcomeIcon aria-hidden="true" />{outcome.replaceAll('_', ' ')}</span></div>
    {rules.length > 0 && <div className="quality-gate-table-wrap"><table className="quality-gate-table"><thead><tr><th>Rule</th><th>Measured</th><th>Threshold</th><th>Result</th><th>Reason</th></tr></thead><tbody>{rules.map((rule) => { const Icon = rule.passed ? CheckCircle2 : XCircle; return <tr key={rule.rule}><td>{gateRuleLabels[rule.rule] || rule.rule.replaceAll('_', ' ')}</td><td className="quality-gate-number">{measure(rule, rule.measured_value)}</td><td className="quality-gate-number">{measure(rule, rule.threshold)}</td><td><span className={`quality-gate-row-result quality-gate-row-result--${rule.passed ? 'passed' : 'failed'}`}><Icon aria-hidden="true" />{rule.passed ? 'Passed' : 'Failed'}</span></td><td className="quality-gate-reason">{rule.reason || 'No reason provided.'}</td></tr> })}</tbody></table></div>}
  </section>
}

