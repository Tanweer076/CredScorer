import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../../api'
import { Card, ErrorBox } from '../../components/ui'
import { money } from '../../format'

// Applications the decision engine sent to a person, oldest first.
export default function ReviewQueue() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/underwriter/queue')
      .then((response) => setItems(response.data))
      .catch((err) => setError(errorMessage(err)))
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Review queue</h1>
      <ErrorBox message={error} />
      {items === null && !error && <p className="text-slate-500">Loading…</p>}
      {items?.length === 0 && <Card><p className="text-slate-600">Nothing to review. 🎉</p></Card>}
      {items?.length > 0 && (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">#</th>
                <th className="px-4 py-3 font-medium">Applicant</th>
                <th className="px-4 py-3 font-medium">Amount</th>
                <th className="px-4 py-3 font-medium">Income / month</th>
                <th className="px-4 py-3 font-medium">Score</th>
                <th className="px-4 py-3 font-medium">Why it needs review</th>
                <th className="px-4 py-3 font-medium">Waiting since</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.application_id} className="border-b border-slate-100 align-top last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link to={`/underwriter/applications/${item.application_id}`} className="font-medium text-indigo-700 hover:underline">
                      {item.application_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{item.applicant_name}</td>
                  <td className="px-4 py-3">{money(item.amount_requested)}</td>
                  <td className="px-4 py-3">{money(item.declared_monthly_income)}</td>
                  <td className="px-4 py-3">{item.score ?? '-'} <span className="text-slate-500">{item.band}</span></td>
                  <td className="max-w-xs px-4 py-3 text-slate-600">{item.review_reason}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">{new Date(item.waiting_since).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}