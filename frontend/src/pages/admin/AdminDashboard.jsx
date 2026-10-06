import { useEffect, useState } from 'react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import api, { errorMessage } from '../../api'
import { Button, Card, ErrorBox, Field, inputClass } from '../../components/ui'

const STATUS_ORDER = ['SUBMITTED', 'DOCS_VERIFIED', 'SCORED', 'MANUAL_REVIEW', 'APPROVED', 'REJECTED']

export default function AdminDashboard() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Admin dashboard</h1>
      <Stats />
      <div className="grid gap-6 lg:grid-cols-2">
        <ThresholdsForm />
        <StaffForm />
      </div>
    </div>
  )
}

function Stats() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/admin/stats')
      .then((response) => setStats(response.data))
      .catch((err) => setError(errorMessage(err)))
  }, [])

  if (error) return <ErrorBox message={error} />
  if (!stats) return <p className="text-slate-500">Loading…</p>

  const total = Object.values(stats.applications_by_status).reduce((a, b) => a + b, 0)
  const chartData = STATUS_ORDER.map((status) => ({ status, count: stats.applications_by_status[status] || 0 }))

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-4">
        <Tile label="Applications" value={total} />
        <Tile label="Waiting for review" value={stats.waiting_for_review} />
        <Tile label="Approval rate" value={stats.approval_rate == null ? '-' : `${Math.round(stats.approval_rate * 100)}%`} />
        <Tile label="Average score" value={stats.average_score ?? '-'} />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Applications by status" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ left: -20 }}>
              <XAxis dataKey="status" tick={{ fontSize: 11 }} interval={0} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Decisions">
          {Object.keys(stats.decisions).length === 0 && <p className="text-sm text-slate-500">None yet.</p>}
          <ul className="space-y-1 text-sm">
            {Object.entries(stats.decisions).map(([key, count]) => (
              <li key={key} className="flex justify-between"><span className="text-slate-600">{key}</span><span className="font-medium">{count}</span></li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  )
}

function Tile({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-800">{value}</p>
    </div>
  )
}

// The score cut-offs the decision engine uses. A change applies to the next decision.
function ThresholdsForm() {
  const [form, setForm] = useState(null)
  const [source, setSource] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get('/admin/thresholds')
      .then((response) => {
        const { source: from, ...values } = response.data
        setForm(values)
        setSource(from)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  function change(event) {
    setForm({ ...form, [event.target.name]: event.target.value })
    setMessage('')
  }

  async function save(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const response = await api.put('/admin/thresholds', {
        approve_min_score: Number(form.approve_min_score),
        reject_max_score: Number(form.reject_max_score),
        max_emi_share: Number(form.max_emi_share),
      })
      setSource(response.data.source)
      setMessage('Saved. New decisions use these values.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title="Decision thresholds">
      {!form && !error && <p className="text-slate-500">Loading…</p>}
      {form && (
        <form onSubmit={save} className="space-y-4">
          <Field label="Approve at or above score">
            <input name="approve_min_score" type="number" min="0" max="1000" required className={inputClass} value={form.approve_min_score} onChange={change} />
          </Field>
          <Field label="Reject below score">
            <input name="reject_max_score" type="number" min="0" max="1000" required className={inputClass} value={form.reject_max_score} onChange={change} />
          </Field>
          <Field label="Most of the monthly income the EMI may take" hint="0.5 means half. Above this, a person reviews the application.">
            <input name="max_emi_share" type="number" min="0.05" max="1" step="0.05" required className={inputClass} value={form.max_emi_share} onChange={change} />
          </Field>
          <p className="text-xs text-slate-500">Currently from: {source}</p>
          <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save thresholds'}</Button>
          {message && <p className="text-sm text-emerald-700">{message}</p>}
        </form>
      )}
      <div className="mt-2"><ErrorBox message={error} /></div>
    </Card>
  )
}

const EMPTY_STAFF = { full_name: '', email: '', password: '', role: 'underwriter' }

// Staff can't sign up themselves; an admin creates their accounts.
function StaffForm() {
  const [form, setForm] = useState(EMPTY_STAFF)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  function change(event) {
    setForm({ ...form, [event.target.name]: event.target.value })
  }

  async function create(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const response = await api.post('/auth/staff', form)
      setMessage(`Created ${response.data.role} ${response.data.email}.`)
      setForm(EMPTY_STAFF)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title="Add a staff member">
      <form onSubmit={create} className="space-y-4">
        <Field label="Full name">
          <input name="full_name" required minLength={2} className={inputClass} value={form.full_name} onChange={change} />
        </Field>
        <Field label="Email">
          <input name="email" type="email" required className={inputClass} value={form.email} onChange={change} />
        </Field>
        <Field label="Password" hint="At least 8 characters. Share it with them privately.">
          <input name="password" type="password" required minLength={8} className={inputClass} value={form.password} onChange={change} />
        </Field>
        <Field label="Role">
          <select name="role" className={inputClass} value={form.role} onChange={change}>
            <option value="underwriter">Underwriter</option>
            <option value="admin">Admin</option>
          </select>
        </Field>
        <Button type="submit" disabled={saving}>{saving ? 'Creating…' : 'Create account'}</Button>
        {message && <p className="text-sm text-emerald-700">{message}</p>}
        <ErrorBox message={error} />
      </form>
    </Card>
  )
}