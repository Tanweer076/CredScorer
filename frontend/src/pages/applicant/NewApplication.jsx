import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { errorMessage } from '../../api'
import { Button, Card, ErrorBox, Field, inputClass } from '../../components/ui'

// Values must match the Literal types in backend/app/applications/schemas.py.
const OPTIONS = {
  employment_type: [['salaried', 'Salaried'], ['self_employed', 'Self-employed'], ['unemployed', 'Unemployed'],
    ['student', 'Student'], ['retired', 'Retired']],
  education: [['lower_secondary', 'Below 10th'], ['secondary', '10th / 12th'], ['incomplete_higher', 'Graduation, not finished'],
    ['higher', 'Graduate'], ['academic_degree', 'Postgraduate / PhD']],
  family_status: [['single', 'Single'], ['married', 'Married'], ['civil_marriage', 'Living together'],
    ['separated', 'Separated / divorced'], ['widow', 'Widowed']],
  housing_type: [['owned', 'Own house / flat'], ['rented', 'Rented'], ['with_parents', 'With parents'],
    ['municipal', 'Government housing'], ['office', 'Company accommodation'], ['co_op', 'Co-operative housing']],
}

const EMPTY = {
  amount_requested: '', term_months: '24', purpose: '', declared_monthly_income: '',
  employment_type: 'salaried', employment_years: '', date_of_birth: '', children: '0', family_members: '1',
  owns_car: false, owns_home: false, education: 'higher', family_status: 'single', housing_type: 'rented',
}

export default function NewApplication() {
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (key) => (e) =>
    setForm({ ...form, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const payload = {
        ...form,
        amount_requested: Number(form.amount_requested),
        term_months: Number(form.term_months),
        declared_monthly_income: Number(form.declared_monthly_income),
        employment_years: Number(form.employment_years || 0),
        children: Number(form.children),
        family_members: Number(form.family_members),
      }
      const { data } = await api.post('/applications', payload)
      navigate(`/applicant/applications/${data.id}`)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const select = (key) => (
    <select value={form[key]} onChange={update(key)} className={inputClass}>
      {OPTIONS[key].map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select>
  )

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">New loan application</h1>

      <Card title="The loan">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Amount (₹)">
            <input type="number" required min="1000" step="1000" value={form.amount_requested} onChange={update('amount_requested')} className={inputClass} />
          </Field>
          <Field label="Term (months)">
            <input type="number" required min="3" max="360" value={form.term_months} onChange={update('term_months')} className={inputClass} />
          </Field>
          <Field label="Purpose">
            <input required minLength={2} maxLength={100} placeholder="e.g. Home renovation" value={form.purpose} onChange={update('purpose')} className={inputClass} />
          </Field>
        </div>
      </Card>

      <Card title="Income and work">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Monthly income (₹)" hint="Gross, before deductions. It is checked against your salary slip.">
            <input type="number" required min="0" value={form.declared_monthly_income} onChange={update('declared_monthly_income')} className={inputClass} />
          </Field>
          <Field label="Employment">{select('employment_type')}</Field>
          <Field label="Years in current job">
            <input type="number" min="0" max="60" step="0.5" value={form.employment_years} onChange={update('employment_years')} className={inputClass} />
          </Field>
        </div>
      </Card>

      <Card title="About you">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Date of birth">
            <input type="date" required value={form.date_of_birth} onChange={update('date_of_birth')} className={inputClass} />
          </Field>
          <Field label="Education">{select('education')}</Field>
          <Field label="Family status">{select('family_status')}</Field>
          <Field label="Children">
            <input type="number" required min="0" max="20" value={form.children} onChange={update('children')} className={inputClass} />
          </Field>
          <Field label="People in household">
            <input type="number" required min="1" max="30" value={form.family_members} onChange={update('family_members')} className={inputClass} />
          </Field>
          <Field label="Housing">{select('housing_type')}</Field>
        </div>
        <div className="mt-4 flex gap-6 text-sm text-slate-700">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.owns_car} onChange={update('owns_car')} /> I own a car
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.owns_home} onChange={update('owns_home')} /> I own a home
          </label>
        </div>
      </Card>

      <ErrorBox message={error} />
      <Button type="submit" disabled={busy}>{busy ? 'Submitting…' : 'Submit application'}</Button>
    </form>
  )
}