import { CalendarDays, Layers3, LoaderCircle, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { projectsApi, testSuitesApi } from '../api/client'
import { chooseProject, rememberProject } from '../testLibrary/projectSelection'
import { LibraryDialog } from './TestLibraryPage'

export function TestSuitesPage() {
  const [projects, setProjects] = useState([]), [projectId, setProjectId] = useState('')
  const [suites, setSuites] = useState([]), [status, setStatus] = useState('loading')
  const [error, setError] = useState(''), [editing, setEditing] = useState(undefined)
  useEffect(() => { let active = true; projectsApi.list().then((items) => { if (!active) return; setProjects(items); setProjectId(chooseProject(items)); if (!items.length) setStatus('ready') }).catch((requestError) => { if (active) { setError(requestError.message); setStatus('error') } }); return () => { active = false } }, [])
  useEffect(() => { if (!projectId) return undefined; let active = true; testSuitesApi.list(projectId).then((items) => { if (active) { setSuites(items); setStatus('ready') } }).catch((requestError) => { if (active) { setError(requestError.message); setStatus('error') } }); return () => { active = false } }, [projectId])
  function changeProject(id) { rememberProject(id); setProjectId(id); setSuites([]); setStatus('loading'); setError('') }
  function save(saved) { setSuites((current) => current.some((suite) => suite.id === saved.id) ? current.map((suite) => suite.id === saved.id ? saved : suite) : [saved, ...current]); setEditing(undefined) }
  async function remove(suite) { if (!window.confirm(`Delete “${suite.name}” and all of its test cases?`)) return; try { await testSuitesApi.remove(suite.id); setSuites((current) => current.filter((item) => item.id !== suite.id)) } catch (requestError) { setError(requestError.message) } }
  const selectedProject = projects.find((project) => project.id === projectId)
  return <main className="library-page suites-view"><section className="library-heading"><div><p className="eyebrow">Project test organization</p><h2>Test Suites</h2><p>View and manage every suite in the selected project.</p></div>{projects.length > 0 && <label>Project<select value={projectId} onChange={(event) => changeProject(event.target.value)}>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>}</section>
    {error && <div className="library-alert" role="alert"><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X /></button></div>}
    {status === 'loading' && <div className="projects-state"><LoaderCircle className="spinner" /><p>Loading test suites...</p></div>}
    {status === 'ready' && !projects.length && <section className="projects-empty"><div><Layers3 /></div><p className="eyebrow">Project required</p><h3>Create a project first</h3><p>Every test suite belongs to a project.</p><Link className="library-link-button" to="/app/projects"><Plus />Create project</Link></section>}
    {status === 'ready' && projects.length > 0 && <><div className="view-toolbar"><div><strong>{suites.length}</strong><span>suite{suites.length === 1 ? '' : 's'} in {selectedProject?.name}</span></div><button className="new-project-button" onClick={() => setEditing(null)}><Plus />New suite</button></div>{!suites.length ? <section className="projects-empty"><div><Layers3 /></div><p className="eyebrow">No suites yet</p><h3>Define the first test suite</h3><p>Group related cases into a reusable verification scope.</p><button onClick={() => setEditing(null)}><Plus />Create suite</button></section> : <section className="suite-grid">{suites.map((suite) => <article className="suite-card" key={suite.id}><div className="project-card__icon"><Layers3 /></div><p className="eyebrow">Test suite</p><h3>{suite.name}</h3><p>{suite.description || 'No description provided.'}</p><footer><span><CalendarDays />Updated {new Date(suite.updated_at).toLocaleDateString()}</span><div><button onClick={() => setEditing(suite)} aria-label={`Edit ${suite.name}`}><Pencil />Edit</button><button className="danger-action" onClick={() => remove(suite)} aria-label={`Delete ${suite.name}`}><Trash2 />Delete</button></div></footer></article>)}</section>}</>}
    {editing !== undefined && <LibraryDialog kind="suite" item={editing} parentId={projectId} onClose={() => setEditing(undefined)} onSaved={save} />}
  </main>
}
