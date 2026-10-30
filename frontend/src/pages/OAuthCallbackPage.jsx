import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { AuthLayout } from '../components/AuthLayout'

export function OAuthCallbackPage() {
  const [params] = useSearchParams(); const navigate = useNavigate(); const { completeOAuthLogin } = useAuth(); const [error, setError] = useState('')
  useEffect(() => { const code = params.get('code'); if (!code) { setError('OAuth sign-in did not return a valid code.'); return }; completeOAuthLogin(code).then((user) => navigate((user?.role || user?.system_role) === 'admin' ? '/admin/dashboard' : '/dashboard', { replace: true })).catch((err) => setError(err.message || 'OAuth sign-in could not be completed.')) }, [completeOAuthLogin, navigate, params])
  return <AuthLayout eyebrow="OAuth sign-in" title="Completing sign-in" description="Verifying your account with the selected provider.">{error ? <div className="form-alert" role="alert"><strong>Unable to sign in</strong><span>{error}</span></div> : <p>Signing you in…</p>}</AuthLayout>
}
