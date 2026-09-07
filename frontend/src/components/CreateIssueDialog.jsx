import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import { issuesApi } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { issueDraft } from '../issues'
import { IssueForm } from './IssueForm'

export function CreateIssueDialog({ result, testCase, onClose, onCreated }) {
  const dialog = useRef(null)
  const [pending, setPending] = useState(false)
  const { logout } = useAuth()
  useEffect(() => {
    const previous = document.activeElement
    const element = dialog.current
    element.showModal()
    return () => { element.close(); previous?.focus() }
  }, [])
  async function create(data) {
    try { const issue = await issuesApi.createFromResult(result.id, data); onCreated(issue); return issue }
    catch (error) { if (error.code === 'unauthorized') logout('Your session expired. Sign in again.'); throw error }
  }
  return <dialog ref={dialog} className="project-dialog library-dialog verification-dialog" aria-labelledby="create-issue-heading" onCancel={(event) => { event.preventDefault(); if (!pending) onClose() }}>
    <header><div><p className="eyebrow">Report verification finding</p><h2 id="create-issue-heading">Create Issue</h2></div><button onClick={onClose} disabled={pending} aria-label="Close"><X /></button></header>
    <IssueForm initial={issueDraft(result, testCase)} onSave={create} onCancel={onClose} onPendingChange={setPending} />
  </dialog>
}
