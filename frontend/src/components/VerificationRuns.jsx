import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LoaderCircle, X } from 'lucide-react'
import { verificationRunsApi } from '../api/client'
import { useAuth } from '../auth/useAuth'

import { verificationLabels, formatRunDate } from '../verification'

export function VerificationStatusBadge({ status }) {
  return <span className={`verification-badge verification-badge--${status}`}>{verificationLabels[status] || status}</span>
}

export function StartVerificationDialog({ project, suite, activeCount, onClose }) {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const dialog = useRef(null)
  const [name, setName] = useState(() => `${suite.name} - ${new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`.slice(0, 160))
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { const previous = document.activeElement; dialog.current.showModal(); return () => previous?.focus() }, [])
  async function submit(event) {
    event.preventDefault()
    if (!name.trim()) { setError('Enter a run name.'); return }
    setPending(true); setError('')
    try {
      const run = await verificationRunsApi.create(suite.id, { name: name.trim() })
      navigate(`/app/verification-runs/${run.id}`)
    } catch (error) {
      if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
      else setError(error.message)
    } finally { setPending(false) }
  }
  return <dialog ref={dialog} className="project-dialog library-dialog verification-dialog" aria-labelledby="start-run-title" onCancel={(event) => { event.preventDefault(); if (!pending) onClose() }}>
    <header><div><p className="eyebrow">Execute test suite</p><h2 id="start-run-title">Start Verification</h2></div><button onClick={onClose} disabled={pending} aria-label="Close"><X /></button></header>
    <form onSubmit={submit}>
      <p>{project.name} / {suite.name}</p><p>{activeCount} active test {activeCount === 1 ? 'case' : 'cases'}. Only active cases will be included.</p>
      {activeCount === 0 && <p role="status">This suite needs an active test case before a run can be created.</p>}
      {error && <div className="form-alert" role="alert">{error}</div>}
      <div className="field"><label htmlFor="run-name">Run name</label><input autoFocus id="run-name" value={name} onChange={(event) => setName(event.target.value)} maxLength={160} required disabled={pending} /></div>
      <footer><button type="button" className="secondary-button" onClick={onClose} disabled={pending}>Cancel</button><button className="primary-button" disabled={pending}>{pending ? <><LoaderCircle className="spinner" />Creating...</> : 'Start Verification'}</button></footer>
    </form>
  </dialog>
}

export function VerificationHistory({ suiteId }) {
  const { logout } = useAuth()
  const [runs, setRuns] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    verificationRunsApi.list(suiteId).then((items) => { if (active) { setRuns(items); setStatus('ready') } }).catch((error) => {
      if (!active) return
      if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
      else { setError(error.message); setStatus('error') }
    })
    return () => { active = false }
  }, [suiteId, attempt, logout])
  return <section className="verification-history" aria-labelledby="history-title"><h3 id="history-title">Verification history</h3>
    {status === 'loading' && <p role="status">Loading verification history...</p>}
    {status === 'error' && <div className="form-alert" role="alert"><span>{error}</span><button className="secondary-button" onClick={() => { setStatus('loading'); setAttempt((value) => value + 1) }}>Retry</button></div>}
    {status === 'ready' && !runs.length && <p>No previous runs. Start verification to execute this suite.</p>}
    {status === 'ready' && runs.map((run) => <article className="verification-history-row" key={run.id}><div><h4>{run.name}</h4><p>{formatRunDate(run.created_at)} · {run.total_cases - run.pending_count} / {run.total_cases} completed</p></div><VerificationStatusBadge status={run.status} /><Link className="library-link-button" aria-label={`Open Run: ${run.name}`} to={`/app/verification-runs/${run.id}`}>Open Run</Link></article>)}
  </section>
}

