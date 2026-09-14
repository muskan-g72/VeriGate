import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { useAuth } from './auth/useAuth'
import { AppShell } from './components/AppShell'
import { FullPageLoader } from './components/FullPageLoader'
import { AccessPage } from './pages/AccessPage'
import { AdminAuditLogsPage } from './pages/admin/AdminAuditLogsPage'
import { AdminDashboardPage } from './pages/admin/AdminDashboardPage'
import { AdminUsersPage } from './pages/admin/AdminUsersPage'
import { EvidencePage } from './pages/EvidencePage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { GitHubPrsPage } from './pages/GitHubPrsPage'
import { InsightsPage } from './pages/InsightsPage'
import { IssueDetailPage } from './pages/IssueDetailPage'
import { IssuesPage } from './pages/IssuesPage'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OverviewPage } from './pages/OverviewPage'
import { PlaywrightTestsPage } from './pages/PlaywrightTestsPage'
import { ProjectSummaryPage } from './pages/ProjectSummaryPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { RegisterPage } from './pages/RegisterPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { RunsPage } from './pages/RunsPage'
import { TestCasesPage } from './pages/TestCasesPage'
import { TestLibraryPage } from './pages/TestLibraryPage'
import { TestSuitesPage } from './pages/TestSuitesPage'
import { UnauthorizedPage } from './pages/UnauthorizedPage'
import { UserDashboardPage } from './pages/UserDashboardPage'
import { VerificationRunPage } from './pages/VerificationRunPage'

function ProtectedRoute({ children, requireAdmin = false }) {
  const { status, isAdmin } = useAuth()
  if (status === 'restoring') return <FullPageLoader label="Restoring your workspace" />
  if (status !== 'authenticated') return <Navigate to="/login" replace />
  if (requireAdmin && !isAdmin) return <Navigate to="/unauthorized" replace />
  return children
}

function GuestRoute({ children }) {
  const { status, isAdmin } = useAuth()
  if (status === 'restoring') return <FullPageLoader label="Checking your session" />
  if (status === 'authenticated') {
    return <Navigate to={isAdmin ? '/admin/dashboard' : '/dashboard'} replace />
  }
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public & Guest Routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
        <Route path="/register" element={<GuestRoute><RegisterPage /></GuestRoute>} />
        <Route path="/forgot-password" element={<GuestRoute><ForgotPasswordPage /></GuestRoute>} />
        <Route path="/reset-password" element={<GuestRoute><ResetPasswordPage /></GuestRoute>} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />

        {/* User Dashboard Route */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<UserDashboardPage />} />
        </Route>

        {/* Dedicated Admin Routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requireAdmin={true}>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="dashboard" element={<AdminDashboardPage />} />
          <Route path="users" element={<AdminUsersPage />} />
          <Route path="audit-logs" element={<AdminAuditLogsPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="verification-runs" element={<RunsPage />} />
          <Route path="github" element={<GitHubPrsPage />} />
          <Route path="evidence" element={<EvidencePage />} />
          <Route path="reports" element={<InsightsPage />} />
          <Route path="settings" element={<AccessPage />} />
        </Route>

        {/* Existing Application Workspace Routes (Preserved & Protected) */}
        <Route
          path="/app"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<OverviewPage />} />
          <Route path="runs" element={<RunsPage />} />
          <Route path="issues" element={<IssuesPage />} />
          <Route path="issues/:issueId" element={<IssueDetailPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="projects/:projectId" element={<ProjectSummaryPage />} />
          <Route path="verification-runs/:runId" element={<VerificationRunPage />} />
          <Route path="test-library" element={<TestLibraryPage />} />
          <Route path="test-suites" element={<TestSuitesPage />} />
          <Route path="test-cases" element={<TestCasesPage />} />
          <Route path="playwright-tests" element={<PlaywrightTestsPage />} />
          <Route path="github-prs" element={<GitHubPrsPage />} />
          <Route path="evidence" element={<EvidencePage />} />
          <Route path="insights" element={<InsightsPage />} />
          <Route path="access" element={<AccessPage />} />
        </Route>

        {/* Fallback 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AuthProvider>
  )
}
