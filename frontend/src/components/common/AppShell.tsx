import { Activity, FlaskConical, Menu, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const isLab = location.pathname.startsWith('/lab')

  return (
    <div className={isLab ? 'app-shell lab-shell' : 'app-shell'}>
      <header className="topbar">
        <NavLink to="/operations" className="brand" aria-label="PropertyOps AI home">
          <span className="brand-mark"><Activity size={18} strokeWidth={2.3} /></span>
          <span>
            <strong>PropertyOps</strong>
            <small>AI Investigator</small>
          </span>
        </NavLink>

        <nav className={menuOpen ? 'primary-nav open' : 'primary-nav'} aria-label="Main navigation">
          <NavLink to="/operations" onClick={() => setMenuOpen(false)}>
            <Activity size={16} /> Operations
          </NavLink>
          <NavLink to="/lab" onClick={() => setMenuOpen(false)}>
            <FlaskConical size={16} /> Lab
          </NavLink>
        </nav>

        <div className="topbar-context" aria-label="System status">
          <span className="live-dot" /> Demo environment
        </div>

        <button className="menu-button" onClick={() => setMenuOpen((value) => !value)} aria-label="Toggle navigation" aria-expanded={menuOpen}>
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>
      <main>{children}</main>
    </div>
  )
}
