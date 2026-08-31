import { ArrowRight, LoaderCircle } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { AuthLayout } from '../components/AuthLayout'
import { PasswordField } from '../components/PasswordField'

export function RegisterPage() {
  const { login } = useAuth(); const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', password: '' }); const [errors, setErrors] = useState({}); const [pending, setPending] = useState(false); const [serverError, setServerError] = useState(''); const [created, setCreated] = useState(false)
  async function submit(event) {
    event.preventDefault(); const next = {}
    if (!form.full_name.trim()) next.full_name = 'Enter your name.'
    if (!/^\S+@\S+\.\S+$/.test(form.email)) next.email = 'Enter a valid email address.'
    if (form.password.length < 8) next.password = 'Use at least 8 characters.'
    else if (form.password.length > 128) next.password = 'Use no more than 128 characters.'
    setErrors(next); setServerError(''); if (Object.keys(next).length) return; setPending(true)
    try { await authApi.register({ full_name: form.full_name.trim(), email: form.email.trim(), password: form.password }); setCreated(true); await login(form.email.trim(), form.password); navigate('/app', { replace: true }) } catch (error) { if (error.status === 409) setErrors((current) => ({ ...current, email: 'An account with this email already exists.' })); else setServerError('Something went wrong while creating your workspace. Please try again.') } finally { setPending(false) }
  }
  return <AuthLayout eyebrow="Create your account" title={<>Create your <span className="heading-keep">VeriGate account</span></>} description="Start capturing verifiable test evidence in your workspace." footer={<>Already have an account? <Link to="/login">Sign in</Link></>}>
    {serverError && <div className="form-alert" role="alert"><strong>Unable to create account</strong><span>{serverError}</span></div>}
    {created && <div className="form-success" role="status">Workspace created <span aria-hidden="true">✓</span></div>}
    <form className="auth-form" onSubmit={submit} noValidate><div className="field"><label htmlFor="full-name">Full name</label><input id="full-name" autoComplete="name" disabled={pending} value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} aria-invalid={Boolean(errors.full_name)} placeholder="verigate123" autoFocus /><div className={`field-error ${errors.full_name ? 'is-visible' : ''}`} role="alert">{errors.full_name}</div></div><div className="field"><label htmlFor="email">Email</label><input id="email" type="email" autoComplete="email" disabled={pending} value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? 'register-email-error' : undefined} placeholder="you@example.com" /><div className={`field-error ${errors.email ? 'is-visible' : ''}`} id="register-email-error" role="alert">{errors.email}</div></div><PasswordField value={form.password} disabled={pending} maxLength={128} onChange={(event) => setForm({ ...form, password: event.target.value })} error={errors.password} showStrength autoComplete="new-password" placeholder="At least 8 characters" /><button className={`primary-button ${created ? 'is-success' : ''}`} disabled={pending || created}>{created ? <>Workspace created <span aria-hidden="true">✓</span></> : pending ? <><LoaderCircle className="spinner" />Creating workspace...</> : <>Create account<ArrowRight /></>}</button></form>
  </AuthLayout>
}
