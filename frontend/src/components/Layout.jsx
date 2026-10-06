import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { homeFor, useAuth } from '../auth'

const LINKS = {
  applicant: [
    { to: '/applicant', label: 'My applications' },
    { to: '/applicant/new', label: 'New application' },
  ],
  underwriter: [{ to: '/underwriter', label: 'Review queue' }],
  admin: [
    { to: '/admin', label: 'Dashboard' },
    { to: '/underwriter', label: 'Review queue' },
  ],
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <Link to={homeFor(user)} className="text-lg font-bold text-indigo-700">CredScorer</Link>
            <nav className="flex gap-4 text-sm">
              {(LINKS[user.role] || []).map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end
                  className={({ isActive }) => (isActive ? 'font-semibold text-indigo-700' : 'text-slate-600 hover:text-slate-900')}
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <span>{user.full_name} <span className="text-slate-400">({user.role})</span></span>
            <button onClick={handleLogout} className="text-indigo-700 hover:underline">Log out</button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}