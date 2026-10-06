import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api'
import { homeFor, useAuth } from '../auth'
import { Button, ErrorBox, Field, inputClass } from '../components/ui'

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={homeFor(user)} replace />

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const me = await login(email, password)
      navigate(homeFor(me))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthPage title="Log in to CredScorer">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Email">
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Password">
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className={inputClass} />
        </Field>
        <ErrorBox message={error} />
        <Button type="submit" disabled={busy} className="w-full">{busy ? 'Logging in…' : 'Log in'}</Button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">
        New here? <Link to="/signup" className="text-indigo-700 hover:underline">Create an account</Link>
      </p>
    </AuthPage>
  )
}

export function AuthPage({ title, children }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="mb-1 text-center text-xl font-bold text-indigo-700">CredScorer</p>
        <h1 className="mb-6 text-center text-sm text-slate-600">{title}</h1>
        {children}
      </div>
    </div>
  )
}