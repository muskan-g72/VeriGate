import { useRef, useState } from 'react'
import { issueSeverities, issueStatuses } from '../issues'

export function IssueStatusBadge({ status }) {
  return <span className={`verification-badge issue-status--${status}`}>{issueStatuses[status]}</span>
}

export function IssueForm({ initial, editing = false, onSave, onCancel, onPendingChange }) {
  const [form, setForm] = useState(initial)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const busy = useRef(false)
  function change(field, value) { setForm((current) => ({ ...current, [field]: value })); setNotice('') }
  async function submit(event) {
    event.preventDefault()
    if (busy.current) return
    if (!form.title.trim()) { setError('Enter an issue title.'); return }
    busy.current = true; setPending(true); onPendingChange?.(true); setError(''); setNotice('')
    try {
      const saved = await onSave({ title: form.title.trim(), description: form.description.trim() || null, severity: form.severity, ...(editing ? { status: form.status } : {}) })
      if (editing) { setForm({ title: saved.title, description: saved.description || '', severity: saved.severity, status: saved.status }); setNotice('Issue updated.') }
    } catch (error) { setError(error.message) }
    finally { busy.current = false; setPending(false); onPendingChange?.(false) }
  }
  return <form className="issue-form" onSubmit={submit} aria-busy={pending}>
    {error && <div className="form-alert" role="alert">{error}</div>}
    <div className="field"><label htmlFor="issue-title">Title</label><input autoFocus id="issue-title" value={form.title} onChange={(event) => change('title', event.target.value)} maxLength={180} required disabled={pending} /></div>
    <div className="field"><label htmlFor="issue-description">Description <span>Optional</span></label><textarea id="issue-description" rows={7} value={form.description} onChange={(event) => change('description', event.target.value)} disabled={pending} /></div>
    <div className="library-form-row"><div className="field"><label htmlFor="issue-severity">Severity</label><select id="issue-severity" value={form.severity} onChange={(event) => change('severity', event.target.value)} disabled={pending}>{Object.entries(issueSeverities).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
      {editing && <div className="field"><label htmlFor="issue-status">Status</label><select id="issue-status" value={form.status} onChange={(event) => change('status', event.target.value)} disabled={pending}>{Object.entries(issueStatuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>}
    </div>
    <footer>{onCancel && <button type="button" className="secondary-button" onClick={onCancel} disabled={pending}>Cancel</button>}<button className="primary-button" disabled={pending}>{pending ? 'Saving...' : editing ? 'Save changes' : 'Create Issue'}</button></footer>
    <p role="status">{notice}</p>
  </form>
}
