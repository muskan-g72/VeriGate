import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { useAuth } from './auth/useAuth'
import { AppShell } from './components/AppShell'
import { FullPageLoader } from './components/FullPageLoader'
import { LoginPage } from './pages/LoginPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OverviewPage } from './pages/OverviewPage'
import { RegisterPage } from './pages/RegisterPage'

function ProtectedRoute({ children }) {
  const { status } = useAuth()
  if (status === 'restoring') return <FullPageLoader label="Restoring your workspace" />
  if (status !== 'authenticated') return <Navigate to="/login" replace />
  return children
}

function GuestRoute({ children }) {
  const { status } = useAuth()
  if (status === 'restoring') return <FullPageLoader label="Checking your session" />
  if (status === 'authenticated') return <Navigate to="/app" replace />
  return children
}

export default function App() {
  return <AuthProvider><Routes>
    <Route path="/" element={<Navigate to="/app" replace />} />
    <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
    <Route path="/register" element={<GuestRoute><RegisterPage /></GuestRoute>} />
    <Route path="/app" element={<ProtectedRoute><AppShell /></ProtectedRoute>}><Route index element={<OverviewPage />} /></Route>
    <Route path="*" element={<NotFoundPage />} />
  </Routes></AuthProvider>
}
