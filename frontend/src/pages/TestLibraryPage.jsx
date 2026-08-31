import { ArrowRight, BookOpen, CheckCircle2, ChevronRight, FileCheck2, Layers3, LoaderCircle, Pencil, Plus, Power, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { projectsApi, testCasesApi, testSuitesApi } from '../api/client'
import { chooseProject, rememberProject } from '../testLibrary/projectSelection'

export function LibraryDialog({ kind, item, parentId, onClose, onSaved }) {
  const isCase = kind === 'case'
  const [form, setForm] = useState(() => isCase ? {
    title: item?.title || '', description: item?.description || '', steps: item?.steps || '',
    expected_result: item?.expected_result || '', priority: item?.priority || 'medium', is_active: item?.is_active ?? true,
  } : { name: item?.name || '', description: item?.description || '' })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [pending, setPending] = useState(false)
  const firstInput = useRef(null)
  useEffect(() => { firstInput.current?.focus() }, [])
  useEffect(() => { const close = (event) => event.key === 'Escape' && !pending && onClose(); document.addEventListener('keydown', close); return () => document.removeEventListener('keydown', close) }, [onClose, pending])

  async function submit(event) {
    event.preventDefault()
    const next = {}
    if (!(isCase ? form.title : form.name).trim()) next.name = `Enter a ${isCase ? 'test case title' : 'suite name'}.`
    if (isCase && !form.steps.trim()) next.steps = 'Describe the steps to execute.'
    if (isCase && !form.expected_result.trim()) next.expected_result = 'Describe the expected result.'
    setErrors(next); setServerError('')
    if (Object.keys(next).length) return
    setPending(true)
    const payload = isCase ? { ...form, title: form.title.trim(), description: form.description.trim() || null, steps: form.steps.trim(), expected_result: form.expected_result.trim() } : { name: form.name.trim(), description: form.description.trim() || null }
    try {
      const saved = isCase
        ? (item ? await testCasesApi.update(item.id, payload) : await testCasesApi.create(parentId, payload))
        : (item ? await testSuitesApi.update(item.id, payload) : await testSuitesApi.create(parentId, payload))
      onSaved(saved)
    } catch (error) { setServerError(error.message) }
    finally { setPending(false) }
  }

  const title = `${item ? 'Edit' : 'Create'} test ${isCase ? 'case' : 'suite'}`
  return <div className="dialog-backdrop library-dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && !pending && onClose()}><section className="project-dialog library-dialog" role="dialog" aria-modal="true" aria-labelledby="library-dialog-title">
    <header><div><p className="eyebrow">Test definition</p><h2 id="library-dialog-title">{title}</h2></div><button onClick={onClose} disabled={pending} aria-label="Close"><X /></button></header>
    <form onSubmit={submit} noValidate>{serverError && <div className="form-alert" role="alert"><strong>Unable to save</strong><span>{serverError}</span></div>}
      <div className="field"><label htmlFor="definition-name">{isCase ? 'Title' : 'Suite name'}</label><input ref={firstInput} id="definition-name" maxLength={isCase ? 160 : 120} value={isCase ? form.title : form.name} disabled={pending} aria-invalid={Boolean(errors.name)} onChange={(event) => setForm({ ...form, [isCase ? 'title' : 'name']: event.target.value })} placeholder={isCase ? 'Valid user can sign in' : 'Authentication'} /><div className={`field-error ${errors.name ? 'is-visible' : ''}`} role="alert">{errors.name}</div></div>
      <div className="field"><label htmlFor="definition-description">Description <span>Optional</span></label><textarea id="definition-description" rows="3" value={form.description} disabled={pending} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Describe the verification scope." /></div>
      {isCase && <><div className="field"><label htmlFor="case-steps">Execution steps</label><textarea id="case-steps" rows="4" value={form.steps} disabled={pending} aria-invalid={Boolean(errors.steps)} onChange={(event) => setForm({ ...form, steps: event.target.value })} placeholder={'1. Enter valid credentials\n2. Submit the login form'} /><div className={`field-error ${errors.steps ? 'is-visible' : ''}`} role="alert">{errors.steps}</div></div><div className="field"><label htmlFor="case-expected">Expected result</label><textarea id="case-expected" rows="3" value={form.expected_result} disabled={pending} aria-invalid={Boolean(errors.expected_result)} onChange={(event) => setForm({ ...form, expected_result: event.target.value })} placeholder="The user is authenticated and redirected." /><div className={`field-error ${errors.expected_result ? 'is-visible' : ''}`} role="alert">{errors.expected_result}</div></div><div className="library-form-row"><div className="field"><label htmlFor="case-priority">Priority</label><select id="case-priority" value={form.priority} disabled={pending} onChange={(event) => setForm({ ...form, priority: event.target.value })}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></div>{item && <label className="active-toggle"><input type="checkbox" checked={form.is_active} disabled={pending} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} /><span>Active test case</span></label>}</div></>}
      <footer><button type="button" className="secondary-button" onClick={onClose} disabled={pending}>Cancel</button><button className="primary-button" disabled={pending}>{pending ? <><LoaderCircle className="spinner" />Saving...</> : <>Save {isCase ? 'case' : 'suite'}<ArrowRight /></>}</button></footer>
    </form>
  </section></div>
}

