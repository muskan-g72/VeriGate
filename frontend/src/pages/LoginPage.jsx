import { ArrowRight, LoaderCircle } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { AuthLayout } from '../components/AuthLayout'
import { PasswordField } from '../components/PasswordField'

export function LoginPage() {
  const { login, sessionNotice } = useAuth(); const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' }); const [errors, setErrors] = useState({}); const [pending, setPending] = useState(false); const [serverError, setServerError] = useState('')
  async function submit(event) {
    event.preventDefault(); const next = {}
    if (!/^\S+@\S+\.\S+$/.test(form.email)) next.email = 'Enter a valid email address.'
    if (!form.password) next.password = 'Enter your password.'
    setErrors(next); setServerError(''); if (Object.keys(next).length) return; setPending(true)
    try { await login(form.email.trim(), form.password); navigate('/app', { replace: true }) } catch (error) { setServerError(error.status === 401 ? 'Incorrect email or password.' : error.message) } finally { setPending(false) }
  }
  return <AuthLayout eyebrow="Secure access" title="Welcome back" description="Sign in to continue to your verification workspace." footer={<>New to VeriGate? <Link to="/register">Create an account</Link></>}>
    {(sessionNotice || serverError) && <div className="form-alert" role="alert"><strong>{sessionNotice ? 'Session ended' : 'Unable to sign in'}</strong><span>{serverError || sessionNotice}</span></div>}
    <form className="auth-form" onSubmit={submit} noValidate><div className="field"><label htmlFor="email">Email</label><input id="email" type="email" autoComplete="email" disabled={pending} value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? 'email-error' : undefined} placeholder="you@example.com" autoFocus /><div className={`field-error ${errors.email ? 'is-visible' : ''}`} id="email-error" role="alert">{errors.email}</div></div><PasswordField value={form.password} disabled={pending} onChange={(event) => setForm({ ...form, password: event.target.value })} error={errors.password} autoComplete="current-password" placeholder="Your password" /><button className="primary-button" disabled={pending}>{pending ? <><LoaderCircle className="spinner" />Signing in...</> : <>Sign in<ArrowRight /></>}</button></form>
  </AuthLayout>
}
