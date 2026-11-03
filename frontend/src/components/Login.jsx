import { useState } from 'react'
import { LockKeyhole, ShieldCheck } from 'lucide-react'
import { API_URL, setSession } from '../lib/api'

function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLoginSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'No fue posible iniciar sesión')

      // sessionStorage reduce la persistencia del token frente a localStorage.
      setSession(data.access_token)
      onLogin({ nombre: data.nombre, rol: data.rol, email })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-brand-panel">
        <div className="brand-mark">CINTAC</div>
        <p className="eyebrow">Plataforma interna de Comercio Exterior</p>
        <h1>ComexControl</h1>
        <p className="login-intro">
          Cotizaciones marítimas con datos controlados, versionados y trazables.
        </p>
        <div className="security-note">
          <ShieldCheck size={22} />
          <span>Acceso protegido por credenciales individuales y permisos por rol.</span>
        </div>
      </section>

      <section className="login-form-panel">
        <form className="login-card" onSubmit={handleLoginSubmit}>
          <div className="login-icon"><LockKeyhole size={24} /></div>
          <p className="eyebrow">Acceso seguro</p>
          <h2>Ingresar a ComexControl</h2>
          <p className="muted">Utilice su cuenta asignada por el administrador del sistema.</p>

          {error && <div className="alert alert-error">{error}</div>}

          <label className="field">
            <span>Correo electrónico</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
              placeholder="nombre@cintac.cl"
            />
          </label>

          <label className="field">
            <span>Contraseña</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              minLength={8}
              maxLength={72}
              required
              placeholder="••••••••••"
            />
          </label>

          <button className="button button-primary button-full" type="submit" disabled={loading}>
            {loading ? 'Validando acceso…' : 'Ingresar'}
          </button>
          <p className="login-help">El sistema no permite registro público ni selección libre de roles.</p>
        </form>
      </section>
    </main>
  )
}

export default Login
