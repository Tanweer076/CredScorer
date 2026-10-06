import { useState } from 'react'
import api, { errorMessage } from '../api'
import { money } from '../format'
import Reasons from './Reasons'
import { Button, Card, ErrorBox } from './ui'

// "What if I asked for less, or for longer?" Re-scores with changed values. Nothing is saved.
export default function WhatIf({ application }) {
  const original = {
    monthly_income: Number(application.declared_monthly_income),
    amount_requested: Number(application.amount_requested),
    term_months: application.term_months,
    employment_years: application.employment_years,
  }
  const [values, setValues] = useState(original)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const sliders = [
    { key: 'amount_requested', label: 'Loan amount', min: 10000, max: Math.max(original.amount_requested * 2, 50000), step: 5000, show: money },
    { key: 'term_months', label: 'Loan length', min: 6, max: Math.max(original.term_months, 120), step: 6, show: (v) => `${v} months` },
    { key: 'monthly_income', label: 'Monthly income', min: 5000, max: Math.max(original.monthly_income * 2, 50000), step: 1000, show: money },
    { key: 'employment_years', label: 'Years in current job', min: 0, max: 40, step: 0.5, show: (v) => `${v} years` },
  ]

  function change(key, value) {
    setValues({ ...values, [key]: Number(value) })
  }

  async function tryIt() {
    // Only send what actually changed.
    const changes = Object.fromEntries(Object.entries(values).filter(([key, value]) => value !== original[key]))
    if (Object.keys(changes).length === 0) {
      setError('Move a slider first')
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await api.post(`/applications/${application.id}/what-if`, changes)
      setResult(response.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setValues(original)
    setResult(null)
    setError('')
  }

  return (
    <Card title="What if?">
      <p className="mb-4 text-sm text-slate-600">Try different numbers to see how your score would change. Nothing is saved.</p>
      <div className="space-y-4">
        {sliders.map((s) => (
          <label key={s.key} className="block">
            <span className="flex justify-between text-sm">
              <span className="font-medium text-slate-700">{s.label}</span>
              <span className="text-slate-800">{s.show(values[s.key])}</span>
            </span>
            <input
              type="range"
              min={s.min}
              max={s.max}
              step={s.step}
              value={values[s.key]}
              onChange={(e) => change(s.key, e.target.value)}
              className="w-full accent-indigo-600"
            />
          </label>
        ))}
      </div>
      <div className="mt-4 flex gap-2">
        <Button onClick={tryIt} disabled={loading}>{loading ? 'Checking…' : 'See my new score'}</Button>
        <Button variant="secondary" onClick={reset}>Reset</Button>
      </div>
      <div className="mt-3"><ErrorBox message={error} /></div>

      {result && (
        <div className="mt-4 rounded-lg bg-slate-50 p-4">
          <div className="flex items-baseline gap-3">
            <span className="text-slate-500">{result.current.score}</span>
            <span className="text-slate-400">→</span>
            <span className="text-3xl font-bold text-slate-800">{result.scenario.score}</span>
            <span className={`font-semibold ${result.score_change >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {result.score_change >= 0 ? '+' : ''}{result.score_change}
            </span>
            <span className="text-sm text-slate-500">({result.scenario.band})</span>
          </div>
          <p className="mt-1 text-sm text-slate-600">
            Monthly repayment: {money(result.current.monthly_emi)} → <strong>{money(result.scenario.monthly_emi)}</strong>
          </p>
          {result.score_change === 0 && (
            <p className="mt-1 text-xs text-slate-500">The score moves in steps, so small changes often leave it the same. Try a bigger change.</p>
          )}
          <div className="mt-3"><Reasons reasons={result.scenario.reasons} /></div>
        </div>
      )}
    </Card>
  )
}