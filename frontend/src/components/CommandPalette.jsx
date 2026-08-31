import { Search, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

const commands = [{ name: 'Overview', path: '/app' }, { name: 'Projects', path: '/app/projects' }, { name: 'Test Library', path: '/app/test-library' }, { name: 'Test Suites', path: '/app/test-suites' }, { name: 'Test Cases', path: '/app/test-cases' }, { name: 'Runs — Coming soon' }, { name: 'Issues — Coming soon' }, { name: 'Settings — Coming soon' }]
export function CommandPalette({ open, onClose }) {
  const navigate = useNavigate()
  const inputRef = useRef(null)
  const [query, setQuery] = useState('')
  useEffect(() => { if (open) requestAnimationFrame(() => inputRef.current?.focus()) }, [open])
  useEffect(() => { const close = (event) => event.key === 'Escape' && onClose(); document.addEventListener('keydown', close); return () => document.removeEventListener('keydown', close) }, [onClose])
  if (!open) return null
  const filtered = commands.filter((command) => command.name.toLowerCase().includes(query.toLowerCase()))
  const select = (command) => { if (!command.path) return; navigate(command.path); setQuery(''); onClose() }
  return <div className="dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="command-dialog" role="dialog" aria-modal="true" aria-label="Command palette"><div className="command-search"><Search /><input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search commands…" aria-label="Search commands" /><button onClick={onClose} aria-label="Close command palette"><X /></button></div><p className="command-label">Navigate</p><div className="command-list">{filtered.map((command) => <button key={command.name} disabled={!command.path} onClick={() => select(command)}><span>{command.name}</span>{command.path && <kbd>Enter</kbd>}</button>)}{filtered.length === 0 && <p className="command-empty">No matching commands</p>}</div></section></div>
}
