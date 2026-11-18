import { Activity, CircleHelp, FlaskConical, Menu, X } from 'lucide-react'
import { useRef, useState, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { DemoGuideDrawer } from './DemoGuideDrawer'
import { DemoWelcome } from './DemoWelcome'

const WELCOME_STORAGE_KEY = 'propertyops_demo_welcome_seen'

function shouldShowWelcome() {
  try {
    return window.localStorage.getItem(WELCOME_STORAGE_KEY) !== 'true'
  } catch {
    return true
  }
}

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [demoDialog, setDemoDialog] = useState<'welcome' | 'guide' | null>(() => shouldShowWelcome() ? 'welcome' : null)
  const guideButtonRef = useRef<HTMLButtonElement>(null)
  const location = useLocation()
  const isLab = location.pathname.startsWith('/lab')

  function dismissWelcome(nextDialog: 'guide' | null = null) {
    try {
      window.localStorage.setItem(WELCOME_STORAGE_KEY, 'true')
    } catch {
      // The welcome can still be dismissed when browser storage is unavailable.
    }
    setDemoDialog(nextDialog)
  }

  return (
    <div className={isLab ? 'app-shell lab-shell' : 'app-shell'}>
      <header className="topbar">
        <NavLink to="/operations" className="brand" aria-label="PropertyOps AI home">
          <span className="brand-mark">
            <img
              src="/propertyops-icon.png"
              alt=""
            />
          </span>
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

        <div className="topbar-actions">
          <div className="topbar-context">
            <span className="live-dot" aria-hidden="true" /> Simulated demo
          </div>
          <button
            ref={guideButtonRef}
            type="button"
            className="topbar-guide"
            aria-haspopup="dialog"
            onClick={() => {
              setMenuOpen(false)
              setDemoDialog('guide')
            }}
          >
            <CircleHelp size={16} aria-hidden="true" /> Demo guide
          </button>
        </div>

        <button className="menu-button" onClick={() => setMenuOpen((value) => !value)} aria-label="Toggle navigation" aria-expanded={menuOpen}>
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>
      <main>{children}</main>
      {demoDialog === 'welcome' && (
        <DemoWelcome onDismiss={() => dismissWelcome()} onOpenGuide={() => dismissWelcome('guide')} />
      )}
      {demoDialog === 'guide' && (
        <DemoGuideDrawer onDismiss={() => setDemoDialog(null)} returnFocusRef={guideButtonRef} />
      )}
    </div>
  )
}
