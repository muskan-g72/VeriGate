import { AlertTriangle, ArrowRight, CheckCircle2, ExternalLink, FileCheck2, FlaskConical, Layers3, LoaderCircle, Monitor, Play, RefreshCw, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { projectsApi, testCasesApi, testSuitesApi, verificationRunsApi } from '../api/client'
import { chooseProject, rememberProject } from '../testLibrary/projectSelection'
import { formatRunDate } from '../verification'

export function PlaywrightTestsPage() {
  const [projects, setProjects] = useState([])
  const [projectId, setProjectId] = useState('')
  const [suites, setSuites] = useState([])
  const [suiteId, setSuiteId] = useState('')
  const [cases, setCases] = useState([])
  const [caseId, setCaseId] = useState('')
  const [pageStatus, setPageStatus] = useState('loading')
  const [pageError, setPageError] = useState('')

  // Execution state
  const [executing, setExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState(null)
  const [executionRunId, setExecutionRunId] = useState(null)
  const [executionError, setExecutionError] = useState('')
  const [previewScreenshot, setPreviewScreenshot] = useState(null)

  // 1. Load projects on mount
  useEffect(() => {
    let active = true
    projectsApi.list()
      .then((items) => {
        if (!active) return
        setProjects(items)
        const chosen = chooseProject(items)
        setProjectId(chosen)
        if (!items.length) setPageStatus('ready')
      })
      .catch((err) => {
        if (active) {
          setPageError(err.message)
          setPageStatus('error')
        }
      })
    return () => { active = false }
  }, [])

  // 2. Load suites when project changes
  useEffect(() => {
    if (!projectId) return
    let active = true
    testSuitesApi.list(projectId)
      .then((items) => {
        if (!active) return
        setSuites(items)
        const initialSuiteId = items[0]?.id || ''
        setSuiteId(initialSuiteId)
        if (!items.length) {
          setCases([])
          setCaseId('')
          setPageStatus('ready')
        }
      })
      .catch((err) => {
        if (active) {
          setPageError(err.message)
          setPageStatus('error')
        }
      })
    return () => { active = false }
  }, [projectId])

  // 3. Load cases when suite changes
  useEffect(() => {
    if (!suiteId) return
    let active = true
    testCasesApi.list(suiteId)
      .then((items) => {
        if (!active) return
        setCases(items)
        // Prefer selecting an automated case if available
        const firstAutomated = items.find((c) => c.execution_mode === 'automated')
        setCaseId(firstAutomated?.id || items[0]?.id || '')
        setPageStatus('ready')
      })
      .catch((err) => {
        if (active) {
          setPageError(err.message)
          setPageStatus('error')
        }
      })
    return () => { active = false }
  }, [suiteId])

  function changeProject(nextId) {
    rememberProject(nextId)
    setProjectId(nextId)
    setSuites([])
    setSuiteId('')
    setCases([])
    setCaseId('')
    setPageStatus(nextId ? 'loading' : 'ready')
    setExecutionResult(null)
    setExecutionRunId(null)
    setExecutionError('')
  }

  function changeSuite(nextSuiteId) {
    setSuiteId(nextSuiteId)
    setCases([])
    setCaseId('')
    setPageStatus(nextSuiteId ? 'loading' : 'ready')
    setExecutionResult(null)
    setExecutionRunId(null)
    setExecutionError('')
  }

  function changeCase(nextCaseId) {
    setCaseId(nextCaseId)
    setExecutionResult(null)
    setExecutionRunId(null)
    setExecutionError('')
  }

  const selectedProject = useMemo(() => projects.find((p) => p.id === projectId), [projects, projectId])
  const selectedSuite = useMemo(() => suites.find((s) => s.id === suiteId), [suites, suiteId])
  const selectedCase = useMemo(() => cases.find((c) => c.id === caseId), [cases, caseId])

  const isAutomated = selectedCase?.execution_mode === 'automated'
  const hasSteps = isAutomated && selectedCase?.automation_steps && selectedCase.automation_steps.length > 0
  const canRun = Boolean(selectedSuite && selectedCase && isAutomated && !executing)

  // Run Playwright test via backend verification run creation
  async function handleRunTest() {
    if (!canRun) return
    setExecuting(true)
    setExecutionError('')
    setExecutionResult(null)

    try {
      const runPayload = {
        name: `Playwright — ${selectedCase.title}`,
      }
      const createdRun = await verificationRunsApi.create(suiteId, runPayload)
      setExecutionRunId(createdRun.id)

      // Find the result corresponding to the selected test case
      const targetResult = createdRun.results?.find((r) => r.test_case_id === selectedCase.id)
      if (targetResult) {
        setExecutionResult(targetResult)
      } else {
        // Fallback to first result if present
        setExecutionResult(createdRun.results?.[0] || null)
      }
    } catch (err) {
      setExecutionError(err.message || 'Playwright execution failed.')
    } finally {
      setExecuting(false)
    }
  }

  return (
    <main className="library-page playwright-page">
      <section className="library-heading">
        <div>
          <p className="eyebrow">Automated Verification</p>
          <h2>Playwright Tests</h2>
          <p>
            Execute automated end-to-end browser tests via Playwright Chromium. Inspect live status, execution logs, failure traces, and captured screenshots.
          </p>
        </div>
        {projects.length > 0 && (
          <label>
            Project
            <select
              value={projectId}
              onChange={(e) => changeProject(e.target.value)}
              disabled={executing}
            >
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </section>

      {pageError && (
        <div className="library-alert" role="alert">
          <span>{pageError}</span>
          <button onClick={() => setPageError('')} aria-label="Dismiss error">
            <X size={14} />
          </button>
        </div>
      )}

      {pageStatus === 'loading' && (
        <div className="projects-state">
          <LoaderCircle className="spinner" />
          <p>Loading test configuration...</p>
        </div>
      )}

      {pageStatus === 'ready' && projects.length === 0 && (
        <section className="projects-empty">
          <div><FileCheck2 /></div>
          <p className="eyebrow">Project required</p>
          <h3>Create a project first</h3>
          <p>Playwright tests are organized into suites inside projects.</p>
          <Link className="library-link-button" to="/app/projects">
            Create project
          </Link>
        </section>
      )}

      {pageStatus === 'ready' && projects.length > 0 && suites.length === 0 && (
        <section className="projects-empty">
          <div><Layers3 /></div>
          <p className="eyebrow">Suite required</p>
          <h3>Create a test suite first</h3>
          <p>You need a test suite with test cases to execute Playwright tests.</p>
          <Link className="library-link-button" to="/app/test-suites">
            Create suite
          </Link>
        </section>
      )}

      {pageStatus === 'ready' && suites.length > 0 && (
        <div className="playwright-layout">
          {/* Left panel: Test Case Selection & Configuration */}
          <section className="playwright-config-card" aria-label="Test selection and controls">
            <header className="card-section-header">
              <div>
                <p className="eyebrow">{selectedProject?.name || 'Project'}</p>
                <h3>Test Selection</h3>
              </div>
              <div className="runtime-badge">
                <Monitor size={12} />
                <span>Chromium (Headless)</span>
              </div>
            </header>

            <div className="config-form">
              <div className="field">
                <label htmlFor="playwright-suite-select">Test Suite</label>
                <select
                  id="playwright-suite-select"
                  value={suiteId}
                  disabled={executing}
                  onChange={(e) => changeSuite(e.target.value)}
                >
                  {suites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label htmlFor="playwright-case-select">Test Case</label>
                {cases.length === 0 ? (
                  <p className="field-hint">No test cases in this suite.</p>
                ) : (
                  <select
                    id="playwright-case-select"
                    value={caseId}
                    disabled={executing}
                    onChange={(e) => changeCase(e.target.value)}
                  >
                    {cases.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.execution_mode === 'automated' ? '⚡ ' : '👤 '}
                        {c.title} ({c.execution_mode || 'manual'})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {selectedCase && (
                <div className="selected-case-summary">
                  <div className="case-meta-tags">
                    <span className={`priority priority--${selectedCase.priority}`}>
                      {selectedCase.priority}
                    </span>
                    <span className={`execution-tag execution-tag--${selectedCase.execution_mode || 'manual'}`}>
                      {selectedCase.execution_mode === 'automated' ? 'Automated' : 'Manual'}
                    </span>
                    <span className="case-activity">
                      {selectedCase.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>

                  <h4>{selectedCase.title}</h4>
                  {selectedCase.description && <p>{selectedCase.description}</p>}

                  {isAutomated ? (
                    <div className="case-steps-preview">
                      <strong>Configured Playwright Steps ({selectedCase.automation_steps?.length || 0})</strong>
                      {hasSteps ? (
                        <ol className="step-overview-list">
                          {selectedCase.automation_steps.map((step, idx) => (
                            <li key={idx}>
                              <code>{step.action}</code>
                              {step.selector && <span> selector: <code>{step.selector}</code></span>}
                              {step.value && <span> target: <code>{step.value}</code></span>}
                            </li>
                          ))}
                        </ol>
                      ) : (
                        <p className="warning-text">
                          <AlertTriangle size={13} /> This automated case has no automation steps defined.
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="manual-notice-card">
                      <AlertTriangle size={15} />
                      <div>
                        <strong>Manual Test Case</strong>
                        <p>
                          This test case is configured for manual execution. To execute it with Playwright, edit the test case in Test Cases and set its Execution Mode to Automated with browser steps.
                        </p>
                        <Link to="/app/test-cases" className="link-button-inline">
                          Edit in Test Cases <ArrowRight size={12} />
                        </Link>
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="action-row">
                <button
                  type="button"
                  className="primary-button run-playwright-btn"
                  onClick={handleRunTest}
                  disabled={!canRun}
                  aria-busy={executing}
                >
                  {executing ? (
                    <>
                      <LoaderCircle className="spinner" size={16} />
                      Running Playwright...
                    </>
                  ) : (
                    <>
                      <Play size={16} />
                      Run Playwright test
                    </>
                  )}
                </button>
              </div>
            </div>
          </section>

          {/* Right panel: Live Execution State, Logs, and Evidence */}
          <section className="playwright-output-card" aria-live="polite" aria-label="Execution results">
            <header className="card-section-header">
              <h3>Execution Output</h3>
              {executionRunId && (
                <Link
                  to={`/app/verification-runs/${executionRunId}`}
                  className="secondary-button external-run-link"
                  title="Open full verification run"
                >
                  View Run Details <ExternalLink size={12} />
                </Link>
              )}
            </header>

            {executing && (
              <div className="execution-running-state">
                <LoaderCircle className="spinner running-spinner" size={36} />
                <h4>Executing Playwright in Chromium...</h4>
                <p>Launching browser, executing automated steps, and capturing screenshot evidence on failure.</p>
              </div>
            )}

            {!executing && executionError && (
              <div className="execution-error-state" role="alert">
                <AlertTriangle size={24} />
                <h4>Execution Error</h4>
                <p>{executionError}</p>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={handleRunTest}
                  disabled={!canRun}
                >
                  <RefreshCw size={13} /> Retry execution
                </button>
              </div>
            )}

            {!executing && !executionError && !executionResult && (
              <div className="execution-idle-state">
                <FlaskConical size={32} />
                <h4>Ready to execute</h4>
                <p>
                  Select an automated test case from the left panel and click <strong>Run Playwright test</strong> to start browser execution.
                </p>
              </div>
            )}

            {!executing && executionResult && (
              <div className="execution-result-view">
                {/* Result Status Banner */}
                <div className={`result-banner result-banner--${executionResult.status}`}>
                  <div className="result-banner-icon">
                    {executionResult.status === 'passed' ? (
                      <CheckCircle2 size={24} />
                    ) : (
                      <AlertTriangle size={24} />
                    )}
                  </div>
                  <div className="result-banner-info">
                    <h4>Test {executionResult.status.toUpperCase()}</h4>
                    <p>{executionResult.actual_result || (executionResult.status === 'passed' ? 'All steps verified successfully' : 'Test execution encountered a failure')}</p>
                  </div>
                  <div className="result-banner-metrics">
                    {executionResult.duration != null && (
                      <span className="metric-pill">
                        <strong>Duration:</strong> {executionResult.duration}s
                      </span>
                    )}
                    {executionResult.executed_at && (
                      <span className="metric-pill">
                        <strong>Time:</strong> {formatRunDate(executionResult.executed_at)}
                      </span>
                    )}
                  </div>
                </div>

                {/* Failure Details */}
                {executionResult.status === 'failed' && executionResult.failure_message && (
                  <div className="execution-failure-box" role="alert">
                    <div className="failure-box-header">
                      <strong>Failure Reason:</strong>
                    </div>
                    <p className="failure-message-text">{executionResult.failure_message}</p>
                    {executionResult.stack_trace && (
                      <details className="stack-trace-details">
                        <summary>View Execution Stack Trace</summary>
                        <pre className="stack-trace-block">{executionResult.stack_trace}</pre>
                      </details>
                    )}
                  </div>
                )}

                {/* Execution Log Terminal */}
                <div className="execution-console-panel">
                  <div className="console-header">
                    <span>Console Log</span>
                    <span className="console-meta">{selectedCase?.title} · Chromium</span>
                  </div>
                  <pre className="console-body">
                    {`[playwright] Launching Chromium (headless=True)...
[playwright] Navigating context and executing ${selectedCase?.automation_steps?.length || 0} steps...
${selectedCase?.automation_steps?.map((step, i) => `[step ${i + 1}] ${step.action}: ${step.selector || ''} ${step.value || ''}`).join('\n') || ''}
[playwright] Status: ${executionResult.status} (${executionResult.duration != null ? `${executionResult.duration}s` : 'completed'})
[playwright] Result: ${executionResult.actual_result || executionResult.status}
${executionResult.failure_message ? `[error] ${executionResult.failure_message}` : '[playwright] Execution finished without error.'}`}
                  </pre>
                </div>

                {/* Evidence & Screenshots */}
                <div className="evidence-section">
                  <h4>Captured Evidence</h4>
                  {executionResult.evidence_items && executionResult.evidence_items.length > 0 ? (
                    <div className="evidence-grid">
                      {executionResult.evidence_items.map((item) => (
                        <div className="evidence-card" key={item.id}>
                          {item.type === 'screenshot' && item.content ? (
                            <div className="screenshot-card-content">
                              <img
                                src={`data:image/png;base64,${item.content}`}
                                alt={item.name}
                                className="screenshot-thumb"
                                onClick={() => setPreviewScreenshot(item)}
                              />
                              <div className="screenshot-card-footer">
                                <span>{item.name}</span>
                                <button
                                  type="button"
                                  className="secondary-button"
                                  onClick={() => setPreviewScreenshot(item)}
                                >
                                  Enlarge
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="text-evidence-content">
                              <strong>{item.name}</strong>
                              <span>{item.type}</span>
                              {item.content && <pre>{item.content}</pre>}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="no-evidence-text">
                      No screenshots or artifacts were generated during this run. (Screenshots are automatically captured when an automated step fails).
                    </p>
                  )}
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      {/* Screenshot Enlarge Modal */}
      {previewScreenshot && (
        <div
          className="dialog-backdrop"
          onClick={() => setPreviewScreenshot(null)}
          role="presentation"
        >
          <div
            className="screenshot-modal"
            role="dialog"
            aria-modal="true"
            aria-label={previewScreenshot.name}
            onClick={(e) => e.stopPropagation()}
          >
            <header>
              <h3>{previewScreenshot.name}</h3>
              <button
                type="button"
                className="icon-action-btn"
                onClick={() => setPreviewScreenshot(null)}
                aria-label="Close screenshot preview"
              >
                <X size={16} />
              </button>
            </header>
            <div className="screenshot-modal-body">
              <img
                src={`data:image/png;base64,${previewScreenshot.content}`}
                alt={previewScreenshot.name}
              />
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