export function TestLibraryPage() {
  const [projects, setProjects] = useState([])
  const [projectId, setProjectId] = useState('')
  const [suites, setSuites] = useState([])
  const [suiteId, setSuiteId] = useState('')
  const [cases, setCases] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [dialog, setDialog] = useState(null)

  useEffect(() => { let active = true; projectsApi.list().then((items) => { if (!active) return; const selected = chooseProject(items); setProjects(items); setProjectId(selected); setStatus(items.length ? 'loading' : 'ready') }).catch((requestError) => { if (active) { setError(requestError.message); setStatus('error') } }); return () => { active = false } }, [])
  useEffect(() => { if (!projectId) return undefined; let active = true; testSuitesApi.list(projectId).then((items) => { if (!active) return; setSuites(items); setSuiteId((current) => items.some((suite) => suite.id === current) ? current : items[0]?.id || ''); setStatus('ready') }).catch((requestError) => { if (active) { setError(requestError.message); setStatus('error') } }); return () => { active = false } }, [projectId])
  useEffect(() => { if (!suiteId) return undefined; let active = true; testCasesApi.list(suiteId).then((items) => { if (active) setCases(items) }).catch((requestError) => { if (active) setError(requestError.message) }); return () => { active = false } }, [suiteId])

  const selectedProject = projects.find((project) => project.id === projectId)
  const selectedSuite = suites.find((suite) => suite.id === suiteId)
  function savedSuite(saved) { setSuites((current) => current.some((suite) => suite.id === saved.id) ? current.map((suite) => suite.id === saved.id ? saved : suite) : [saved, ...current]); setSuiteId(saved.id); setDialog(null) }
  function savedCase(saved) { setCases((current) => current.some((testCase) => testCase.id === saved.id) ? current.map((testCase) => testCase.id === saved.id ? saved : testCase) : [saved, ...current]); setDialog(null) }
  async function toggleCase(testCase) { try { const saved = await testCasesApi.update(testCase.id, { is_active: !testCase.is_active }); savedCase(saved) } catch (requestError) { setError(requestError.message) } }
  function changeProject(nextProjectId) { rememberProject(nextProjectId); setProjectId(nextProjectId); setSuites([]); setSuiteId(''); setCases([]); setStatus('loading'); setError('') }

  return <main className="library-page"><section className="library-heading"><div><p className="eyebrow">Reusable verification definitions</p><h2>Test Library</h2><p>Organize executable cases into project-owned suites.</p></div>{projects.length > 0 && <label>Project<select value={projectId} onChange={(event) => changeProject(event.target.value)}>{projects.map((project) => <option value={project.id} key={project.id}>{project.name}</option>)}</select></label>}</section>
    {error && <div className="library-alert" role="alert"><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X /></button></div>}
    {status === 'loading' && !projects.length && <div className="projects-state"><LoaderCircle className="spinner" /><p>Loading test library...</p></div>}
    {status === 'error' && !projects.length && <div className="projects-state projects-state--error"><p>{error}</p></div>}
    {status === 'ready' && projects.length === 0 && <section className="projects-empty"><div><BookOpen /></div><p className="eyebrow">Project required</p><h3>Create a project first</h3><p>Test suites belong to a project. Create your first project before defining the test library.</p><Link className="library-link-button" to="/app/projects"><Plus />Create project</Link></section>}
    {projects.length > 0 && <div className="library-layout"><aside className="suite-panel"><header><div><p>Test suites</p><span>{suites.length}</span></div><button onClick={() => setDialog({ kind: 'suite' })} aria-label="Create test suite"><Plus /></button></header>{status === 'loading' && <div className="suite-loading"><LoaderCircle className="spinner" /></div>}{status !== 'loading' && suites.length === 0 && <div className="suite-empty"><Layers3 /><p>No suites in<br /><strong>{selectedProject?.name}</strong></p><button onClick={() => setDialog({ kind: 'suite' })}>Create suite</button></div>}{suites.map((suite) => <button className={`suite-row ${suite.id === suiteId ? 'is-selected' : ''}`} key={suite.id} onClick={() => setSuiteId(suite.id)}><Layers3 /><span><strong>{suite.name}</strong><small>{suite.description || 'No description'}</small></span><ChevronRight /></button>)}</aside>
      <section className="cases-panel">{selectedSuite ? <><header><div><p className="eyebrow">{selectedProject?.name}</p><h3>{selectedSuite.name}</h3><p>{selectedSuite.description || 'No suite description provided.'}</p></div><div><button className="secondary-button" onClick={() => setDialog({ kind: 'suite', item: selectedSuite })}><Pencil />Edit suite</button><button className="new-project-button" onClick={() => setDialog({ kind: 'case' })}><Plus />New test case</button></div></header>{cases.length === 0 ? <div className="case-empty"><FileCheck2 /><h4>No test cases yet</h4><p>Define the executable steps and expected result for this suite.</p><button onClick={() => setDialog({ kind: 'case' })}><Plus />Create test case</button></div> : <div className="case-list">{cases.map((testCase) => <article className={`case-card ${!testCase.is_active ? 'is-inactive' : ''}`} key={testCase.id}><div className="case-status"><CheckCircle2 /></div><div className="case-body"><div><span className={`priority priority--${testCase.priority}`}>{testCase.priority}</span><span className="case-activity">{testCase.is_active ? 'Active' : 'Inactive'}</span></div><h4>{testCase.title}</h4><p>{testCase.description || 'No description provided.'}</p><details><summary>Execution definition</summary><div><strong>Steps</strong><pre>{testCase.steps}</pre><strong>Expected result</strong><p>{testCase.expected_result}</p></div></details></div><div className="case-actions"><button onClick={() => setDialog({ kind: 'case', item: testCase })} aria-label={`Edit ${testCase.title}`}><Pencil /></button><button onClick={() => toggleCase(testCase)} aria-label={`${testCase.is_active ? 'Deactivate' : 'Activate'} ${testCase.title}`}><Power /></button></div></article>)}</div>}</> : <div className="case-empty"><Layers3 /><h4>Select or create a suite</h4><p>Choose a suite to view its test cases.</p></div>}</section></div>}
    {dialog && <LibraryDialog kind={dialog.kind} item={dialog.item} parentId={dialog.kind === 'case' ? suiteId : projectId} onClose={() => setDialog(null)} onSaved={dialog.kind === 'case' ? savedCase : savedSuite} />}
  </main>
}
