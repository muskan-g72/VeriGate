import { LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { dashboardApi } from '../api/client'

export function ProjectSummaryPage() {
  const { projectId } = useParams(); const [summary, setSummary] = useState(null); const [error, setError] = useState('')
  useEffect(() => { let active = true; dashboardApi.projectSummary(projectId).then((data) => { if (active) setSummary(data) }).catch((err) => { if (active) setError(err.message) }); return () => { active = false } }, [projectId])
  if (error) return <main className="library-page"><div className="projects-state projects-state--error"><p>{error}</p><Link className="secondary-button" to="/app/projects">Back to Projects</Link></div></main>
  if (!summary) return <main className="library-page"><div className="projects-state"><LoaderCircle className="spinner" /><p>Loading project summary...</p></div></main>
  const result = summary.verification_results
  return <main className="library-page"><section className="library-heading"><div><p className="eyebrow">Project dashboard</p><h2>{summary.project.name}</h2><p>{summary.project.description || 'No description provided.'}</p></div><Link className="secondary-button" to="/app/projects">Back to Projects</Link></section><section className="runs-metrics">{[['Test suites', summary.test_suites], ['Test cases', summary.test_cases], ['Verification runs', summary.verification_runs], ['Pass rate', `${result.pass_rate}%`]].map(([label, value]) => <article key={label}><span>{label}</span><strong>{value}</strong></article>)}</section><section className="access-grid"><article className="report-panel"><h3>Verification results</h3><ul className="simple-list">{Object.entries(result).filter(([key]) => key !== 'pass_rate' && key !== 'total').map(([key, value]) => <li key={key}><strong>{key}</strong><span>{value}</span></li>)}</ul></article><article className="report-panel"><h3>Issues</h3><ul className="simple-list"><li><strong>Open</strong><span>{summary.issues.open}</span></li><li><strong>Resolved</strong><span>{summary.issues.resolved}</span></li></ul>{summary.latest_run && <p>Latest run: {summary.latest_run.name} ({summary.latest_run.status})</p>}</article></section></main>
}
