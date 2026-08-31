import { Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'

function getStrength(password) {
  if (!password) return { label: '', score: 0, hint: 'Use at least 8 characters.' }
  let score = password.length >= 8 ? 1 : 0
  if (password.length >= 12) score += 1
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1
  if (/\d/.test(password) && /[^\w\s]/.test(password)) score += 1
  const labels = ['Weak', 'Weak', 'Fair', 'Good', 'Strong']
  return { label: labels[score], score, hint: password.length < 8 ? `${8 - password.length} more character${8 - password.length === 1 ? '' : 's'} required.` : 'Meets the VeriGate password requirement.' }
}

export function PasswordField({ id = 'password', label = 'Password', error, showStrength = false, disabled = false, value = '', ...props }) {
  const [visible, setVisible] = useState(false)
  const strength = getStrength(value)
  const describedBy = [error && `${id}-error`, showStrength && `${id}-strength`].filter(Boolean).join(' ') || undefined
  return <div className="field"><label htmlFor={id}>{label}</label><div className="input-wrap"><input id={id} type={visible ? 'text' : 'password'} value={value} disabled={disabled} aria-invalid={Boolean(error)} aria-describedby={describedBy} {...props} /><button className="input-action" type="button" disabled={disabled} onClick={() => setVisible((current) => !current)} aria-label={visible ? 'Hide password' : 'Show password'}>{visible ? <EyeOff /> : <Eye />}</button></div><div className={`field-error ${error ? 'is-visible' : ''}`} id={`${id}-error`} role="alert">{error}</div>{showStrength && <div className="password-strength" id={`${id}-strength`} aria-live="polite"><div className="strength-heading"><span>Password strength</span><strong>{strength.label}</strong></div><div className="strength-meter" data-score={strength.score} aria-hidden="true"><i /><i /><i /><i /></div><small>{strength.hint}</small></div>}</div>
}
