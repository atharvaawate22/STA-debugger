import { useEffect, useState } from 'react'
import { api } from '../api'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'users', label: 'Users' },
  { id: 'keys', label: 'API Keys' },
  { id: 'analyses', label: 'All Analyses' },
]

export default function AdminPage() {
  const [tab, setTab] = useState('overview')

  return (
    <div>
      <div className="rule-head">
        <h1>Admin Console</h1>
        <span className="idx">// root</span>
      </div>
      <p className="muted">Manage users, the shared API-key pool, and every user's history.</p>

      <div className="admin-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? 'active' : ''}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab />}
      {tab === 'users' && <UsersTab />}
      {tab === 'keys' && <KeysTab />}
      {tab === 'analyses' && <AnalysesTab />}
    </div>
  )
}

function useAsync(loader, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const reload = () => setReloadKey((k) => k + 1)

  useEffect(() => {
    let alive = true
    loader()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e.message))
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey, ...deps])

  return { data, error, reload }
}

// ---------- Overview ----------

function OverviewTab() {
  const { data, error } = useAsync(() => api.admin.stats())
  if (error) return <p className="error">{error}</p>
  if (!data) return <p className="muted">Loading…</p>

  const cards = [
    { label: 'Users', value: data.total_users },
    { label: 'Admins', value: data.total_admins },
    { label: 'Analyses', value: data.total_analyses },
    { label: 'Violations found', value: data.total_violations },
    { label: 'Active API keys', value: data.active_api_keys },
  ]
  return (
    <div className="summary-cards">
      {cards.map((c) => (
        <div key={c.label} className="metric">
          <span className="metric-label">{c.label}</span>
          <span className="metric-value">{c.value}</span>
        </div>
      ))}
    </div>
  )
}

// ---------- Users ----------

