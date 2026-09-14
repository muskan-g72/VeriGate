import { ArrowLeft, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { useAuth } from '../auth/useAuth'

export function UnauthorizedPage() {
  const { user } = useAuth()
  const role = user?.role || user?.system_role || 'user'
  const fallbackPath = role === 'admin' ? '/admin/dashboard' : '/dashboard'

  return (
    <main className="not-found">
      <Brand />
      <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid rgba(239, 68, 68, 0.28)',
          display: 'grid',
          placeItems: 'center',
          color: '#f87171',
          marginBottom: '16px'
        }}>
          <ShieldAlert size={28} />
        </div>
        <p className="eyebrow" style={{ color: '#f87171' }}>403 / Access Forbidden</p>
        <h1>Admin Clearance Required</h1>
        <p style={{ maxWidth: '440px', lineHeight: '1.6', marginTop: '8px' }}>
          Your current account role (<strong>{role.toUpperCase()}</strong>) does not have permission to access this administrative control surface.
        </p>
        <Link to={fallbackPath} style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 20px',
          borderRadius: '8px',
          background: 'rgba(139, 92, 246, 0.15)',
          border: '1px solid rgba(192, 132, 252, 0.3)',
          color: '#f3e8ff',
          textDecoration: 'none',
          marginTop: '24px',
          fontWeight: 500,
          fontSize: '14px'
        }}>
          <ArrowLeft size={16} />
          Return to {role === 'admin' ? 'Admin Dashboard' : 'User Dashboard'}
        </Link>
      </div>
    </main>
  )
}
