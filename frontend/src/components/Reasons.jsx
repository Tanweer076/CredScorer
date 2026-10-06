// The factors that moved the score, with a red or green marker for which way.
export default function Reasons({ reasons }) {
  return (
    <ul className="space-y-2">
      {reasons.map((reason) => {
        const raises = reason.direction === 'increases_risk'
        return (
          <li key={reason.feature} className="flex gap-2 text-sm">
            <span className={`mt-0.5 font-bold ${raises ? 'text-red-600' : 'text-emerald-600'}`}>{raises ? '▲' : '▼'}</span>
            <span className="text-slate-700">{reason.text}</span>
          </li>
        )
      })}
    </ul>
  )
}