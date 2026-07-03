import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { clearSession, getToken, isAdmin } from './api'
import Navbar from './components/Navbar'
import AdminPage from './pages/AdminPage'
import AnalysisPage from './pages/AnalysisPage'
import HistoryPage from './pages/HistoryPage'
import LoginPage from './pages/LoginPage'
import UploadPage from './pages/UploadPage'

function RequireAuth({ children }) {
  if (!getToken()) return <Navigate to="/login" replace />
  return children
}

function RequireAdmin({ children }) {
  if (!getToken()) return <Navigate to="/login" replace />
  if (!isAdmin()) return <Navigate to="/" replace />
  return children
}

export default function App() {
  const navigate = useNavigate()

  const handleLogout = () => {
    clearSession()
    navigate('/login')
  }

  return (
    <>
      {getToken() && <Navbar onLogout={handleLogout} />}
      <main className="container">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<RequireAuth><UploadPage /></RequireAuth>} />
          <Route path="/history" element={<RequireAuth><HistoryPage /></RequireAuth>} />
          <Route path="/analyses/:id" element={<RequireAuth><AnalysisPage /></RequireAuth>} />
          <Route path="/admin" element={<RequireAdmin><AdminPage /></RequireAdmin>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  )
}
