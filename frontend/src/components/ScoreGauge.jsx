import { PolarAngleAxis, RadialBar, RadialBarChart } from 'recharts'

const BAND_COLORS = {
  Excellent: '#059669',
  Good: '#16a34a',
  Fair: '#ca8a04',
  'Below average': '#ea580c',
  Poor: '#dc2626',
}

// A half-circle gauge: the coloured part shows the score out of 1000.
export default function ScoreGauge({ score, band }) {
  const color = BAND_COLORS[band] || '#4f46e5'
  return (
    <div className="relative mx-auto h-40 w-64">
      <RadialBarChart
        width={256}
        height={160}
        cx={128}
        cy={140}
        innerRadius={95}
        outerRadius={125}
        startAngle={180}
        endAngle={0}
        barSize={24}
        data={[{ value: score }]}
      >
        <PolarAngleAxis type="number" domain={[0, 1000]} tick={false} />
        <RadialBar dataKey="value" fill={color} background={{ fill: '#e2e8f0' }} cornerRadius={12} isAnimationActive={false} />
      </RadialBarChart>
      <div className="absolute inset-x-0 bottom-3 text-center">
        <div className="text-4xl font-bold text-slate-800">{score}</div>
        <div className="text-sm font-medium" style={{ color }}>{band}</div>
      </div>
    </div>
  )
}