function UsersTab() {
  const { data: users, error, reload } = useAsync(() => api.admin.listUsers())
  const [form, setForm] = useState({ username: '', password: '', role: 'user' })
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)
  const me = localStorage.getItem('username')

  const createUser = async (e) => {
    e.preventDefault()
    setFormError('')
    setBusy(true)
    try {
      await api.admin.createUser(form.username, form.password, form.role)
      setForm({ username: '', password: '', role: 'user' })
      reload()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const toggleRole = async (u) => {
    const next = u.role === 'admin' ? 'user' : 'admin'
    try {
      await api.admin.updateUser(u.id, { role: next })
      reload()
    } catch (err) { alert(err.message) }
  }

  const resetPassword = async (u) => {
    const pw = prompt(`New password for ${u.username} (min 6 chars):`)
    if (!pw) return
    try {
      await api.admin.updateUser(u.id, { password: pw })
      alert('Password updated.')
    } catch (err) { alert(err.message) }
  }

  const removeUser = async (u) => {
    if (!confirm(`Delete ${u.username} and all their analyses? This cannot be undone.`)) return
    try {
      await api.admin.deleteUser(u.id)
      reload()
    } catch (err) { alert(err.message) }
  }

  if (error) return <p className="error">{error}</p>

  return (
    <div>
      <div className="card">
        <h3>Add a user</h3>
        <form className="inline-form" onSubmit={createUser}>
          <input
            placeholder="username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
          />
          <input
            type="password"
            placeholder="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
          <button className="btn btn-primary btn-small" disabled={busy}>Create</button>
        </form>
        {formError && <p className="error">{formError}</p>}
      </div>

      {!users ? <p className="muted">Loading…</p> : (
        <table className="history-table">
          <thead>
            <tr><th>User</th><th>Role</th><th>Analyses</th><th>Joined</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username}{u.username === me && ' (you)'}</td>
                <td>
                  <span className={`badge ${u.role === 'admin' ? 'badge-high' : ''}`}>{u.role}</span>
                </td>
                <td>{u.analysis_count}</td>
                <td>{new Date(u.created_at).toLocaleDateString()}</td>
                <td className="row-actions">
                  <button className="link" onClick={() => toggleRole(u)} disabled={u.username === me}>
                    {u.role === 'admin' ? 'Demote' : 'Promote'}
                  </button>
                  <button className="link" onClick={() => resetPassword(u)}>Reset password</button>
                  <button className="link danger" onClick={() => removeUser(u)} disabled={u.username === me}>
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

// ---------- API Keys ----------

function KeysTab() {
  const { data: keys, error, reload } = useAsync(() => api.admin.listApiKeys())
  const [form, setForm] = useState({ label: '', secret: '' })
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)

  const addKey = async (e) => {
    e.preventDefault()
    setFormError('')
    setBusy(true)
    try {
      await api.admin.createApiKey(form.label, form.secret)
      setForm({ label: '', secret: '' })
      reload()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const toggleActive = async (k) => {
    try {
      await api.admin.updateApiKey(k.id, { is_active: !k.is_active })
      reload()
    } catch (err) { alert(err.message) }
  }

  const removeKey = async (k) => {
    if (!confirm(`Delete key "${k.label}"? Users relying on it will lose AI explanations.`)) return
    try {
      await api.admin.deleteApiKey(k.id)
      reload()
    } catch (err) { alert(err.message) }
  }

  if (error) return <p className="error">{error}</p>

  return (
    <div>
      <div className="card">
        <h3>Add a Groq API key</h3>
        <p className="muted">Users pick keys by label — the secret is never shown to them.</p>
        <form className="inline-form" onSubmit={addKey}>
          <input
            placeholder="label (e.g. Team key)"
            value={form.label}
            onChange={(e) => setForm({ ...form, label: e.target.value })}
            required
          />
          <input
            type="password"
            placeholder="gsk_… secret"
            value={form.secret}
            onChange={(e) => setForm({ ...form, secret: e.target.value })}
            required
          />
          <button className="btn btn-primary btn-small" disabled={busy}>Add key</button>
        </form>
        {formError && <p className="error">{formError}</p>}
      </div>

      {!keys ? <p className="muted">Loading…</p> : keys.length === 0 ? (
        <p className="muted">No keys yet. Add one so users can run AI explanations.</p>
      ) : (
        <table className="history-table">
          <thead>
            <tr><th>Label</th><th>Key</th><th>Status</th><th>Added by</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k.id}>
                <td>{k.label}</td>
                <td><code>{k.masked}</code></td>
                <td>
                  <span className={`badge ${k.is_active ? 'badge-met' : ''}`}>
                    {k.is_active ? 'active' : 'disabled'}
                  </span>
                </td>
                <td>{k.created_by}</td>
                <td className="row-actions">
                  <button className="link" onClick={() => toggleActive(k)}>
                    {k.is_active ? 'Disable' : 'Enable'}
                  </button>
                  <button className="link danger" onClick={() => removeKey(k)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ---------- All analyses ----------

function AnalysesTab() {
  const { data, error, reload } = useAsync(() => api.admin.listAnalyses())

  const remove = async (a) => {
    if (!confirm(`Delete "${a.filename}" (uploaded by ${a.username})?`)) return
    try {
      await api.admin.deleteAnalysis(a.id)
      reload()
    } catch (err) { alert(err.message) }
  }

  if (error) return <p className="error">{error}</p>
  if (!data) return <p className="muted">Loading…</p>
  if (data.length === 0) return <p className="muted">No analyses uploaded yet.</p>

  return (
    <table className="history-table">
      <thead>
        <tr><th>User</th><th>File</th><th>Violations</th><th>WNS</th><th>Uploaded</th><th></th></tr>
      </thead>
      <tbody>
        {data.map((a) => (
          <tr key={a.id}>
            <td>{a.username}</td>
            <td>{a.filename}</td>
            <td>{a.summary.violated_paths} / {a.summary.total_paths}</td>
            <td>{a.summary.wns != null ? `${a.summary.wns} ns` : '—'}</td>
            <td>{new Date(a.created_at).toLocaleString()}</td>
            <td className="row-actions">
              <button className="link danger" onClick={() => remove(a)}>Delete</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
