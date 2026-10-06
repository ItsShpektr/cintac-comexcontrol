import { useEffect, useState } from 'react'
import { FileClock, LogOut, Settings2, ShipWheel } from 'lucide-react'
import AdminPanel from './components/AdminPanel'
import HistoryPanel from './components/HistoryPanel'
import Login from './components/Login'
import QuotePanel from './components/QuotePanel'
import { apiFetch, clearSession, getToken } from './lib/api'

function defaultTabForRole(role) {
  if (role === 'Analista COMEX') return 'cotizar'
  if (role === 'Administrador') return 'admin'
  return 'historial'
}

function App() {
  const [user, setUser] = useState(null)
  const [loadingSession, setLoadingSession] = useState(Boolean(getToken()))
  const [tab, setTab] = useState('historial')

  useEffect(() => {
    const unauthorized = () => {
      setUser(null)
      setTab('historial')
    }
    window.addEventListener('comex:unauthorized', unauthorized)
    return () => window.removeEventListener('comex:unauthorized', unauthorized)
  }, [])

  useEffect(() => {
    if (!getToken()) {
      setLoadingSession(false)
      return
    }

    apiFetch('/api/me')
      .then((data) => {
        setUser(data)
        setTab(defaultTabForRole(data.rol))
      })
      .catch(() => {
        clearSession()
        setUser(null)
      })
      .finally(() => setLoadingSession(false))
  }, [])

  const handleLogin = (loggedUser) => {
    setUser(loggedUser)
    setTab(defaultTabForRole(loggedUser.rol))
  }

  const logout = () => {
    clearSession()
    setUser(null)
    setTab('historial')
  }

  if (loadingSession) return <div className="splash">Validando sesión segura…</div>
  if (!user) return <Login onLogin={handleLogin} />

  const canQuote = user.rol === 'Analista COMEX'
  const isAdmin = user.rol === 'Administrador'

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <span className="brand-mark compact">CINTAC</span>
          <div>
            <strong>ComexControl</strong>
            <small>Gestión logística y cotizaciones</small>
          </div>
        </div>

        <div className="account-block">
          <div>
            <strong>{user.nombre}</strong>
            <small>{user.rol}</small>
          </div>
          <button className="icon-button" onClick={logout} title="Cerrar sesión" aria-label="Cerrar sesión">
            <LogOut size={19} />
          </button>
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          {canQuote && (
            <button className={tab === 'cotizar' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('cotizar')}>
              <ShipWheel size={19} /> Cotizar
            </button>
          )}

          <button className={tab === 'historial' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('historial')}>
            <FileClock size={19} /> Historial
          </button>

          {isAdmin && (
            <button className={tab === 'admin' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('admin')}>
              <Settings2 size={19} /> Administración
            </button>
          )}

          <div className="sidebar-note">
            <span>Seguridad</span>
            <p>Sesión JWT, permisos por rol, validación de datos y auditoría.</p>
          </div>
        </aside>

        <main className="content-area">
          {tab === 'cotizar' && canQuote && <QuotePanel />}
          {tab === 'historial' && <HistoryPanel />}
          {tab === 'admin' && isAdmin && <AdminPanel />}
        </main>
      </div>
    </div>
  )
}

export default App
