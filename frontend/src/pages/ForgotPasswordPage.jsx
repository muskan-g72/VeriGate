import { ArrowLeft, ArrowRight, LoaderCircle, MailCheck } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../api/client'
import { AuthLayout } from '../components/AuthLayout'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState(''), [error, setError] = useState(''), [pending, setPending] = useState(false), [sent, setSent] = useState(false)
  async function submit(event) {
    event.preventDefault()
    if (!/^\S+@\S+\.\S+$/.test(email)) { setError('Enter a valid email address.'); return }
    setError(''); setPending(true)
    try { await authApi.forgotPassword(email.trim()); setSent(true) } catch (requestError) { setError(requestError.message) } finally { setPending(false) }
  }
  return <AuthLayout eyebrow="Account recovery" title="Reset your password" description="Enter your account email and we’ll send you a secure reset link." footer={<Link to="/login"><ArrowLeft /> Back to sign in</Link>}>
    {sent ? <div className="recovery-success" role="status"><MailCheck /><h3>Check your inbox</h3><p>If an account exists for <strong>{email}</strong>, a reset link is on its way. It expires in 20 minutes.</p></div> : <form className="auth-form" onSubmit={submit} noValidate>{error && <div className="form-alert" role="alert"><strong>Unable to continue</strong><span>{error}</span></div>}<div className="field"><label htmlFor="recovery-email">Email</label><input id="recovery-email" type="email" autoComplete="email" value={email} disabled={pending} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" autoFocus /></div><button className="primary-button" disabled={pending}>{pending ? <><LoaderCircle className="spinner" />Sending link...</> : <>Send reset link <ArrowRight /></>}</button></form>}
  </AuthLayout>
}
