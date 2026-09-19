const KIND_LABEL = {
  shared_logic: 'Shared logic',
  endpoint_bus: 'Endpoint bus',
  startpoint: 'Common startpoint',
  bottleneck_cell: 'Common slow cell',
}

// Violations that share a root cause. Clicking a group filters the path list
// below to just those paths.
export default function GroupsPanel({ groups, activeKey, onSelect }) {
  if (!groups || groups.length === 0) return null

  return (
    <div className="card groups-panel">
      <h3>// Likely root causes</h3>
      <p className="muted">
        Violating paths that share logic, an endpoint bus, or a launch point. Fixing one of
        these can help several paths at once.
      </p>
      <ul className="group-list">
        {groups.map((g) => {
          const key = `${g.kind}:${g.key}:${g.check_type}`
          const active = key === activeKey
          return (
            <li key={key}>
              <button
                className={`group-row ${active ? 'active' : ''}`}
                onClick={() => onSelect(active ? null : { key, indices: g.path_indices })}
              >
                <span className="group-title">
                  <span className="badge">{KIND_LABEL[g.kind] || g.kind}</span>{' '}
                  <span className="badge">{g.check_type}</span>{' '}
                  <strong>{g.key}</strong>
                </span>
                <span className="group-stats">
                  {g.count} paths · worst {g.worst_slack} ns · {Math.round(g.tns_share * 100)}% of{' '}
                  {g.check_type} TNS
                </span>
                <span className="group-detail">{g.detail}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
