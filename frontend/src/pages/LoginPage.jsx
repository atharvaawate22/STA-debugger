import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setSession } from '../api'

export default function LoginPage() {
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const call = mode === 'login' ? api.login : api.register
      const data = await call(username, password)
      setSession(data.access_token, data.username, data.role)
      navigate(data.role === 'admin' ? '/admin' : '/')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card framed">
        <div className="auth-head">
          <span>STA//DEBUGGER</span>
          <span><span className="dot">●</span> {mode === 'login' ? 'AUTH' : 'ENROLL'}</span>
        </div>
        <h1><span className="caret">&gt;</span> {mode === 'login' ? 'sign in' : 'new account'}</h1>
        <p className="subtitle">
          Static timing analysis console. Upload an OpenSTA report and get a
          per-path diagnosis of every setup and hold violation.
        </p>

        <form onSubmit={handleSubmit}>
        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            required
          />
        </label>

        {error && <p className="error">{error}</p>}

        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
        </button>
        </form>

        <p className="auth-switch">
          {mode === 'login' ? (
            <>No account?{' '}
              <button className="link" onClick={() => { setMode('register'); setError('') }}>
                Register
              </button>
            </>
          ) : (
            <>Already registered?{' '}
              <button className="link" onClick={() => { setMode('login'); setError('') }}>
                Log in
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  )
}
