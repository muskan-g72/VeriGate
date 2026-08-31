import { ArrowRight, Boxes, CalendarDays, LoaderCircle, Pencil, Plus, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { projectsApi } from '../api/client'

const emptyForm = { name: '', description: '' }

function ProjectDialog({ project, onClose, onSaved }) {
  const [form, setForm] = useState(() => project ? { name: project.name, description: project.description || '' } : emptyForm)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const nameRef = useRef(null)

  useEffect(() => { nameRef.current?.focus() }, [])
  useEffect(() => {
    const handleKey = (event) => event.key === 'Escape' && !pending && onClose()
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose, pending])

  async function submit(event) {
    event.preventDefault()
    const name = form.name.trim()
    if (!name) { setError('Enter a project name.'); return }
    setPending(true); setError('')
    const payload = { name, description: form.description.trim() || null }
    try {
      const saved = project ? await projectsApi.update(project.id, payload) : await projectsApi.create(payload)
      onSaved(saved)
    } catch (requestError) {
      setError(requestError.message)
    } finally { setPending(false) }
  }

  return <div className="dialog-backdrop project-dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && !pending && onClose()}>
    <section className="project-dialog" role="dialog" aria-modal="true" aria-labelledby="project-dialog-title">
      <header><div><p className="eyebrow">{project ? 'Update record' : 'New verification record'}</p><h2 id="project-dialog-title">{project ? 'Edit project' : 'Create project'}</h2></div><button onClick={onClose} disabled={pending} aria-label="Close"><X /></button></header>
      <form onSubmit={submit} noValidate>
        {error && <div className="form-alert" role="alert"><strong>Unable to save project</strong><span>{error}</span></div>}
        <div className="field"><label htmlFor="project-name">Project name</label><input ref={nameRef} id="project-name" maxLength={120} value={form.name} disabled={pending} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Backend verification" /></div>
        <div className="field"><label htmlFor="project-description">Description <span>Optional</span></label><textarea id="project-description" rows="5" value={form.description} disabled={pending} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="What will this project verify?" /></div>
        <footer><button type="button" className="secondary-button" onClick={onClose} disabled={pending}>Cancel</button><button className="primary-button" disabled={pending}>{pending ? <><LoaderCircle className="spinner" />Saving...</> : <>{project ? 'Save changes' : 'Create project'}<ArrowRight /></>}</button></footer>
      </form>
    </section>
  </div>
}

const formatDate = (value) => new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))

export function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(undefined)

  async function loadProjects() {
    try { setProjects(await projectsApi.list()); setStatus('ready') }
    catch (requestError) { setError(requestError.message); setStatus('error') }
  }
  useEffect(() => {
    let active = true
    projectsApi.list().then((result) => {
      if (active) { setProjects(result); setStatus('ready') }
    }).catch((requestError) => {
      if (active) { setError(requestError.message); setStatus('error') }
    })
    return () => { active = false }
  }, [])

  function retryLoad() {
    setStatus('loading'); setError(''); loadProjects()
  }

  function saveProject(saved) {
    setProjects((current) => {
      const exists = current.some((project) => project.id === saved.id)
      return exists ? current.map((project) => project.id === saved.id ? saved : project) : [saved, ...current]
    })
    setEditing(undefined)
  }

  return <main className="projects-page">
    <section className="projects-heading"><div><p className="eyebrow">Verification workspace</p><h2>Projects</h2><p>Create a durable home for test suites, runs, evidence, and issues.</p></div><button className="new-project-button" onClick={() => setEditing(null)}><Plus />New project</button></section>
    {status === 'loading' && <div className="projects-state"><LoaderCircle className="spinner" /><p>Loading projects...</p></div>}
    {status === 'error' && <div className="projects-state projects-state--error"><p>{error}</p><button onClick={retryLoad}>Try again</button></div>}
    {status === 'ready' && projects.length === 0 && <section className="projects-empty"><div><Boxes /></div><p className="eyebrow">No records yet</p><h3>Create your first project</h3><p>Start with a name and description. You can refine the project as your verification scope grows.</p><button onClick={() => setEditing(null)}><Plus />Create project</button></section>}
    {status === 'ready' && projects.length > 0 && <section className="project-grid" aria-label="Projects">{projects.map((project) => <article className="project-card" key={project.id}>
      <div className="project-card__icon"><Boxes /></div><div className="project-card__content"><p className="eyebrow">Project</p><h3>{project.name}</h3><p>{project.description || 'No description provided.'}</p></div><footer><span><CalendarDays />Updated {formatDate(project.updated_at)}</span><button onClick={() => setEditing(project)} aria-label={`Edit ${project.name}`}><Pencil />Edit</button></footer>
    </article>)}</section>}
    {editing !== undefined && <ProjectDialog project={editing} onClose={() => setEditing(undefined)} onSaved={saveProject} />}
  </main>
}
