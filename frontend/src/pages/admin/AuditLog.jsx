import { useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'
import { Card, ErrorBox, Field, inputClass } from '../../components/ui'

const ACTIONS = [
  'APPLICATION_CREATED', 'APPLICATION_UPDATED', 'DOCUMENT_UPLOADED', 'DOCUMENT_EXTRACTED', 'DOCUMENT_FAILED',
  'APPLICATION_SCORED', 'STATUS_CHANGE', 'AUTO_DECISION', 'MANUAL_DECISION', 'THRESHOLD_UPDATE',
]

// Every important change, newest first. Read-only: the API has no way to edit or delete these rows.
export default function AuditLog() {
  const [action, setAction] = useState('')
  const [entityType, setEntityType] = useState('')
  const [entityId, setEntityId] = useState('')
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const params = { limit: 200 }
    if (action) params.action = action
    if (entityType) params.entity_type = entityType
    if (entityId) params.entity_id = entityId
    let cancelled = false
    api.get('/admin/audit-logs', { params })
      .then((response) => {
        if (cancelled) return
        setRows(response.data)
        setError('')
      })
      .catch((err) => { if (!cancelled) setError(errorMessage(err)) })
    return () => { cancelled = true }
  }, [action, entityType, entityId])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Audit log</h1>
      <Card>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Action">
            <select className={inputClass} value={action} onChange={(e) => setAction(e.target.value)}>
              <option value="">All actions</option>
              {ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </Field>
          <Field label="Entity">
            <select className={inputClass} value={entityType} onChange={(e) => setEntityType(e.target.value)}>
              <option value="">Everything</option>
              <option value="application">Applications</option>
              <option value="document">Documents</option>
              <option value="settings">Settings</option>
            </select>
          </Field>
          <Field label="Id" hint="e.g. an application number. Leave empty to see all.">
            <input type="number" min="1" className={inputClass} value={entityId} onChange={(e) => setEntityId(e.target.value)} />
          </Field>
        </div>
      </Card>
      <ErrorBox message={error} />
      {rows === null && !error && <p className="text-slate-500">Loading…</p>}
      {rows?.length === 0 && <Card><p className="text-slate-600">No matching entries.</p></Card>}
      {rows?.length > 0 && (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">When</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">Entity</th>
                <th className="px-4 py-3 font-medium">By</th>
                <th className="px-4 py-3 font-medium">Change</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-slate-100 align-top last:border-0">
                  <td className="whitespace-nowrap px-4 py-2 text-slate-600">{new Date(row.created_at).toLocaleString()}</td>
                  <td className="px-4 py-2 font-medium text-slate-800">{row.action}</td>
                  <td className="whitespace-nowrap px-4 py-2">{row.entity_type}{row.entity_id != null && ` #${row.entity_id}`}</td>
                  <td className="px-4 py-2 text-slate-600">{row.actor_id ? `user ${row.actor_id}` : 'system'}</td>
                  <td className="px-4 py-2"><Change before={row.before} after={row.after} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}

function Change({ before, after }) {
  return (
    <div className="max-w-md space-y-1 font-mono text-xs break-all">
      {before && <p className="text-red-700">− {JSON.stringify(before)}</p>}
      {after && <p className="text-emerald-700">+ {JSON.stringify(after)}</p>}
    </div>
  )
}