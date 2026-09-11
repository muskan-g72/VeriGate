import { AlertTriangle, Check, CheckCircle2, Lightbulb, LoaderCircle, RefreshCw, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { verificationRunsApi } from '../api/client'

export function AiFailureDetective({ run, onAnalysisComplete }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [analysisData, setAnalysisData] = useState(null)
  const [selectedResultIndex, setSelectedResultIndex] = useState(0)

  const failedCount = run?.failed_count ?? 0
  const hasFailures = failedCount > 0 || (run?.results?.some((r) => r.status === 'failed' || r.status === 'blocked'))

  async function handleAnalyze() {
    if (!run?.id) return
    setLoading(true)
    setError('')
    try {
      const data = await verificationRunsApi.analyze(run.id)
      setAnalysisData(data)
      setSelectedResultIndex(0)
      if (onAnalysisComplete) onAnalysisComplete(data)
    } catch (err) {
      setError(err.message || 'Failed to analyze verification failure.')
    } finally {
      setLoading(false)
    }
  }

  if (!hasFailures) {
    return (
      <section className="ai-detective-card ai-detective-card--clean" aria-label="AI Failure Detective">
        <div className="ai-detective-clean-banner">
          <CheckCircle2 size={18} className="success-icon" />
          <div>
            <strong>AI Failure Detective</strong>
            <p>No failed test cases detected in this run. All executed tests passed successfully.</p>
          </div>
        </div>
      </section>
    )
  }

  const activeAnalysis = analysisData?.analyses?.[selectedResultIndex]

  return (
    <section className="ai-detective-card" aria-label="AI Failure Detective">
      <header className="ai-detective-header">
        <div className="ai-detective-title-area">
          <div className="ai-detective-eyebrow">
            <Sparkles size={14} />
            <span>AI FAILURE DETECTIVE</span>
          </div>
          <h3>Automated Root Cause Diagnosis</h3>
          <p className="ai-detective-subtitle">
            Analyzes test failure messages, stack traces, expected vs actual outputs, and execution steps to determine why the verification failed and how to fix it.
          </p>
        </div>

        <div className="ai-detective-header-actions">
          {!analysisData ? (
            <button
              type="button"
              className="primary-button ai-detective-run-btn"
              disabled={loading}
              onClick={handleAnalyze}
            >
              {loading ? (
                <>
                  <LoaderCircle size={14} className="spinner" />
                  <span>Analyzing Failure...</span>
                </>
              ) : (
                <>
                  <Sparkles size={14} />
                  <span>Analyze Failure</span>
                </>
              )}
            </button>
          ) : (
            <button
              type="button"
              className="secondary-button"
              disabled={loading}
              onClick={handleAnalyze}
              title="Re-run failure analysis"
            >
              <RefreshCw size={13} className={loading ? 'spinner' : ''} />
              <span>Re-analyze</span>
            </button>
          )}
        </div>
      </header>

      {error && (
        <div className="ai-detective-error-alert" role="alert">
          <AlertTriangle size={15} />
          <span>{error}</span>
          <button type="button" className="secondary-button" onClick={handleAnalyze}>
            Retry
          </button>
        </div>
      )}

      {loading && (
        <div className="ai-detective-loading-state" role="status">
          <LoaderCircle size={24} className="spinner" />
          <h4>Investigating verification failure...</h4>
          <p>Evaluating assertions, error patterns, DOM selectors, and execution signals.</p>
        </div>
      )}

      {!loading && !analysisData && !error && (
        <div className="ai-detective-ready-state">
          <p>
            {failedCount} failed verification case{failedCount > 1 ? 's' : ''} ready for AI diagnosis. Click <strong>Analyze Failure</strong> to uncover root causes and suggested resolutions.
          </p>
        </div>
      )}

      {!loading && analysisData && activeAnalysis && (
        <div className="ai-detective-body">
          {/* Multiple failed tests switcher */}
          {analysisData.analyses.length > 1 && (
            <div className="ai-detective-tabs" role="tablist" aria-label="Failed test cases">
              {analysisData.analyses.map((item, idx) => (
                <button
                  key={item.result_id}
                  type="button"
                  role="tab"
                  aria-selected={selectedResultIndex === idx}
                  className={`ai-detective-tab ${selectedResultIndex === idx ? 'is-active' : ''}`}
                  onClick={() => setSelectedResultIndex(idx)}
                >
                  <span className="tab-status-dot" />
                  <span>{item.test_case_title}</span>
                </button>
              ))}
            </div>
          )}

          {/* Test Meta Bar */}
          <div className="ai-detective-meta-bar">
            <div className="meta-item">
              <span className="meta-label">Test Case</span>
              <strong className="meta-value">{activeAnalysis.test_case_title}</strong>
            </div>
            <div className="meta-item">
              <span className="meta-label">Status</span>
              <span className="status-badge status-badge--failed">FAILED</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Failure Category</span>
              <span className="category-tag">{activeAnalysis.failure_category}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Confidence</span>
              <span className={`confidence-pill ${activeAnalysis.confidence >= 0.9 ? 'confidence-high' : 'confidence-medium'}`}>
                {Math.round(activeAnalysis.confidence * 100)}% Confidence
              </span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Analysis Engine</span>
              <span className="source-tag">
                {activeAnalysis.analysis_source === 'llm' ? '🤖 AI Model' : '⚡ Heuristic Engine'}
              </span>
            </div>
          </div>

          {/* Diagnosis Grid */}
          <div className="ai-detective-grid">
            {/* Root Cause Card */}
            <div className="diagnosis-block diagnosis-block--root-cause">
              <h4>ROOT CAUSE</h4>
              <p className="root-cause-text">{activeAnalysis.root_cause}</p>
            </div>

            {/* Why This Failed */}
            <div className="diagnosis-block">
              <h4>WHY THIS FAILED</h4>
              <p className="explanation-text">{activeAnalysis.explanation}</p>
            </div>

            {/* Suggested Fix */}
            <div className="diagnosis-block diagnosis-block--fix">
              <div className="fix-header">
                <Lightbulb size={14} className="fix-icon" />
                <h4>SUGGESTED FIX</h4>
              </div>
              <p className="fix-text">{activeAnalysis.suggested_fix}</p>
            </div>

            {/* Evidence & Signals Used */}
            <div className="diagnosis-block diagnosis-block--signals">
              <h4>EVIDENCE USED</h4>
              <ul className="signals-list">
                {activeAnalysis.evidence_used?.map((signal) => (
                  <li key={signal} className="signal-item">
                    <Check size={12} className="signal-check" />
                    <span>{signal}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
