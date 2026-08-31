import { Search, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

const commands = ['Overview', 'Projects — Coming soon', 'Runs — Coming soon', 'Test Library — Coming soon', 'Issues — Coming soon', 'Settings — Coming soon']
export function CommandPalette({ open, onClose }) {
  const inputRef = useRef(null)
  const [query, setQuery] = useState('')
  useEffect(() => { if (open) requestAnimationFrame(() => inputRef.current?.focus()) }, [open])
  useEffect(() => { const close = (event) => event.key === 'Escape' && onClose(); document.addEventListener('keydown', close); return () => document.removeEventListener('keydown', close) }, [onClose])
  if (!open) return null
  const filtered = commands.filter((command) => command.toLowerCase().includes(query.toLowerCase()))
  return <div className="dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="command-dialog" role="dialog" aria-modal="true" aria-label="Command palette"><div className="command-search"><Search /><input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search commands…" aria-label="Search commands" /><button onClick={onClose} aria-label="Close command palette"><X /></button></div><p className="command-label">Navigate</p><div className="command-list">{filtered.map((command) => <button key={command} disabled={command !== 'Overview'} onClick={onClose}><span>{command}</span>{command === 'Overview' && <kbd>Enter</kbd>}</button>)}{filtered.length === 0 && <p className="command-empty">No matching commands</p>}</div></section></div>
}
