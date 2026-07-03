import { NavLink } from 'react-router-dom'
import { isAdmin } from '../api'

export default function Navbar({ onLogout }) {
  const username = localStorage.getItem('username')
  const admin = isAdmin()

  return (
    <nav className="navbar">
      <div className="navbar-inner container">
        <span className="brand">STA//DEBUGGER</span>
        <div className="nav-links">
          <NavLink to="/" end>New</NavLink>
          <NavLink to="/history">History</NavLink>
          {admin && <NavLink to="/admin">Admin</NavLink>}
        </div>
        <div className="nav-user">
          <span className="username">{username}</span>
          {admin && <span className="role-badge">admin</span>}
          <button className="btn btn-small" onClick={onLogout}>Log out</button>
        </div>
      </div>
    </nav>
  )
}
