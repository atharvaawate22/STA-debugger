export default function SummaryCards({ summary }) {
  const cards = [
    { label: 'Total paths', value: summary.total_paths },
    {
      label: 'Violations',
      value: summary.violated_paths,
      tone: summary.violated_paths > 0 ? 'bad' : 'good',
    },
    { label: 'WNS (ns)', value: summary.wns ?? '—', tone: summary.wns != null ? 'bad' : undefined },
    { label: 'TNS (ns)', value: summary.tns !== 0 ? summary.tns : '—' },
    { label: 'Setup / Hold', value: `${summary.setup_violations} / ${summary.hold_violations}` },
  ]

  return (
    <div className="summary-cards">
      {cards.map((card) => (
        <div key={card.label} className={`metric ${card.tone || ''}`}>
          <span className="metric-label">{card.label}</span>
          <span className="metric-value">{card.value}</span>
        </div>
      ))}
    </div>
  )
}
