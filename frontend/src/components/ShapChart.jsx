import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

// SHAP values as horizontal bars: red pushes the risk up, green pulls it down.
// The longer the bar, the more that factor moved this applicant's score.
export default function ShapChart({ reasons }) {
  const data = reasons.map((r) => ({
    name: r.text.split(':')[0], // "Monthly income: ₹60,000. This..." -> "Monthly income"
    impact: r.impact,
    text: r.text,
  }))
  return (
    <ResponsiveContainer width="100%" height={48 * data.length + 40}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 8, bottom: 8 }}>
        <XAxis type="number" tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey="name" width={190} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(value) => [value.toFixed(3), 'Impact on risk']} labelFormatter={(_, payload) => payload?.[0]?.payload.text} />
        <ReferenceLine x={0} stroke="#94a3b8" />
        <Bar dataKey="impact" isAnimationActive={false}>
          {data.map((d) => <Cell key={d.name} fill={d.impact > 0 ? '#dc2626' : '#059669'} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}