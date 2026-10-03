import { useState, useEffect } from 'react'
import Login from './components/Login'
import './App.css'

function App() {
  const [userRole, setUserRole] = useState(null)
  const [apiMessage, setApiMessage] = useState('Cargando...')

  useEffect(() => {
    if (userRole) {
      fetch('https://cintac-comexcontrol.onrender.com/')
        .then((res) => res.json())
        .then((data) => setApiMessage(data.message))
        .catch((err) => console.error(err))
    }
  }, [userRole])

  if (!userRole) {
    return <Login onLogin={(role) => setUserRole(role)} />
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #ccc', paddingBottom: '1rem' }}>
        <h2>CINTAC - ComexControl (Panel Principal)</h2>
        <div>
          <span>Rol activo: <strong>{userRole}</strong></span>
          <button 
            onClick={() => setUserRole(null)} 
            style={{ marginLeft: '1rem', padding: '0.3rem 0.6rem', cursor: 'pointer' }}
          >
            Cerrar Sesión
          </button>
        </div>
      </header>

      <main style={{ marginTop: '2rem' }}>
        <h3>Estado de conexión con el Backend:</h3>
        <p><strong>{apiMessage}</strong></p>
        
        {/* Aquí agregaremos el formulario del Cotizador de Fletes en el siguiente paso */}
        <div style={{ marginTop: '2rem', padding: '1rem', background: '#f4f4f4', borderRadius: '6px' }}>
          <h4>Módulo de Cotización de Fletes Marítimos</h4>
          <p>Próximamente formulario de Origen, Destino y cálculo automático de recargos (BAF, THC).</p>
        </div>
      </main>
    </div>
  )
}

export default App