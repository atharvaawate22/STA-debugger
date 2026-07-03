import { useState } from 'react'
import { api } from '../api'

function DelayBar({ stage, maxDelay }) {
  const width = maxDelay > 0 ? Math.max(2, (stage.delay / maxDelay) * 100) : 2
  return (
    <div className="stage-row">
      <span className="stage-name" title={stage.cell}>
        {stage.instance} <em>({stage.cell})</em>
      </span>
      <div className="stage-bar-track">
        <div className="stage-bar" style={{ width: `${width}%` }} />
      </div>
      <span className="stage-delay">{stage.delay.toFixed(2)} ns</span>
    </div>
  )
}

export default function PathCard({ analysisId, pathIndex, analyzed, apiKeys = [] }) {
  const { path, diagnosis } = analyzed
  const violated = path.status === 'VIOLATED'
  const [open, setOpen] = useState(false)
  const [explanation, setExplanation] = useState('')
  const [explainError, setExplainError] = useState('')
  const [explaining, setExplaining] = useState(false)
  const [keyId, setKeyId] = useState('')

  const maxDelay = Math.max(...path.logic_chain.map((s) => s.delay), 0)

  const handleExplain = async () => {
    setExplainError('')
    setExplaining(true)
    try {
      // With multiple keys the user must choose one; a single key is implicit.
      const chosen = keyId ? Number(keyId) : (apiKeys.length === 1 ? apiKeys[0].id : null)
      const data = await api.explainPath(analysisId, pathIndex, chosen)
      setExplanation(data.explanation)
    } catch (err) {
      setExplainError(err.message)
    } finally {
      setExplaining(false)
    }
  }

  return (
    <div className={`card path-card ${violated ? 'violated' : ''}`}>
      <button className="path-header" onClick={() => setOpen(!open)}>
        <span className="path-title">
          <span className={`led ${violated ? 'bad' : ''}`} />
          {path.startpoint} → {path.endpoint}
        </span>
        <span className="path-tags">
          <span className="badge">{diagnosis.check_type}</span>
          {violated && diagnosis.severity && (
            <span className={`badge badge-${diagnosis.severity}`}>{diagnosis.severity}</span>
          )}
          <span className={`slack-tag ${violated ? 'badge badge-violated' : 'badge badge-met'}`}>
            {path.slack >= 0 ? '+' : ''}{path.slack} ns
          </span>
          <span className="chevron">{open ? '[-]' : '[+]'}</span>
        </span>
      </button>

      {open && (
        <div className="path-body">
          <div className="path-facts">
            <span>Clock group: <strong>{path.path_group || '—'}</strong></span>
            <span>Logic depth: <strong>{diagnosis.logic_depth}</strong></span>
            <span>Logic delay: <strong>{diagnosis.total_logic_delay} ns</strong></span>
            {diagnosis.clock_skew != null && (
              <span>Clock skew: <strong>{diagnosis.clock_skew} ns</strong></span>
            )}
            {diagnosis.bottleneck_instance && (
              <span>
                Bottleneck: <strong>{diagnosis.bottleneck_instance}</strong>{' '}
                ({Math.round(diagnosis.bottleneck_share * 100)}% of path delay)
              </span>
            )}
          </div>

          {path.logic_chain.length > 0 && (
            <>
              <h4>Stage delays</h4>
              <div className="stage-list">
                {path.logic_chain.map((stage, i) => (
                  <DelayBar key={i} stage={stage} maxDelay={maxDelay} />
                ))}
              </div>
            </>
          )}

          {violated && diagnosis.suggestions.length > 0 && (
            <>
              <h4>Suggested fixes</h4>
              <ol className="suggestions">
                {diagnosis.suggestions.map((s, i) => (
                  <li key={i}>
                    <span className={`badge badge-${s.priority}`}>{s.priority}</span>{' '}
                    <strong>{s.fix}</strong>
                    <p className="muted">{s.reason}</p>
                  </li>
                ))}
              </ol>
            </>
          )}

          {violated && (
            <div className="explain-section">
              {explanation ? (
                <blockquote className="explanation">{explanation}</blockquote>
              ) : apiKeys.length === 0 ? (
                <p className="muted">
                  AI explanations are unavailable — no API key has been provisioned by
                  an administrator yet.
                </p>
              ) : (
                <div className="explain-controls">
                  {apiKeys.length > 1 && (
                    <select
                      className="key-select"
                      value={keyId}
                      onChange={(e) => setKeyId(e.target.value)}
                    >
                      <option value="">Choose an API key…</option>
                      {apiKeys.map((k) => (
                        <option key={k.id} value={k.id}>{k.label} ({k.masked})</option>
                      ))}
                    </select>
                  )}
                  <button
                    className="btn btn-small"
                    onClick={handleExplain}
                    disabled={explaining || (apiKeys.length > 1 && !keyId)}
                  >
                    {explaining ? 'Asking the model…' : 'Explain with AI (optional)'}
                  </button>
                  {explainError && <p className="error">{explainError}</p>}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
