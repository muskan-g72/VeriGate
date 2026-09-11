import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { CreateEvidenceDialog } from './CreateEvidenceDialog'
import { CreateIssueDialog } from './CreateIssueDialog'
import { evidenceApi, verificationRunsApi } from '../api/client'
import { canCreateIssue } from '../issues'
import { VerificationStatusBadge } from './VerificationRuns'
import { formatRunDate, verificationLabels } from '../verification'
import { Sparkles, RefreshCw, AlertCircle, Cpu } from 'lucide-react'

export function VerificationResultCard({ result, testCase, disabled, saving, onSave }) {
  const [creatingIssue, setCreatingIssue] = useState(false)
  const [creatingEvidence, setCreatingEvidence] = useState(false)
  const [createdIssue, setCreatedIssue] = useState(null)
  const [actualResult, setActualResult] = useState(result.actual_result || '')
  const [notes, setNotes] = useState(result.notes || '')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [evidence, setEvidence] = useState([])
  const [evidenceError, setEvidenceError] = useState('')
  const [evidenceLoading, setEvidenceLoading] = useState(true)
  const [previewImage, setPreviewImage] = useState(null)
  const [analyzingResult, setAnalyzingResult] = useState(false)
  const [resultAnalysis, setResultAnalysis] = useState(null)
  const [resultAnalysisError, setResultAnalysisError] = useState('')

  useEffect(() => {
    let active = true
    evidenceApi.list(result.id)
      .then((items) => { if (active) setEvidence(items) })
      .catch((requestError) => { if (active) setEvidenceError(requestError.message) })
      .finally(() => { if (active) setEvidenceLoading(false) })
    return () => { active = false }
  }, [result.id])

  async function save(status) {
    setError('')
    setNotice('')
    try {
      await onSave(result.id, { status, actual_result: actualResult || null, notes: notes || null })
      setNotice('Result saved.')
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  async function removeEvidence(item) {
    if (!window.confirm(`Remove evidence "${item.name}"?`)) return
    try {
      await evidenceApi.remove(item.id)
      setEvidence((current) => current.filter((entry) => entry.id !== item.id))
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  async function handleAnalyzeResult() {
    setAnalyzingResult(true)
    setResultAnalysisError('')
    try {
      const data = await verificationRunsApi.analyzeResult(result.id)
      setResultAnalysis(data)
    } catch (err) {
      setResultAnalysisError(err.message || 'Failed to analyze result.')
    } finally {
      setAnalyzingResult(false)
    }
  }

  return (
    <article id={`result-${result.id}`} className="verification-result" aria-labelledby={`title-${result.id}`} aria-busy={saving}>
      <header>
        <div>
          <span className={`priority priority--${testCase?.priority}`}>{testCase?.priority || 'Test case'}</span>
          <h3 id={`title-${result.id}`}>{testCase?.title || `Test case ${result.test_case_id}`}</h3>
        </div>
        <div className="result-header-tags">
          {result.duration != null && <span className="duration-tag">{result.duration}s</span>}
          <VerificationStatusBadge status={result.status} />
        </div>
      </header>

      {testCase ? (
        <>
          <p className="verification-copy">{testCase.description}</p>
          <div className="verification-definition">
            <div><h4>Execution steps</h4><p>{testCase.steps}</p></div>
            <div><h4>Expected result</h4><p>{testCase.expected_result}</p></div>
          </div>
        </>
      ) : (
        <p>Test definition is unavailable.</p>
      )}

      {(result.failure_message || result.stack_trace || result.status === 'failed') && (
        <div className="failure-details-block" role="region" aria-label="Failure details">
          {result.failure_message && <div className="failure-alert"><strong>Failure:</strong><span>{result.failure_message}</span></div>}
          {result.stack_trace && <details className="failure-stack-details"><summary>View stack trace</summary><pre className="stack-trace-code">{result.stack_trace}</pre></details>}
          {result.status === 'failed' && (
            <div className="result-detective-section">
              {!resultAnalysis && !analyzingResult && (
                <button
                  type="button"
                  className="secondary-button ai-detective-trigger-btn"
                  onClick={handleAnalyzeResult}
                >
                  <Sparkles size={14} className="ai-icon-inline" />
                  Diagnose Failure with AI
                </button>
              )}
              {analyzingResult && (
                <div className="ai-detective-loading-inline">
                  <span className="loading-spinner-sm" />
                  <span>AI Detective is diagnosing this failure...</span>
                </div>
              )}
              {resultAnalysisError && (
                <div className="ai-detective-inline-error">
                  <AlertCircle size={14} />
                  <span>{resultAnalysisError}</span>
                  <button type="button" className="link-button" onClick={handleAnalyzeResult}>Retry</button>
                </div>
              )}
              {resultAnalysis && (
                <div className="result-detective-box">
                  <div className="result-detective-header">
                    <div className="result-detective-title">
                      <Sparkles size={15} className="ai-sparkle-icon" />
                      <strong>AI Failure Diagnosis</strong>
                    </div>
                    <div className="ai-detective-meta-inline">
                      <span className="category-tag">{resultAnalysis.category}</span>
                      <span className={`confidence-pill confidence-${resultAnalysis.confidence.toLowerCase()}`}>
                        {resultAnalysis.confidence} Confidence
                      </span>
                      <span className="source-tag">
                        <Cpu size={12} /> {resultAnalysis.analysis_source === 'llm' ? 'AI Model' : 'Heuristic Engine'}
                      </span>
                      <button
                        type="button"
                        className="icon-refresh-btn"
                        title="Re-analyze"
                        onClick={handleAnalyzeResult}
                      >
                        <RefreshCw size={13} />
                      </button>
                    </div>
                  </div>
                  <div className="result-detective-body">
                    <div className="diagnosis-field">
                      <span className="diagnosis-label">Root Cause</span>
                      <p className="root-cause-text">{resultAnalysis.root_cause}</p>
                    </div>
                    <div className="diagnosis-field">
                      <span className="diagnosis-label">Why This Failed</span>
                      <p className="explanation-text">{resultAnalysis.explanation}</p>
                    </div>
                    <div className="diagnosis-field">
                      <span className="diagnosis-label">Suggested Fix</span>
                      <pre className="fix-text">{resultAnalysis.suggested_fix}</pre>
                    </div>
                    {resultAnalysis.evidence_used?.length > 0 && (
                      <div className="diagnosis-field">
                        <span className="diagnosis-label">Signals Analyzed</span>
                        <ul className="signals-inline-list">
                          {resultAnalysis.evidence_used.map((sig, idx) => (
                            <li key={idx}><code>{sig}</code></li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="verification-definition">
        <div className="field">
          <label htmlFor={`actual-${result.id}`}>Actual result <span>Optional</span></label>
          <textarea id={`actual-${result.id}`} rows={3} value={actualResult} disabled={saving} onChange={(event) => setActualResult(event.target.value)} />
        </div>
        <div className="field">
          <label htmlFor={`notes-${result.id}`}>Notes <span>Optional</span></label>
          <textarea id={`notes-${result.id}`} rows={3} value={notes} disabled={saving} onChange={(event) => setNotes(event.target.value)} />
        </div>
      </div>

      <p>Enter observations before choosing a result, or edit them later and save details.</p>
      <div className="verification-actions" aria-label="Set test result">
        {['passed', 'failed', 'blocked', 'skipped', 'pending'].map((status) => (
          <button type="button" className="secondary-button" aria-pressed={result.status === status} disabled={disabled} key={status} onClick={() => save(status)}>
            {status === 'pending' ? 'Reset to Pending' : verificationLabels[status]}
          </button>
        ))}
        <button className="primary-button" disabled={disabled} onClick={() => save(result.status)}>Save details</button>
      </div>

      <p role="status">{saving ? 'Saving result...' : notice}{result.executed_at && ` Executed: ${formatRunDate(result.executed_at)}`}</p>
      {canCreateIssue(result.status) && (
        <button className="secondary-button" disabled={disabled} onClick={() => setCreatingIssue(true)}>Create Issue</button>
      )}
      {createdIssue && (
        <p role="status">Issue created. <Link to={`/app/issues/${createdIssue.id}`} state={{ runId: result.verification_run_id, resultId: result.id }}>Open issue</Link> or <Link to={`/app/issues?projectId=${createdIssue.project_id}`}>view project issues</Link>.</p>
      )}
      {creatingIssue && (
        <CreateIssueDialog result={result} testCase={testCase} onClose={() => setCreatingIssue(false)} onCreated={(issue) => { setCreatedIssue(issue); setCreatingIssue(false) }} />
      )}

      <section className="result-evidence" aria-label="Evidence">
        <div className="result-evidence__heading">
          <h4>Evidence</h4>
          <button type="button" className="secondary-button" disabled={disabled} onClick={() => setCreatingEvidence(true)}>Attach evidence</button>
        </div>
        {evidenceLoading ? (
          <p>Loading evidence...</p>
        ) : evidenceError ? (
          <p className="evidence-error">Evidence could not be loaded: {evidenceError}</p>
        ) : evidence.length ? (
          <ul>
            {evidence.map((item) => (
              <li key={item.id}>
                <strong>{item.name}</strong>
                <span>{item.type}{item.description ? ` · ${item.description}` : ''}</span>
                {item.type === 'screenshot' && item.content ? (
                  <div className="screenshot-evidence-item">
                    <img src={`data:image/png;base64,${item.content}`} alt={item.name} className="screenshot-preview-img" onClick={() => setPreviewImage(item)} />
                    <button type="button" className="secondary-button view-screenshot-btn" onClick={() => setPreviewImage(item)}>View full screenshot</button>
                  </div>
                ) : (
                  item.content && <pre>{item.content}</pre>
                )}
                {!disabled && <button className="list-action" onClick={() => removeEvidence(item)}>Remove</button>}
              </li>
            ))}
          </ul>
        ) : (
          <p>No evidence has been attached to this result.</p>
        )}
      </section>

      {creatingEvidence && (
        <CreateEvidenceDialog resultId={result.id} onClose={() => setCreatingEvidence(false)} onCreated={(item) => { setEvidence((current) => [item, ...current]); setCreatingEvidence(false) }} />
      )}
      {error && <div className="form-alert" role="alert">{error}</div>}

      {previewImage && (
        <div className="dialog-backdrop" onClick={() => setPreviewImage(null)}>
          <div className="screenshot-modal" role="dialog" aria-modal="true" aria-label={previewImage.name} onClick={(e) => e.stopPropagation()}>
            <header>
              <h3>{previewImage.name}</h3>
              <button type="button" className="icon-action-btn" onClick={() => setPreviewImage(null)} aria-label="Close screenshot preview">✕</button>
            </header>
            <div className="screenshot-modal-body">
              <img src={`data:image/png;base64,${previewImage.content}`} alt={previewImage.name} />
            </div>
          </div>
        </div>
      )}
    </article>
  )
}
