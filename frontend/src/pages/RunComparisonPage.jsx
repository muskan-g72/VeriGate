import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowDown, ArrowUp, ArrowUpDown, CheckCircle2, CircleMinus, Search, XCircle } from 'lucide-react'
import { verificationRunsApi } from '../api/client'
import { comparisonCategories, defaultComparisonCategories, filterComparisonRows, formatDuration, formatDurationDelta } from '../runComparison'
import { formatRunDate } from '../verification'

const categories = comparisonCategories
const labels = { regressed: 'Regressed', changed_other: 'Changed', added: 'Added', removed: 'Removed', improved: 'Improved', unchanged: 'Unchanged' }
const statusIcon = (status) => status === 'passed' ? <CheckCircle2 aria-hidden="true" /> : status === 'failed' || status === 'blocked' ? <XCircle aria-hidden="true" /> : <CircleMinus aria-hidden="true" />

export function RunComparisonPage() {
  const [params] = useSearchParams(); const navigate = useNavigate()
  const baselineId = params.get('baseline'); const targetId = params.get('target')
  const [data, setData] = useState(null); const [error, setError] = useState(''); const [search, setSearch] = useState(''); const [sort, setSort] = useState('default'); const [active, setActive] = useState(() => new Set(defaultComparisonCategories))
  useEffect(() => { let current = true; if (!baselineId || !targetId) { setError('Choose two completed runs to compare.'); return undefined }
    verificationRunsApi.compare(targetId, baselineId).then((value) => { if (current) { setData(value); setError('') } }).catch((err) => { if (current) { setData(null); setError(err.message) } })
    return () => { current = false }
  }, [baselineId, targetId])
  const rows = useMemo(() => { if (!data) return []; const filtered = filterComparisonRows(data.rows, active, search)
    return [...filtered].sort((a, b) => sort === 'duration' ? Math.abs(b.duration_delta || 0) - Math.abs(a.duration_delta || 0) : sort === 'priority' ? ['critical', 'high', 'medium', 'low'].indexOf(a.priority) - ['critical', 'high', 'medium', 'low'].indexOf(b.priority) : 0)
  }, [data, active, search, sort])
  const toggle = (category) => setActive((old) => { const next = new Set(old); next.has(category) ? next.delete(category) : next.add(category); return next })
  const swap = () => navigate(`/app/runs/compare?baseline=${encodeURIComponent(targetId)}&target=${encodeURIComponent(baselineId)}`)
  if (error) return <main className="library-page comparison-page"><div className="projects-state projects-state--error" role="alert"><p>{error}</p><Link className="secondary-button" to="/app/runs">Back to runs</Link></div></main>
  if (!data) return <main className="library-page comparison-page"><div className="projects-state" role="status">Loading run comparison...</div></main>
  const { baseline, target, summary } = data
  return <main className="library-page comparison-page">
    <Link className="library-link-button" to={`/app/verification-runs/${target.id}`}>Back to target run</Link>
    <header className="comparison-header"><RunHeader label="Before" run={baseline} /><button className="secondary-button comparison-swap" onClick={swap} title="Swap baseline and target"><ArrowUpDown size={16} /> Swap</button><RunHeader label="After" run={target} /></header>
    <section className="comparison-summary" aria-label="Comparison summary">{categories.map((key) => <article key={key}><span>{labels[key]}</span><strong>{summary.counts[key]}</strong></article>)}<article><span>Pass rate</span><strong>{summary.baseline_pass_rate ?? '—'}% → {summary.target_pass_rate ?? '—'}%</strong><small>{signed(summary.pass_rate_delta, ' pp')}</small></article><article><span>Total duration</span><strong>{formatDuration(summary.baseline_total_duration)} → {formatDuration(summary.target_total_duration)}</strong><small>{formatDurationDelta(summary.total_duration_delta)}</small></article>{data.gate_changed && <article className="comparison-gate"><span>Quality gate</span><strong>{baseline.gate_outcome || 'none'} → {target.gate_outcome || 'none'}</strong></article>}</section>
    <section className="comparison-toolbar"><div className="comparison-chips"><button className={!active.size ? 'active' : ''} onClick={() => setActive(new Set())}>All ({data.rows.length})</button>{categories.map((key) => <button key={key} className={active.has(key) ? 'active' : ''} onClick={() => toggle(key)}>{labels[key]} ({summary.counts[key]})</button>)}</div><label className="comparison-search"><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search test cases" /></label><select value={sort} onChange={(event) => setSort(event.target.value)} aria-label="Sort comparison"><option value="default">Default order</option><option value="duration">Duration delta</option><option value="priority">Priority</option></select></section>
    {!rows.length ? <section className="projects-state">{data.rows.length ? 'No test cases match these filters.' : 'No differences between these runs'}</section> : <div className="comparison-table-wrap"><table className="comparison-table"><thead><tr><th>Test case</th><th>Priority</th><th>Before</th><th>After</th><th>Change</th><th>Duration</th></tr></thead><tbody>{rows.map((row) => <tr key={row.test_case_id}><td><strong>{row.title}</strong>{row.target_failure_message && <details className="comparison-failure"><summary>Failure message</summary><p>{row.target_failure_message}</p></details>}</td><td>{row.priority}</td><td>{row.baseline_result_id ? <Link className={`comparison-status ${row.baseline_status}`} to={`/app/verification-runs/${baseline.id}#result-${row.baseline_result_id}`}>{statusIcon(row.baseline_status)}{row.baseline_status}</Link> : '—'}</td><td>{row.target_result_id ? <Link className={`comparison-status ${row.target_status}`} to={`/app/verification-runs/${target.id}#result-${row.target_result_id}`}>{statusIcon(row.target_status)}{row.target_status}</Link> : '—'}</td><td><span className={`comparison-category ${row.category}`}>{labels[row.category]}</span></td><td>{formatDuration(row.baseline_duration)} → {formatDuration(row.target_duration)}<small className={row.slower ? 'slower' : row.faster ? 'faster' : ''}>{formatDurationDelta(row.duration_delta)}{row.slower ? ' slower' : row.faster ? ' faster' : ''}</small></td></tr>)}</tbody></table></div>}
  </main>
}
function RunHeader({ label, run }) { return <section className="comparison-run"><span>{label}</span><h2>{run.name}</h2><p>{formatRunDate(run.created_at)} · {run.status}</p>{run.pr_number && <p>PR #{run.pr_number}{run.pr_commit_sha && ` · ${run.pr_commit_sha.slice(0, 7)}`}</p>}</section> }
function signed(value, suffix = '') { return value == null ? '—' : `${value > 0 ? '+' : ''}${value}${suffix}` }
