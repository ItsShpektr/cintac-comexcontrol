import { useState } from 'react'

function Login({ onLogin }) {
  const [selectedRole, setSelectedRole] = useState('Analista Comex')

  const handleLoginSubmit = (e) => {
    e.preventDefault()
    // Simulamos el inicio de sesión pasando el rol seleccionado
    onLogin(selectedRole)
  }

  return (
    <div style={{ maxWidth: '400px', margin: '4rem auto', padding: '2rem', border: '1px solid #ccc', borderRadius: '8px', fontFamily: 'sans-serif' }}>
      <h2>CINTAC - ComexControl</h2>
      <p>Seleccione su rol para iniciar sesión (RBAC)</p>
      
      <form onSubmit={handleLoginSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <label style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
          Rol de Usuario:
          <select 
            value={selectedRole} 
            onChange={(e) => setSelectedRole(e.target.value)}
            style={{ padding: '0.5rem', marginTop: '0.3rem' }}
          >
            <option value="Analista Comex">Analista Comex</option>
            <option value="Jefatura Finanzas">Jefatura Finanzas</option>
            <option value="Administrador">Administrador</option>
          </select>
        </label>

        <button 
          type="submit" 
          style={{ padding: '0.7rem', backgroundColor: '#0056b3', color: '#white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
        >
          Ingresar al Sistema
        </button>
      </form>
    </div>
  )
}

export default Login