import {
  AlertTriangle,
  CheckCircle2,
  LoaderCircle,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  UserCheck,
  UserX,
  Users,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { adminApi } from '../../api/client'
import { useAuth } from '../../auth/useAuth'

const initials = (user) =>
  (user?.full_name || user?.email || 'VG')
    .split(/[\s@.]+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(dateStr))
}

export function AdminUsersPage() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [error, setError] = useState('')
  const [successNotice, setSuccessNotice] = useState('')

  // Modal dialog state for confirmations
  const [dialog, setDialog] = useState({
    open: false,
    type: null, // 'role' | 'status'
    user: null,
    targetValue: null,
  })
  const [actionPending, setActionPending] = useState(false)

  async function loadUsers(isBackground = false) {
    if (isBackground) setRefreshing(true)
    else setLoading(true)
    setError('')
    try {
      const data = await adminApi.users()
      setUsers(data || [])
    } catch (err) {
      setError(err.message || 'Failed to retrieve system users.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      const query = search.toLowerCase().trim()
      const matchesSearch =
        !query ||
        u.email.toLowerCase().includes(query) ||
        (u.full_name && u.full_name.toLowerCase().includes(query))
      const matchesRole =
        roleFilter === 'all' || (u.role || u.system_role) === roleFilter
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && u.is_active) ||
        (statusFilter === 'inactive' && !u.is_active)
      return matchesSearch && matchesRole && matchesStatus
    })
  }, [users, search, roleFilter, statusFilter])

  function openRoleConfirm(targetUser, newRole) {
    setDialog({
      open: true,
      type: 'role',
      user: targetUser,
      targetValue: newRole,
    })
  }

  function openStatusConfirm(targetUser, newStatus) {
    setDialog({
      open: true,
      type: 'status',
      user: targetUser,
      targetValue: newStatus,
    })
  }

  function closeDialog() {
    if (actionPending) return
    setDialog({ open: false, type: null, user: null, targetValue: null })
  }

  async function confirmAction() {
    if (!dialog.user || !dialog.type) return
    setActionPending(true)
    setError('')
    setSuccessNotice('')
    try {
      if (dialog.type === 'role') {
        const updated = await adminApi.updateUserRole(
          dialog.user.id,
          dialog.targetValue,
        )
        setUsers((current) =>
          current.map((u) => (u.id === updated.id ? updated : u)),
        )
        setSuccessNotice(
          `Successfully changed role of ${dialog.user.email} to ${dialog.targetValue.toUpperCase()}.`,
        )
      } else if (dialog.type === 'status') {
        const updated = await adminApi.updateUserStatus(
          dialog.user.id,
          dialog.targetValue,
        )
        setUsers((current) =>
          current.map((u) => (u.id === updated.id ? updated : u)),
        )
        setSuccessNotice(
          `Account for ${dialog.user.email} has been ${dialog.targetValue ? 'activated' : 'disabled'}.`,
        )
      }
      closeDialog()
    } catch (err) {
      setError(err.message || 'Operation failed.')
    } finally {
      setActionPending(false)
    }
  }

  return (
    <main className="command-center" aria-label="Admin User Governance">
      {/* Header */}
      <section className="command-center-header">
        <div>
          <p className="eyebrow">
            <span className="live-dot" /> ACCESS &amp; IDENTITY MANAGEMENT
          </p>
          <h2>User Directory</h2>
          <p className="command-subtitle">
            Inspect all platform accounts, audit permissions, and promote or adjust user roles safely.
          </p>
        </div>

        <div className="command-controls">
          <button
            type="button"
            className="secondary-button icon-btn"
            onClick={() => loadUsers(true)}
            disabled={refreshing || loading}
            title="Refresh directory"
            aria-label="Refresh directory"
          >
            <RefreshCw className={refreshing ? 'spinner-fast' : ''} size={15} />
          </button>
        </div>
      </section>

      {/* Alerts */}
      {error && (
        <div className="form-alert" role="alert" style={{ marginBottom: '16px' }}>
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button type="button" className="link-button" onClick={() => setError('')}>
            Dismiss
          </button>
        </div>
      )}
      {successNotice && (
        <div className="form-alert" role="status" style={{ marginBottom: '16px', borderColor: 'rgba(52,211,153,0.3)', background: 'rgba(5,150,105,0.08)' }}>
          <CheckCircle2 size={16} style={{ color: '#34d399' }} />
          <span style={{ color: '#6ee7b7' }}>{successNotice}</span>
          <button type="button" className="link-button" onClick={() => setSuccessNotice('')}>
            Dismiss
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
              placeholder="Search by name or email address..."
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

          {/* Filters */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-3)' }}>Role:</span>
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="access-select"
                style={{ height: '34px', fontSize: '12px', padding: '0 10px' }}
              >
                <option value="all">All Roles</option>
                <option value="admin">Admin</option>
                <option value="user">User</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-3)' }}>Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="access-select"
                style={{ height: '34px', fontSize: '12px', padding: '0 10px' }}
              >
                <option value="all">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Disabled</option>
              </select>
            </div>
          </div>
        </div>
      </section>

      {/* Users Data Table */}
      <section className="report-panel" style={{ padding: 0, overflow: 'hidden' }}>
        {loading && !users.length ? (
          <div className="projects-state" role="status" style={{ padding: '40px' }}>
            <LoaderCircle className="spinner" />
            <p>Loading user accounts...</p>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text-3)' }}>
            <Users size={32} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
            <p style={{ fontSize: '14px', margin: 0 }}>No users found matching current filters.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.02)' }}>
                  <th style={{ padding: '14px 20px', fontWeight: 500, color: 'var(--text-3)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>User</th>
                  <th style={{ padding: '14px 20px', fontWeight: 500, color: 'var(--text-3)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>System Role</th>
                  <th style={{ padding: '14px 20px', fontWeight: 500, color: 'var(--text-3)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Account Status</th>
                  <th style={{ padding: '14px 20px', fontWeight: 500, color: 'var(--text-3)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Joined Date</th>
                  <th style={{ padding: '14px 20px', fontWeight: 500, color: 'var(--text-3)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => {
                  const isSelf = u.id === currentUser?.id
                  const userRole = u.role || u.system_role || 'user'
                  return (
                    <tr
                      key={u.id}
                      style={{
                        borderBottom: '1px solid rgba(255,255,255,0.04)',
                        transition: 'background 0.15s ease',
                      }}
                    >
                      {/* User Info */}
                      <td style={{ padding: '14px 20px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div style={{
                            width: '34px',
                            height: '34px',
                            borderRadius: '50%',
                            background: userRole === 'admin' ? 'linear-gradient(135deg, #7c3aed, #db2777)' : 'rgba(255,255,255,0.08)',
                            color: '#fff',
                            display: 'grid',
                            placeItems: 'center',
                            fontWeight: 600,
                            fontSize: '11px',
                            letterSpacing: '0.05em',
                            flexShrink: 0,
                          }}>
                            {initials(u)}
                          </div>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <strong style={{ fontWeight: 500, color: '#f3eef8' }}>{u.full_name || '—'}</strong>
                              {isSelf && (
                                <span style={{
                                  fontSize: '10px',
                                  padding: '1px 6px',
                                  borderRadius: '999px',
                                  background: 'rgba(192,132,252,0.15)',
                                  color: '#c084fc',
                                  fontWeight: 500,
                                }}>
                                  You
                                </span>
                              )}
                            </div>
                            <small style={{ color: 'var(--text-3)', fontSize: '12px', display: 'block' }}>{u.email}</small>
                          </div>
                        </div>
                      </td>

                      {/* Role Badge */}
                      <td style={{ padding: '14px 20px' }}>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          padding: '3px 9px',
                          borderRadius: '6px',
                          fontSize: '11px',
                          fontWeight: 500,
                          letterSpacing: '0.04em',
                          textTransform: 'uppercase',
                          background: userRole === 'admin' ? 'rgba(147,51,234,0.18)' : 'rgba(255,255,255,0.06)',
                          color: userRole === 'admin' ? '#d8b4fe' : 'var(--text-2)',
                          border: userRole === 'admin' ? '1px solid rgba(192,132,252,0.3)' : '1px solid rgba(255,255,255,0.08)',
                        }}>
                          <Shield size={12} />
                          {userRole}
                        </span>
                      </td>

                      {/* Status Badge */}
                      <td style={{ padding: '14px 20px' }}>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          fontSize: '11px',
                          fontWeight: 500,
                          background: u.is_active ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)',
                          color: u.is_active ? '#4ade80' : '#f87171',
                          border: u.is_active ? '1px solid rgba(74,222,128,0.2)' : '1px solid rgba(248,113,113,0.2)',
                        }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: u.is_active ? '#4ade80' : '#f87171' }} />
                          {u.is_active ? 'Active' : 'Disabled'}
                        </span>
                      </td>

                      {/* Date */}
                      <td style={{ padding: '14px 20px', color: 'var(--text-3)', fontSize: '12px' }}>
                        {formatDate(u.created_at)}
                      </td>

                      {/* Action Buttons */}
                      <td style={{ padding: '14px 20px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '8px' }}>
                          {/* Role Toggle Button */}
                          {userRole === 'admin' ? (
                            <button
                              type="button"
                              className="secondary-button"
                              style={{ fontSize: '11px', padding: '4px 10px' }}
                              disabled={isSelf}
                              title={isSelf ? 'Cannot demote your own account' : 'Demote to regular user'}
                              onClick={() => openRoleConfirm(u, 'user')}
                            >
                              Demote to User
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="secondary-button"
                              style={{ fontSize: '11px', padding: '4px 10px', borderColor: 'rgba(192,132,252,0.35)', color: '#d8b4fe' }}
                              onClick={() => openRoleConfirm(u, 'admin')}
                            >
                              Promote to Admin
                            </button>
                          )}

                          {/* Status Toggle Button */}
                          {u.is_active ? (
                            <button
                              type="button"
                              className="secondary-button"
                              style={{ fontSize: '11px', padding: '4px 8px', color: '#f87171' }}
                              disabled={isSelf}
                              title={isSelf ? 'Cannot disable your own account' : 'Disable account'}
                              onClick={() => openStatusConfirm(u, false)}
                            >
                              <UserX size={14} />
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="secondary-button"
                              style={{ fontSize: '11px', padding: '4px 8px', color: '#4ade80' }}
                              title="Enable account"
                              onClick={() => openStatusConfirm(u, true)}
                            >
                              <UserCheck size={14} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Confirmation Modal */}
      {dialog.open && (
        <div className="mobile-scrim" style={{ display: 'grid', placeItems: 'center', zIndex: 100 }}>
          <div
            className="user-menu"
            style={{
              maxWidth: '460px',
              width: '90%',
              padding: '24px',
              position: 'relative',
            }}
            role="dialog"
            aria-modal="true"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                background: dialog.targetValue === 'admin' ? 'rgba(192,132,252,0.15)' : 'rgba(239,68,68,0.12)',
                display: 'grid',
                placeItems: 'center',
                color: dialog.targetValue === 'admin' ? '#c084fc' : '#f87171',
              }}>
                {dialog.type === 'role' ? <ShieldAlert size={20} /> : <AlertTriangle size={20} />}
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '16px', color: '#f3eef8' }}>
                  {dialog.type === 'role'
                    ? dialog.targetValue === 'admin'
                      ? 'Promote User to Admin'
                      : 'Demote Admin to User'
                    : dialog.targetValue
                      ? 'Activate User Account'
                      : 'Disable User Account'}
                </h3>
                <small style={{ color: 'var(--text-3)' }}>Confirmation required</small>
              </div>
            </div>

            <p style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--text-2)', marginBottom: '20px' }}>
              {dialog.type === 'role' ? (
                dialog.targetValue === 'admin' ? (
                  <>
                    Are you sure you want to promote <strong>{dialog.user?.email}</strong> to <strong>ADMIN</strong>?
                    They will receive full administrative control over all projects, test suites, verification runs, and access management.
                  </>
                ) : (
                  <>
                    Are you sure you want to demote <strong>{dialog.user?.email}</strong> to <strong>USER</strong>?
                    They will lose access to system management and the Admin Control Center.
                  </>
                )
              ) : dialog.targetValue ? (
                <>
                  Reactivate account for <strong>{dialog.user?.email}</strong>? They will be able to log in and use VeriGate again.
                </>
              ) : (
                <>
                  Disable account for <strong>{dialog.user?.email}</strong>? They will be immediately blocked from logging in.
                </>
              )}
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="secondary-button"
                onClick={closeDialog}
                disabled={actionPending}
              >
                Cancel
              </button>
              <button
                type="button"
                className="primary-button"
                onClick={confirmAction}
                disabled={actionPending}
                style={{
                  background: dialog.targetValue === 'admin' || dialog.targetValue === true ? 'linear-gradient(135deg, #7c3aed, #db2777)' : '#dc2626',
                }}
              >
                {actionPending ? (
                  <>
                    <LoaderCircle className="spinner" size={14} />
                    Processing...
                  </>
                ) : (
                  'Confirm Change'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
