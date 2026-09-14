import {
  AlertTriangle,
  History,
  LoaderCircle,
  RefreshCw,
  Search,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { adminApi } from '../../api/client'

const formatDateTime = (dateStr) => {
  if (!dateStr) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'medium',
  }).format(new Date(dateStr))
}

export function AdminAuditLogsPage() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [search, setSearch] = useState('')
  const [actionFilter, setActionFilter] = useState('all')
  const [resourceFilter, setResourceFilter] = useState('all')
  const [error, setError] = useState('')

  async function loadLogs(isBackground = false) {
    if (isBackground) setRefreshing(true)
    else setLoading(true)
    setError('')
    try {
      const data = await adminApi.auditLogs()
      setLogs(data || [])
    } catch (err) {
      setError(err.message || 'Failed to load audit logs.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadLogs()
  }, [])

  const uniqueActions = useMemo(() => {
    const set = new Set(logs.map((l) => l.action).filter(Boolean))
    return Array.from(set).sort()
  }, [logs])

  const uniqueResources = useMemo(() => {
    const set = new Set(logs.map((l) => l.resource_type).filter(Boolean))
    return Array.from(set).sort()
  }, [logs])

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const q = search.toLowerCase().trim()
      const matchesSearch =
        !q ||
        (log.description && log.description.toLowerCase().includes(q)) ||
        (log.action && log.action.toLowerCase().includes(q)) ||
        (log.user?.email && log.user.email.toLowerCase().includes(q))

      const matchesAction = actionFilter === 'all' || log.action === actionFilter
      const matchesResource =
        resourceFilter === 'all' || log.resource_type === resourceFilter

      return matchesSearch && matchesAction && matchesResource
    })
  }, [logs, search, actionFilter, resourceFilter])

  return (
    <main className="command-center" aria-label="Admin Audit Logs">
      {/* Header */}
      <section className="command-center-header">
        <div>
          <p className="eyebrow">
            <span className="live-dot" /> GOVERNANCE &amp; COMPLIANCE
          </p>
          <h2>System Audit Trail</h2>
          <p className="command-subtitle">
            Immutable chronicle of authentication, administrative role changes, project modifications, and verification runs.
          </p>
        </div>

        <div className="command-controls">
          <button
            type="button"
            className="secondary-button icon-btn"
            onClick={() => loadLogs(true)}
            disabled={refreshing || loading}
            title="Refresh logs"
            aria-label="Refresh logs"
          >
            <RefreshCw className={refreshing ? 'spinner-fast' : ''} size={15} />
          </button>
        </div>
      </section>

      {/* Error Banner */}
      {error && (
        <div className="form-alert" role="alert" style={{ marginBottom: '16px' }}>
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button type="button" className="link-button" onClick={() => loadLogs(false)}>
            Retry
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <section className="report-panel" style={{ marginBottom: '20px', padding: '16px 20px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Search */}
          <div style={{ position: 'relative', minWidth: '280px', flex: 1 }}>
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-3)' }} />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search audit descriptions, actions, actors..."
              style={{
                width: '100%',
                padding: '9px 12px 9px 36px',
                borderRadius: '8px',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: '#fff',
                fontSize: '13px',
              }}
            />
          </div>

          {/* Action and Resource Filters */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-3)' }}>Action:</span>
              <select
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="access-select"
                style={{ height: '34px', fontSize: '12px', padding: '0 10px' }}
              >
                <option value="all">All Actions ({logs.length})</option>
                {uniqueActions.map((act) => (
                  <option key={act} value={act}>
                    {act}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-3)' }}>Resource:</span>
              <select
                value={resourceFilter}
                onChange={(e) => setResourceFilter(e.target.value)}
                className="access-select"
                style={{ height: '34px', fontSize: '12px', padding: '0 10px' }}
              >
                <option value="all">All Resources</option>
                {uniqueResources.map((res) => (
                  <option key={res} value={res}>
                    {res}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </section>

      {/* Logs Table */}
      <section className="report-panel" style={{ padding: 0, overflow: 'hidden' }}>
        {loading && !logs.length ? (
          <div className="projects-state" role="status" style={{ padding: '40px' }}>
            <LoaderCircle className="spinner" />
            <p>Loading audit trail records...</p>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text-3)' }}>
            <History size={32} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
            <p style={{ fontSize: '14px', margin: 0 }}>No audit events found.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.02)' }}>
                  <th style={{ padding: '14px 20px', fontWeight: 500, color: 'var(--text-3)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', width: '200px' }}>Timestamp</th>
                  <th style={{ padding: '14px 20px', fontWeight: 500, color: 'var(--text-3)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', width: '150px' }}>Action</th>
                  <th style={{ padding: '14px 20px', fontWeight: 500, color: 'var(--text-3)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Event Details</th>
                  <th style={{ padding: '14px 20px', fontWeight: 500, color: 'var(--text-3)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', width: '220px' }}>Actor</th>
                  <th style={{ padding: '14px 20px', fontWeight: 500, color: 'var(--text-3)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', width: '120px' }}>Resource</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log) => {
                  const isFailure = log.action.includes('fail') || log.action.includes('inactive')
                  const isRole = log.action.includes('role')
                  const isAuth = log.action.includes('login') || log.action.includes('user')
                  return (
                    <tr
                      key={log.id}
                      style={{
                        borderBottom: '1px solid rgba(255,255,255,0.04)',
                        transition: 'background 0.15s ease',
                      }}
                    >
                      <td style={{ padding: '14px 20px', color: 'var(--text-3)', fontSize: '12px', whiteSpace: 'nowrap' }}>
                        {formatDateTime(log.created_at)}
                      </td>
                      <td style={{ padding: '14px 20px' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 500,
                          fontFamily: 'var(--mono)',
                          textTransform: 'uppercase',
                          background: isFailure
                            ? 'rgba(239,68,68,0.15)'
                            : isRole
                              ? 'rgba(192,132,252,0.15)'
                              : isAuth
                                ? 'rgba(96,165,250,0.15)'
                                : 'rgba(255,255,255,0.06)',
                          color: isFailure
                            ? '#f87171'
                            : isRole
                              ? '#c084fc'
                              : isAuth
                                ? '#93c5fd'
                                : 'var(--text-2)',
                        }}>
                          {log.action}
                        </span>
                      </td>
                      <td style={{ padding: '14px 20px', color: '#f3eef8', fontWeight: 500 }}>
                        {log.description || `${log.action} on ${log.resource_type}`}
                      </td>
                      <td style={{ padding: '14px 20px', color: 'var(--text-2)', fontSize: '12px' }}>
                        {log.user?.email ? (
                          <span>{log.user.email}</span>
                        ) : (
                          <span style={{ color: 'var(--text-3)', fontStyle: 'italic' }}>Anonymous / System</span>
                        )}
                      </td>
                      <td style={{ padding: '14px 20px' }}>
                        <span style={{
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          background: 'rgba(255,255,255,0.05)',
                          color: 'var(--text-3)',
                          textTransform: 'capitalize',
                        }}>
                          {log.resource_type}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  )
}
