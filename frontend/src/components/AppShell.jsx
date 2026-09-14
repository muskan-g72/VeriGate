import {
  Bell,
  BookOpen,
  Boxes,
  ChevronDown,
  ChevronsLeft,
  FlaskConical,
  Gauge,
  GitPullRequest,
  KeyRound,
  Menu,
  Play,
  Search,
  Settings,
  Shield,
  Users,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { auditLogsApi } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { Brand } from './Brand'
import { CommandPalette } from './CommandPalette'

const adminNavGroups = [
  [
    'Control Center',
    [
      [Gauge, 'Dashboard', '/admin/dashboard'],
      [Users, 'Users', '/admin/users'],
      [Boxes, 'Projects', '/admin/projects'],
      [Play, 'Verification Runs', '/admin/verification-runs'],
      [GitPullRequest, 'GitHub / PR Integration', '/admin/github'],
    ],
  ],
  [
    'Quality & Audit',
    [
      [FlaskConical, 'Evidence', '/admin/evidence'],
      [BookOpen, 'Reports', '/admin/reports'],
      [Shield, 'Audit Logs', '/admin/audit-logs'],
    ],
  ],
  [
    'Administration',
    [
      [Settings, 'Settings', '/admin/settings'],
    ],
  ],
]

const userNavGroups = [
  [
    'Workspace',
    [
      [Gauge, 'Dashboard', '/dashboard'],
      [Boxes, 'My Projects', '/app/projects'],
      [Play, 'Verification', '/app/runs'],
      [GitPullRequest, 'GitHub / PRs', '/app/github-prs'],
    ],
  ],
  [
    'Quality',
    [
      [FlaskConical, 'Evidence', '/app/evidence'],
      [BookOpen, 'Reports', '/app/insights'],
    ],
  ],
  [
    'Account',
    [
      [KeyRound, 'Profile / Settings', '/app/access'],
    ],
  ],
]

const initials = (user) =>
  (user?.full_name || user?.email || 'VG')
    .split(/[\s@.]+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()

export function AppShell() {
  const { user, isAdmin, logout } = useAuth()
  const location = useLocation()

  const isAdminMode = isAdmin && location.pathname.startsWith('/admin')
  const navGroups = isAdminMode ? adminNavGroups : userNavGroups

  const pageTitles = {
    '/dashboard': 'Dashboard',
    '/admin/dashboard': 'Admin Dashboard',
    '/admin/users': 'Users Management',
    '/admin/projects': 'System Projects',
    '/admin/verification-runs': 'Verification Runs',
    '/admin/github': 'GitHub & PR Integration',
    '/admin/evidence': 'Evidence Records',
    '/admin/reports': 'System Reports',
    '/admin/audit-logs': 'Audit Logs',
    '/admin/settings': 'System Settings',
    '/app': 'Command Center',
    '/app/runs': 'Runs',
    '/app/projects': 'Projects',
    '/app/test-library': 'Test Library',
    '/app/test-suites': 'Test Suites',
    '/app/test-cases': 'Test Cases',
    '/app/playwright-tests': 'Playwright Tests',
    '/app/github-prs': 'PR Verifications',
    '/app/evidence': 'Evidence',
    '/app/insights': 'Insights',
    '/app/access': 'Access',
  }

  const pageTitle =
    pageTitles[location.pathname] ||
    (location.pathname.startsWith('/app/issues')
      ? 'Issues'
      : location.pathname.startsWith('/app/verification-runs/')
        ? 'Verification Run'
        : location.pathname.startsWith('/app/projects/')
          ? 'Project Summary'
          : isAdminMode
            ? 'Control Center'
            : 'Workspace')

  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [userOpen, setUserOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [notificationsStatus, setNotificationsStatus] = useState('idle')

  const userMenuRef = useRef(null)
  const notificationsRef = useRef(null)
  const closePalette = useCallback(() => setPaletteOpen(false), [setPaletteOpen])

  useEffect(() => {
    const shortcut = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPaletteOpen((value) => !value)
      }
    }
    document.addEventListener('keydown', shortcut)
    return () => document.removeEventListener('keydown', shortcut)
  }, [])

  useEffect(() => {
    const outside = (event) => {
      if (!userMenuRef.current?.contains(event.target)) setUserOpen(false)
      if (!notificationsRef.current?.contains(event.target)) setNotificationsOpen(false)
    }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [])

  async function loadNotifications() {
    setNotificationsStatus('loading')
    try {
      const data = await auditLogsApi.list()
      setNotifications(data || [])
      setNotificationsStatus('ready')
    } catch {
      setNotificationsStatus('error')
    }
  }

  function toggleNotifications() {
    const next = !notificationsOpen
    setNotificationsOpen(next)
    if (next) loadNotifications()
  }

  return (
    <div className={`app-shell ${collapsed ? 'is-collapsed' : ''}`}>
      {mobileOpen && (
        <button
          className="mobile-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`sidebar ${mobileOpen ? 'is-open' : ''}`}>
        <div className="sidebar-brand">
          <Brand compact={collapsed} />
          <button
            className="mobile-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <X />
          </button>
        </div>

        {/* Role Mode Badge */}
        {!collapsed && (
          <div style={{
            margin: '0 8px 16px',
            padding: '6px 10px',
            borderRadius: '6px',
            background: isAdminMode ? 'rgba(147,51,234,0.12)' : 'rgba(255,255,255,0.04)',
            border: isAdminMode ? '1px solid rgba(192,132,252,0.25)' : '1px solid rgba(255,255,255,0.06)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <span style={{
              fontSize: '10px',
              fontFamily: 'var(--mono)',
              letterSpacing: '0.08em',
              fontWeight: 600,
              color: isAdminMode ? '#c084fc' : 'var(--text-3)',
              textTransform: 'uppercase',
            }}>
              {isAdminMode ? '🛡️ Admin Center' : '💼 User Workspace'}
            </span>
            {isAdmin && (
              <Link
                to={isAdminMode ? '/dashboard' : '/admin/dashboard'}
                style={{
                  fontSize: '10px',
                  color: 'var(--cyan)',
                  textDecoration: 'none',
                  fontWeight: 500,
                }}
                title={isAdminMode ? 'Switch to User View' : 'Switch to Admin View'}
              >
                {isAdminMode ? 'User View' : 'Admin View'}
              </Link>
            )}
          </div>
        )}

        <nav aria-label="Primary navigation">
          {navGroups.map(([label, items]) => (
            <div className="nav-group" key={label}>
              <p>{label}</p>
              {items.map(([Icon, name, path]) =>
                path ? (
                  <NavLink
                    end={path === '/app' || path === '/dashboard' || path === '/admin/dashboard'}
                    to={path}
                    className={({ isActive }) => `nav-item ${isActive ? 'is-active' : ''}`}
                    key={name}
                    onClick={() => setMobileOpen(false)}
                  >
                    <Icon />
                    <span>{name}</span>
                  </NavLink>
                ) : (
                  <button
                    className="nav-item"
                    key={name}
                    disabled
                    title={`${name} — Coming soon`}
                  >
                    <Icon />
                    <span>{name}</span>
                    <small>SOON</small>
                  </button>
                ),
              )}
            </div>
          ))}
        </nav>

        <button
          className="collapse-button"
          onClick={() => setCollapsed((value) => !value)}
        >
          <ChevronsLeft />
          <span>{collapsed ? 'Expand' : 'Collapse sidebar'}</span>
        </button>
      </aside>

      {/* Main Content Area */}
      <div className="app-main">
        <header className="topbar">
          <div className="topbar-title">
            <button
              className="mobile-menu"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
            >
              <Menu />
            </button>
            <div>
              <p>
                {isAdminMode ? 'ADMIN CONTROL' : 'WORKSPACE'} / {pageTitle.toUpperCase()}
              </p>
              <h1>{pageTitle}</h1>
            </div>
          </div>

          <div className="topbar-actions">
            <button
              className="search-button"
              onClick={() => setPaletteOpen(true)}
            >
              <Search />
              <span>Search commands</span>
              <kbd>Ctrl K</kbd>
            </button>

            {/* Notifications Menu */}
            <div className="notifications-control" ref={notificationsRef}>
              <button
                className="icon-button"
                onClick={toggleNotifications}
                aria-label="Recent workspace activity"
                aria-expanded={notificationsOpen}
              >
                <Bell />
                {notifications.length > 0 && <i />}
              </button>
              {notificationsOpen && (
                <section
                  className="notifications-menu"
                  aria-label="Recent workspace activity"
                >
                  <header>
                    <strong>Recent activity</strong>
                    <button onClick={loadNotifications}>Refresh</button>
                  </header>
                  {notificationsStatus === 'loading' && <p>Loading activity...</p>}
                  {notificationsStatus === 'error' && (
                    <p>Activity is unavailable right now.</p>
                  )}
                  {notificationsStatus === 'ready' &&
                    (notifications.length ? (
                      <ul>
                        {notifications.slice(0, 8).map((item) => (
                          <li key={item.id}>
                            <strong>
                              {item.description ||
                                `${item.action} ${item.resource_type}`}
                            </strong>
                            <span>
                              {new Intl.DateTimeFormat(undefined, {
                                dateStyle: 'medium',
                                timeStyle: 'short',
                              }).format(new Date(item.created_at))}
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No workspace activity yet.</p>
                    ))}
                </section>
              )}
            </div>

            {/* User Dropdown */}
            <div className="user-control" ref={userMenuRef}>
              <button
                className="avatar-button"
                onClick={() => setUserOpen((value) => !value)}
                aria-expanded={userOpen}
              >
                <span>{initials(user)}</span>
                <div>
                  <strong>{user?.full_name || 'VeriGate User'}</strong>
                  <small>{user?.email}</small>
                </div>
                <ChevronDown />
              </button>

              {userOpen && (
                <div className="user-menu" style={{ minWidth: '220px' }}>
                  <div style={{ paddingBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.08)', marginBottom: '8px' }}>
                    <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-3)' }}>Signed in as</p>
                    <strong style={{ fontSize: '13px', color: '#fff', wordBreak: 'break-all' }}>{user?.email}</strong>
                    <div style={{ marginTop: '6px' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 7px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: 600,
                        fontFamily: 'var(--mono)',
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                        background: (user?.role || user?.system_role) === 'admin' ? 'rgba(192,132,252,0.15)' : 'rgba(255,255,255,0.06)',
                        color: (user?.role || user?.system_role) === 'admin' ? '#d8b4fe' : 'var(--text-2)',
                        border: (user?.role || user?.system_role) === 'admin' ? '1px solid rgba(192,132,252,0.3)' : '1px solid rgba(255,255,255,0.08)',
                      }}>
                        ROLE: {(user?.role || user?.system_role || 'USER').toUpperCase()}
                      </span>
                    </div>
                  </div>

                  {isAdmin && (
                    <div style={{ paddingBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.08)', marginBottom: '8px' }}>
                      <Link
                        to={isAdminMode ? '/dashboard' : '/admin/dashboard'}
                        onClick={() => setUserOpen(false)}
                        style={{
                          display: 'block',
                          padding: '6px 8px',
                          borderRadius: '6px',
                          color: '#c084fc',
                          textDecoration: 'none',
                          fontSize: '12px',
                        }}
                      >
                        {isAdminMode ? '← Switch to User Dashboard' : '→ Switch to Admin Center'}
                      </Link>
                    </div>
                  )}

                  <button
                    onClick={() => {
                      setUserOpen(false)
                      logout()
                    }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '6px 8px',
                      borderRadius: '6px',
                      background: 'transparent',
                      border: 0,
                      color: '#f87171',
                      cursor: 'pointer',
                      fontSize: '12px',
                    }}
                  >
                    Log out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <Outlet />
      </div>

      <CommandPalette open={paletteOpen} onClose={closePalette} />
    </div>
  )
}
