import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import PathCard from '../components/PathCard'
import SlackChart from '../components/SlackChart'
import SummaryCards from '../components/SummaryCards'

export default function AnalysisPage() {
  const { id } = useParams()
  const [analysis, setAnalysis] = useState(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('violated')
  const [apiKeys, setApiKeys] = useState([])

  useEffect(() => {
    api.getAnalysis(id).then(setAnalysis).catch((err) => setError(err.message))
  }, [id])

  useEffect(() => {
    // Keys the admin has provisioned; drives the "Explain with AI" picker.
    api.listApiKeys().then(setApiKeys).catch(() => setApiKeys([]))
  }, [])

  if (error) return <p className="error">{error}</p>
  if (!analysis) return <p className="muted">Loading…</p>

  const { summary, paths } = analysis.result
  const shown = paths
    .map((p, index) => ({ ...p, index }))
    .filter((p) => filter === 'all' || p.path.status === 'VIOLATED')

  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(analysis.result, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${analysis.filename.replace(/\.[^.]+$/, '')}_analysis.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{analysis.filename}</h1>
          <p className="muted">Analyzed {new Date(analysis.created_at).toLocaleString()}</p>
        </div>
        <button className="btn" onClick={handleDownload}>Download JSON</button>
      </div>

      <SummaryCards summary={summary} />

      {paths.length > 1 && <SlackChart paths={paths} />}

      <div className="path-filter">
        <h2>// Timing Paths</h2>
        <div className="toggle">
          <button
            className={filter === 'violated' ? 'active' : ''}
            onClick={() => setFilter('violated')}
          >
            Violations ({summary.violated_paths})
          </button>
          <button
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All paths ({summary.total_paths})
          </button>
        </div>
      </div>

      {shown.length === 0 ? (
        <p className="muted">No violated paths — this report meets timing. 🎉</p>
      ) : (
        shown.map((p) => (
          <PathCard
            key={p.index}
            analysisId={analysis.id}
            pathIndex={p.index}
            analyzed={p}
            apiKeys={apiKeys}
          />
        ))
      )}
    </div>
  )
}
