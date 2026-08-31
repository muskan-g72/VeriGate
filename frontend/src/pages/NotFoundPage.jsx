import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/Brand'
export function NotFoundPage() { return <main className="not-found"><Brand /><p className="eyebrow">404 / Route not found</p><h1>This path is outside the gate.</h1><p>The page may have moved, or it may not exist yet.</p><Link to="/app"><ArrowLeft />Return to overview</Link></main> }
