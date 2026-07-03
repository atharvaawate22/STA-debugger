import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export default function SlackChart({ paths }) {
  const data = paths
    .map((p) => ({
      name: `${p.path.startpoint} → ${p.path.endpoint}`,
      slack: p.path.slack,
      violated: p.path.status === 'VIOLATED',
    }))
    .sort((a, b) => a.slack - b.slack)
    .slice(0, 15) // worst 15 paths keep the chart readable

  return (
    <div className="card chart-card">
      <h3>Slack per path — worst first</h3>
      <ResponsiveContainer width="100%" height={Math.max(120, data.length * 34)}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="#322d25" horizontal={false} />
          <XAxis
            type="number"
            unit=" ns"
            stroke="#6a6355"
            tick={{ fontSize: 11, fill: '#948c79', fontFamily: 'IBM Plex Mono, monospace' }}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={220}
            stroke="#6a6355"
            tick={{ fontSize: 11, fill: '#948c79', fontFamily: 'IBM Plex Mono, monospace' }}
          />
          <Tooltip
            formatter={(value) => [`${value} ns`, 'slack']}
            cursor={{ fill: 'rgba(232,168,56,0.08)' }}
            contentStyle={{
              background: '#1a1714',
              border: '1px solid #4a4235',
              borderRadius: 2,
              fontFamily: 'IBM Plex Mono, monospace',
              fontSize: 12,
              color: '#ece7d9',
            }}
          />
          <ReferenceLine x={0} stroke="#6a6355" />
          <Bar dataKey="slack" radius={[0, 0, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.violated ? '#e2543b' : '#9cc24e'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
