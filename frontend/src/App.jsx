import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { useAuth } from './auth/useAuth'
import { AppShell } from './components/AppShell'
import { FullPageLoader } from './components/FullPageLoader'
import { LoginPage } from './pages/LoginPage'
import { LandingPage } from './pages/LandingPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OverviewPage } from './pages/OverviewPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { RegisterPage } from './pages/RegisterPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { TestLibraryPage } from './pages/TestLibraryPage'
import { TestCasesPage } from './pages/TestCasesPage'
import { TestSuitesPage } from './pages/TestSuitesPage'

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
    <Route path="/" element={<LandingPage />} />
    <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
    <Route path="/register" element={<GuestRoute><RegisterPage /></GuestRoute>} />
    <Route path="/forgot-password" element={<GuestRoute><ForgotPasswordPage /></GuestRoute>} />
    <Route path="/reset-password" element={<GuestRoute><ResetPasswordPage /></GuestRoute>} />
    <Route path="/app" element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
      <Route index element={<OverviewPage />} />
      <Route path="projects" element={<ProjectsPage />} />
      <Route path="test-library" element={<TestLibraryPage />} />
      <Route path="test-suites" element={<TestSuitesPage />} />
      <Route path="test-cases" element={<TestCasesPage />} />
    </Route>
    <Route path="*" element={<NotFoundPage />} />
  </Routes></AuthProvider>
}
