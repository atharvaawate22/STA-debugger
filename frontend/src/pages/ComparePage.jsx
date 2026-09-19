import { useEffect, useState } from 'react'
import { api } from '../api'

const SECTIONS = [
  { key: 'fixed', title: 'Fixed', tone: 'met', hint: 'violated before, meets timing now' },
  { key: 'improved', title: 'Improved', tone: 'met', hint: 'still violating, but with better slack' },
  { key: 'regressed', title: 'Regressed', tone: 'violated', hint: 'still violating, with worse slack' },
  { key: 'new_violations', title: 'New violations', tone: 'violated', hint: 'met before (or not present), violating now' },
  { key: 'unchanged', title: 'Unchanged', tone: '', hint: 'still violating, slack about the same' },
  { key: 'dropped', title: 'No longer reported', tone: '', hint: 'violated before, missing from the new report' },
]

const fmt = (v) => (v == null ? '—' : v)
const signed = (v) => (v == null ? '—' : `${v > 0 ? '+' : ''}${v}`)

// Before → after for one metric. `higherIsBetter` decides the colour of "after".
function Delta({ label, before, after, higherIsBetter = true }) {
  let color
  if (before != null && after != null && before !== after) {
    const improved = higherIsBetter ? after > before : after < before
    color = improved ? 'var(--green)' : 'var(--red)'
  }
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <span className="metric-value">
        {fmt(before)} → <span style={{ color }}>{fmt(after)}</span>
      </span>
    </div>
  )
}

function Section({ title, tone, hint, rows }) {
  if (rows.length === 0) return null
  return (
    <div className="card">
      <h3>
        {title} <span className={`badge ${tone ? `badge-${tone}` : ''}`}>{rows.length}</span>
      </h3>
      <p className="muted">{hint}</p>
      <table className="history-table">
        <thead>
          <tr><th>Path</th><th>Check</th><th>Before</th><th>After</th><th>Δ (ns)</th></tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td>{r.startpoint} → {r.endpoint}</td>
              <td>{r.check_type}</td>
              <td>{fmt(r.before)}</td>
              <td>{fmt(r.after)}</td>
              <td>{signed(r.delta)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function ComparePage() {
  const [analyses, setAnalyses] = useState(null)
  const [baseId, setBaseId] = useState('')
  const [newId, setNewId] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listAnalyses().then(setAnalyses).catch((err) => setError(err.message))
  }, [])

  const handleCompare = async () => {
    setError('')
    setResult(null)
    try {
      setResult(await api.compareAnalyses(baseId, newId))
    } catch (err) {
      setError(err.message)
    }
  }

  if (analyses === null && !error) return <p className="muted">Loading…</p>

  const options = (analyses || []).map((a) => (
    <option key={a.id} value={a.id}>
      {a.filename} — {new Date(a.created_at).toLocaleString()}
    </option>
  ))

  return (
    <div>
      <div className="rule-head">
        <h1>Compare Reports</h1>
        <span className="idx">// before / after</span>
      </div>
      <p className="muted">
        Pick the report from before a fix and the one after it. Paths are matched by
        startpoint, endpoint and check type.
      </p>

      <div className="compare-controls">
        <select value={baseId} onChange={(e) => setBaseId(e.target.value)}>
          <option value="">Before (baseline)…</option>
          {options}
        </select>
        <select value={newId} onChange={(e) => setNewId(e.target.value)}>
          <option value="">After (new)…</option>
          {options}
        </select>
        <button
          className="btn btn-primary"
          disabled={!baseId || !newId || baseId === newId}
          onClick={handleCompare}
        >
          Compare
        </button>
      </div>
      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <div className="summary-cards">
            <Delta label="WNS (ns)" before={result.wns_before} after={result.wns_after} />
            <Delta label="TNS (ns)" before={result.tns_before} after={result.tns_after} />
            <Delta
              label="Violations"
              before={result.violations_before}
              after={result.violations_after}
              higherIsBetter={false}
            />
          </div>
          {SECTIONS.map((s) => (
            <Section key={s.key} title={s.title} tone={s.tone} hint={s.hint} rows={result[s.key]} />
          ))}
        </>
      )}
    </div>
  )
}
