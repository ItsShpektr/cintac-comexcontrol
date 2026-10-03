import { useState } from 'react'

function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLoginSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

    try {
      const response = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Error al iniciar sesión')
      }

      // Guardamos el token en el almacenamiento local para futuras peticiones
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('rol', data.rol)

      // Llamamos a la función onLogin pasando el rol real devuelto por la base de datos
      onLogin(data.rol)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: '400px', margin: '4rem auto', padding: '2rem', border: '1px solid #ccc', borderRadius: '8px', fontFamily: 'sans-serif' }}>
      <h2>CINTAC - ComexControl</h2>
      <p>Ingrese sus credenciales de acceso (RBAC)</p>
      
      {error && (
        <div style={{ marginBottom: '1rem', padding: '0.5rem', backgroundColor: '#ffe6e6', color: '#c00', borderRadius: '4px', fontSize: '0.9rem' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleLoginSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <label style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
          Correo Electrónico:
          <input 
            type="email"
            value={email} 
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="juan@comex.com"
            style={{ padding: '0.5rem', marginTop: '0.3rem' }}
          />
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
          Contraseña:
          <input 
            type="password"
            value={password} 
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="********"
            style={{ padding: '0.5rem', marginTop: '0.3rem' }}
          />
        </label>

        <button 
          type="submit" 
          disabled={loading}
          style={{ padding: '0.7rem', backgroundColor: '#0056b3', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
        >
          {loading ? 'Validando...' : 'Ingresar al Sistema'}
        </button>
      </form>
    </div>
  )
}

export default Login