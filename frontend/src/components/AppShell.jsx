import { Bell, BookOpen, Boxes, BrainCircuit, Bug, ChevronDown, ChevronsLeft, FlaskConical, Gauge, KeyRound, Layers3, Menu, MonitorCog, Play, Search, Server, Settings, TestTube2, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { Brand } from './Brand'
import { CommandPalette } from './CommandPalette'

const groups = [
  ['Command', [[Gauge, 'Overview', '/app'], [Boxes, 'Projects', '/app/projects'], [Play, 'Runs']]],
  ['Testing', [[BookOpen, 'Test Library', '/app/test-library'], [Layers3, 'Test Suites', '/app/test-suites'], [TestTube2, 'Test Cases', '/app/test-cases']]],
  ['Quality', [[Bug, 'Issues'], [FlaskConical, 'Evidence']]],
  ['Infrastructure', [[Server, 'Environments'], [MonitorCog, 'Applications']]],
  ['Intelligence', [[Gauge, 'Insights'], [BrainCircuit, 'AI Lab']]],
  ['Management', [[Settings, 'Settings'], [KeyRound, 'Access']]],
]
const initials = (user) => (user?.full_name || user?.email || 'VG').split(/[\s@.]+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()

export function AppShell() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const pageTitles = { '/app/projects': 'Projects', '/app/test-library': 'Test Library', '/app/test-suites': 'Test Suites', '/app/test-cases': 'Test Cases' }
  const pageTitle = pageTitles[location.pathname] || 'Overview'
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [userOpen, setUserOpen] = useState(false)
  const userMenuRef = useRef(null)
  const closePalette = useCallback(() => setPaletteOpen(false), [setPaletteOpen])
  useEffect(() => { const shortcut = (event) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setPaletteOpen((value) => !value) } }; document.addEventListener('keydown', shortcut); return () => document.removeEventListener('keydown', shortcut) }, [])
  useEffect(() => { const outside = (event) => { if (!userMenuRef.current?.contains(event.target)) setUserOpen(false) }; document.addEventListener('pointerdown', outside); return () => document.removeEventListener('pointerdown', outside) }, [])
  return <div className={`app-shell ${collapsed ? 'is-collapsed' : ''}`}>
    {mobileOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside className={`sidebar ${mobileOpen ? 'is-open' : ''}`}><div className="sidebar-brand"><Brand compact={collapsed} /><button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X /></button></div><nav aria-label="Primary navigation">{groups.map(([label, items]) => <div className="nav-group" key={label}><p>{label}</p>{items.map(([Icon, name, path]) => path ? <NavLink end={path === '/app'} to={path} className={({ isActive }) => `nav-item ${isActive ? 'is-active' : ''}`} key={name} onClick={() => setMobileOpen(false)}><Icon /><span>{name}</span></NavLink> : <button className="nav-item" key={name} disabled title={`${name} — Coming soon`}><Icon /><span>{name}</span><small>SOON</small></button>)}</div>)}</nav><button className="collapse-button" onClick={() => setCollapsed((value) => !value)}><ChevronsLeft /><span>{collapsed ? 'Expand' : 'Collapse sidebar'}</span></button></aside>
    <div className="app-main"><header className="topbar"><div className="topbar-title"><button className="mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu /></button><div><p>COMMAND / {pageTitle.toUpperCase()}</p><h1>{pageTitle}</h1></div></div><div className="topbar-actions"><button className="search-button" onClick={() => setPaletteOpen(true)}><Search /><span>Search commands</span><kbd>Ctrl K</kbd></button><button className="icon-button" aria-label="Notifications — no new notifications"><Bell /><i /></button><div className="user-control" ref={userMenuRef}><button className="avatar-button" onClick={() => setUserOpen((value) => !value)} aria-expanded={userOpen}><span>{initials(user)}</span><div><strong>{user?.full_name || 'VeriGate user'}</strong><small>{user?.email}</small></div><ChevronDown /></button>{userOpen && <div className="user-menu"><p>Signed in as<br /><strong>{user?.email}</strong></p><button onClick={() => logout()}>Log out</button></div>}</div></div></header><Outlet /></div>
    <CommandPalette open={paletteOpen} onClose={closePalette} />
  </div>
}
