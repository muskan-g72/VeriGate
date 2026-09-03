import { ArrowRight, LoaderCircle } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { authApi } from '../api/client'
import { AuthLayout } from '../components/AuthLayout'
import { PasswordField } from '../components/PasswordField'

export function ResetPasswordPage() {
  const [params] = useSearchParams(), navigate = useNavigate(), token = params.get('token') || ''
  const [password, setPassword] = useState(''), [confirm, setConfirm] = useState(''), [error, setError] = useState(''), [pending, setPending] = useState(false)
  async function submit(event) {
    event.preventDefault()
    if (!token) { setError('This reset link is missing its security token.'); return }
    if (password.length < 8) { setError('Use at least 8 characters.'); return }
    if (password !== confirm) { setError('The passwords do not match.'); return }
    setError(''); setPending(true)
    try { await authApi.resetPassword(token, password); navigate('/login', { replace: true }) } catch (requestError) { setError(requestError.message) } finally { setPending(false) }
  }
  return <AuthLayout eyebrow="Secure reset" title="Choose a new password" description="Create a strong password you haven’t used for this account before." footer={<>Remembered it? <Link to="/login">Return to sign in</Link></>}>
    {error && <div className="form-alert" role="alert"><strong>Unable to reset password</strong><span>{error}</span></div>}
    <form className="auth-form" onSubmit={submit} noValidate><PasswordField value={password} disabled={pending} onChange={(event) => setPassword(event.target.value)} showStrength autoComplete="new-password" placeholder="At least 8 characters" /><PasswordField id="confirm-password" label="Confirm password" value={confirm} disabled={pending} onChange={(event) => setConfirm(event.target.value)} autoComplete="new-password" placeholder="Enter it again" /><button className="primary-button" disabled={pending || !token}>{pending ? <><LoaderCircle className="spinner" />Updating password...</> : <>Update password <ArrowRight /></>}</button></form>
  </AuthLayout>
}
