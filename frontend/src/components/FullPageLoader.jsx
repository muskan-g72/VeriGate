import { GateMark } from './Brand'
export function FullPageLoader({ label }) { return <main className="launch-screen"><GateMark size={38} /><p>{label}<span aria-hidden="true">…</span></p></main> }
