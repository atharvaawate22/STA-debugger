import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function HistoryPage() {
  const [analyses, setAnalyses] = useState(null)
  const [error, setError] = useState('')

  const load = () => {
    api.listAnalyses().then(setAnalyses).catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this analysis?')) return
    try {
      await api.deleteAnalysis(id)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  if (error) return <p className="error">{error}</p>
  if (analyses === null) return <p className="muted">Loading…</p>

  return (
    <div>
      <div className="rule-head">
        <h1>Past Analyses</h1>
        <span className="idx">// history</span>
      </div>
      {analyses.length === 0 ? (
        <p className="muted">
          Nothing here yet — run your first analysis from the{' '}
          <Link to="/">New Analysis</Link> page.
        </p>
      ) : (
        <table className="history-table">
          <thead>
            <tr>
              <th>Report</th>
              <th>Date</th>
              <th>Paths</th>
              <th>Violations</th>
              <th>WNS (ns)</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {analyses.map((a) => (
              <tr key={a.id}>
                <td><Link to={`/analyses/${a.id}`}>{a.filename}</Link></td>
                <td>{new Date(a.created_at).toLocaleString()}</td>
                <td>{a.summary.total_paths}</td>
                <td>
                  {a.summary.violated_paths > 0 ? (
                    <span className="badge badge-violated">{a.summary.violated_paths}</span>
                  ) : (
                    <span className="badge badge-met">0</span>
                  )}
                </td>
                <td>{a.summary.wns ?? '—'}</td>
                <td>
                  <button className="btn btn-small" onClick={() => handleDelete(a.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
