import { Brand } from './Brand'
import { useLocation } from 'react-router-dom'

export function AuthLayout({ eyebrow, title, description, children, footer }) {
  const { pathname } = useLocation()
  return <main className="auth-layout" key={pathname}>
    <div className="auth-atmosphere" aria-hidden="true"><span /></div>
    <section className="auth-story">
      <div className="auth-reveal auth-reveal--logo"><Brand /></div>
      <div className="auth-story__content">
        <div className="auth-story__copy">
          <p className="eyebrow auth-reveal auth-reveal--hero-label">Test verification platform</p>
          <div className="auth-reveal auth-reveal--hero-copy"><h1>Run tests. Capture <em>evidence.</em><br />Prove the result.</h1><p>Turn test execution into traceable evidence, actionable issues and defensible verdicts.</p></div>
          <article className="verification-artifact" aria-label="Latest verification preview">
            <p>Latest verification</p>
            <div className="artifact-meta"><div><span>Endpoint</span><strong>API /login</strong></div><div><span>Run</span><strong>#1842</strong></div></div>
            <ul><li><span aria-hidden="true">✓</span> Request completed</li><li><span aria-hidden="true">✓</span> Response matched</li><li><span aria-hidden="true">✓</span> Evidence captured</li></ul>
            <div className="artifact-verdict"><span>Verdict</span><strong><i aria-hidden="true" /> Pass</strong></div>
          </article>
        </div>
      </div>
      <div className="auth-path auth-reveal auth-reveal--workflow" aria-label="Verification workflow: Test, Execute, Capture, Verify"><span>Test</span><i /><span>Execute</span><i /><span>Capture</span><i /><span>Verify</span></div>
    </section>
    <section className="auth-panel"><div className="auth-card"><div className="mobile-brand auth-reveal auth-reveal--logo"><Brand /></div><div className="auth-reveal auth-reveal--form-heading"><p className="eyebrow">{eyebrow}</p><h2>{title}</h2><p className="auth-description">{description}</p></div><div className="auth-reveal auth-reveal--form-body">{children}<p className="auth-footer">{footer}</p></div></div></section>
  </main>
}
