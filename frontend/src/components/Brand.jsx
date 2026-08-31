export function GateMark({ size = 32, title = 'VeriGate' }) {
  return <svg className="gate-mark" width={size} height={size} viewBox="0 0 32 32" role="img" aria-label={title}>
    <path className="gate-mark__left" d="M4 4.5 13 7.4v4.1L8.3 10v12l4.7-1.5v4.1L4 27.5Z" />
    <path className="gate-mark__right" d="m28 4.5-9 2.9v4.1l4.7-1.5v12L19 20.5v4.1l9 2.9Z" />
    <rect className="gate-mark__node gate-mark__node--cyan" x="11.2" y="13.1" width="4.1" height="4.1" />
    <rect className="gate-mark__node gate-mark__node--cyan" x="15.9" y="17.8" width="4.1" height="4.1" />
    <rect className="gate-mark__node gate-mark__node--blue" x="16.1" y="13.1" width="4.1" height="4.1" />
    <rect className="gate-mark__node gate-mark__node--proof" x="22.1" y="13.1" width="4.1" height="4.1" />
  </svg>
}

export function Brand({ compact = false }) {
  return <div className="brand"><GateMark />{!compact && <span className="wordmark"><span>Veri</span><span>Gate</span></span>}</div>
}
