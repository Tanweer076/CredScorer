import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, homeFor, useAuth } from './auth'
import Layout from './components/Layout'
import RequireRole from './components/RequireRole'
import AdminDashboard from './pages/admin/AdminDashboard'
import AuditLog from './pages/admin/AuditLog'
import ApplicationDetail from './pages/applicant/ApplicationDetail'
import MyApplications from './pages/applicant/MyApplications'
import NewApplication from './pages/applicant/NewApplication'
import Login from './pages/Login'
import Signup from './pages/Signup'
import ReviewApplication from './pages/staff/ReviewApplication'
import ReviewQueue from './pages/staff/ReviewQueue'

function Home() {
  const { user, loading } = useAuth()
  if (loading) return null
  return <Navigate to={homeFor(user)} replace />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          <Route element={<RequireRole roles={['applicant']}><Layout /></RequireRole>}>
            <Route path="/applicant" element={<MyApplications />} />
            <Route path="/applicant/new" element={<NewApplication />} />
            <Route path="/applicant/applications/:id" element={<ApplicationDetail />} />
          </Route>

          <Route element={<RequireRole roles={['underwriter', 'admin']}><Layout /></RequireRole>}>
            <Route path="/underwriter" element={<ReviewQueue />} />
            <Route path="/underwriter/applications/:id" element={<ReviewApplication />} />
          </Route>

          <Route element={<RequireRole roles={['admin']}><Layout /></RequireRole>}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/audit" element={<AuditLog />} />
          </Route>

          <Route path="*" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}