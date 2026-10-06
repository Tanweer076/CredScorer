import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api'
import { useAuth } from '../auth'
import { Button, ErrorBox, Field, inputClass } from '../components/ui'
import { AuthPage } from './Login'

export default function Signup() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ fullName: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await signup(form.fullName, form.email, form.password)
      navigate('/applicant/new')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthPage title="Create an applicant account">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Full name" hint="As it appears on your salary slip and bank statement">
          <input required value={form.fullName} onChange={update('fullName')} className={inputClass} />
        </Field>
        <Field label="Email">
          <input type="email" required value={form.email} onChange={update('email')} className={inputClass} />
        </Field>
        <Field label="Password" hint="At least 8 characters">
          <input type="password" required minLength={8} value={form.password} onChange={update('password')} className={inputClass} />
        </Field>
        <ErrorBox message={error} />
        <Button type="submit" disabled={busy} className="w-full">{busy ? 'Creating…' : 'Create account'}</Button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">
        Already registered? <Link to="/login" className="text-indigo-700 hover:underline">Log in</Link>
      </p>
    </AuthPage>
  )
}