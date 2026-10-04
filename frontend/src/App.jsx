import { useState, useEffect } from 'react'
import Login from './components/Login'
import './App.css'
function App() {
const [userRole, setUserRole] = useState(null)
const [apiMessage, setApiMessage] = useState('Cargando...')
// Estados para el formulario de cotización
const [puertoOrigen, setPuertoOrigen] = useState('')
const [puertoDestino, setPuertoDestino] = useState('')
const [tipoContenedor, setTipoContenedor] = useState("20'")
const [cantidad, setCantidad] = useState(1)
// Estados para la respuesta, carga y errores del cotizador
const [resultado, setResultado] = useState(null)
const [cotizadorError, setCotizadorError] = useState('')
const [loadingCotizacion, setLoadingCotizacion] = useState(false)
const API_URL = import.meta.env.VITE_API_URL || 'https://cintac-comexcontrol.onrender.com'
useEffect(() => {
if (userRole) {
  fetch(`${API_URL}/`)
  .then((res) => res.json())
  .then((data) => setApiMessage(data.message))
  .catch((err) => console.error(err))
}
}, [userRole, API_URL])
const handleCotizarSubmit = async (e) => {
  e.preventDefault()
  setCotizadorError('')
  setResultado(null)
  setLoadingCotizacion(true)
  try {
    const response = await fetch(`${API_URL}/api/cotizar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        puerto_origen: puertoOrigen,
        puerto_destino: puertoDestino,
        tipo_contenedor: tipoContenedor,
        cantidad: Number(cantidad)
      }),
    })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Error al procesar la cotización')
  }

  setResultado(data)
} catch (err) {
  setCotizadorError(err.message)
} finally {
  setLoadingCotizacion(false)
}


}
if (!userRole) {
return <Login onLogin={(role) => setUserRole(role)} />
}
return (
<div style={{ padding: '2rem', fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif', maxWidth: '850px', margin: '0 auto', color: '#2b2b2b' }}>
  {/* HEADER CORPORATIVO CINTAC */}
  <header style={{ 
    display: 'flex', 
    justifyContent: 'space-between', 
    borderBottom: '4px solid #f37021', // Naranja CINTAC oficial
    paddingBottom: '1rem', 
    alignItems: 'center',
    backgroundColor: '#ffffff',
    padding: '1rem 1.5rem',
    borderRadius: '8px 8px 0 0',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
  }}>
    <div>
      <h2 style={{ margin: 0, color: '#1a1a1a', fontSize: '1.4rem', fontWeight: 'bold' }}>
        CINTAC <span style={{ color: '#f37021', fontWeight: 'normal' }}>| ComexControl</span>
      </h2>
      <span style={{ fontSize: '0.8rem', color: '#666', textTransform: 'uppercase', letterSpacing: '1px' }}>Portal de Gestión Logística</span>
    </div>
    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
      <span style={{ fontSize: '0.9rem', color: '#444' }}>Rol activo: <strong style={{ color: '#f37021' }}>{userRole}</strong></span>
      <button 
        onClick={() => setUserRole(null)} 
        style={{ padding: '0.4rem 0.8rem', cursor: 'pointer', backgroundColor: '#333333', color: '#fff', border: 'none', borderRadius: '4px', fontWeight: 'bold', fontSize: '0.85rem' }}
      >
        Cerrar Sesión
      </button>
    </div>
  </header>

  <main style={{ marginTop: '1.5rem' }}>
    
    {/* ESTADO DE CONEXIÓN */}
    <div style={{ marginBottom: '1.5rem', padding: '1rem', background: '#f8f9fa', borderLeft: '4px solid #2b8a3e', borderRadius: '4px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
      <p style={{ margin: 0, fontSize: '0.85rem', color: '#6c757d', textTransform: 'uppercase', fontWeight: 'bold' }}>Estado de conexión con el Backend:</p>
      <p style={{ margin: '0.3rem 0 0 0', fontWeight: 'bold', color: '#2b8a3e', fontSize: '1rem' }}>{apiMessage}</p>
    </div>
    
    {/* MÓDULO DE COTIZACIÓN */}
    <div style={{ padding: '2rem', background: '#ffffff', border: '1px solid #e0e0e0', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.02)' }}>
      <div style={{ borderBottom: '2px solid #f8f9fa', paddingBottom: '0.8rem', marginBottom: '1.5rem' }}>
        <h3 style={{ margin: 0, color: '#1a1a1a', fontSize: '1.25rem' }}>Módulo de Cotización de Fletes Marítimos</h3>
        <p style={{ margin: '0.3rem 0 0 0', fontSize: '0.9rem', color: '#666' }}>Ingrese los datos de la ruta para calcular tarifas de referencia basadas en el Excel oficial de CINTAC.</p>
      </div>

      {cotizadorError && (
        <div style={{ marginBottom: '1.2rem', padding: '0.8rem', backgroundColor: '#fff5f5', color: '#c53030', border: '1px solid #feb2b2', borderRadius: '4px', fontSize: '0.9rem' }}>
          <strong>Error:</strong> {cotizadorError}
        </div>
      )}

      <form onSubmit={handleCotizarSubmit} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.2rem' }}>
        <label style={{ display: 'flex', flexDirection: 'column', textAlign: 'left', fontSize: '0.9rem', fontWeight: 'bold', color: '#333' }}>
          Puerto de Origen:
          <input 
            type="text" 
            value={puertoOrigen} 
            onChange={(e) => setPuertoOrigen(e.target.value)} 
            required
            placeholder="Ej: Shanghai"
            style={{ padding: '0.6rem', marginTop: '0.4rem', fontWeight: 'normal', border: '1px solid #ccc', borderRadius: '4px', backgroundColor: '#fff', color: '#000' }}
          />
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', textAlign: 'left', fontSize: '0.9rem', fontWeight: 'bold', color: '#333' }}>
          Puerto de Destino:
          <input 
            type="text" 
            value={puertoDestino} 
            onChange={(e) => setPuertoDestino(e.target.value)} 
            required
            placeholder="Ej: San Antonio"
            style={{ padding: '0.6rem', marginTop: '0.4rem', fontWeight: 'normal', border: '1px solid #ccc', borderRadius: '4px', backgroundColor: '#fff', color: '#000' }}
          />
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', textAlign: 'left', fontSize: '0.9rem', fontWeight: 'bold', color: '#333' }}>
          Tipo de Contenedor:
          <select 
            value={tipoContenedor} 
            onChange={(e) => setTipoContenedor(e.target.value)}
            style={{ padding: '0.6rem', marginTop: '0.4rem', fontWeight: 'normal', border: '1px solid #ccc', borderRadius: '4px', background: '#fff', color: '#000' }}
          >
            <option value="20'">20 Pies (20')</option>
            <option value="40'">40 Pies (40')</option>
          </select>
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', textAlign: 'left', fontSize: '0.9rem', fontWeight: 'bold', color: '#333' }}>
          Cantidad de Contenedores:
          <input 
            type="number" 
            value={cantidad} 
            onChange={(e) => setCantidad(e.target.value)} 
            min="1"
            required
            style={{ padding: '0.6rem', marginTop: '0.4rem', fontWeight: 'normal', border: '1px solid #ccc', borderRadius: '4px', backgroundColor: '#fff', color: '#000' }}
          />
        </label>

        <div style={{ gridColumn: 'span 2', marginTop: '0.5rem' }}>
          <button 
            type="submit" 
            disabled={loadingCotizacion}
            style={{ width: '100%', padding: '0.9rem', backgroundColor: '#f37021', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', fontSize: '1rem', transition: 'background 0.2s' }}
          >
            {loadingCotizacion ? 'Consultando Tarifas y Calculando...' : 'Calcular Cotización'}
          </button>
        </div>
      </form>

      {/* RESULTADO DE LA COTIZACIÓN */}
      {resultado && (
        <div style={{ marginTop: '2rem', padding: '1.5rem', background: '#fdfbfb', border: '1px solid #e2e8f0', borderRadius: '6px', borderTop: '4px solid #1a365d' }}>
          <h4 style={{ margin: '0 0 1rem 0', color: '#1a365d', borderBottom: '1px solid #edf2f7', paddingBottom: '0.5rem', fontSize: '1.1rem' }}>
            Resultado de la Cotización
          </h4>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.95rem' }}>
            <div>
              <span style={{ color: '#718096', fontSize: '0.85rem', textTransform: 'uppercase' }}>Tipo de Ruta:</span>
              <p style={{ margin: '0.2rem 0 0 0', fontWeight: 'bold', color: '#2d3748' }}>{resultado.ruta}</p>
            </div>
            <div>
              <span style={{ color: '#718096', fontSize: '0.85rem', textTransform: 'uppercase' }}>Tiempo de Tránsito:</span>
              <p style={{ margin: '0.2rem 0 0 0', fontWeight: 'bold', color: '#2d3748' }}>{resultado.transito_min} a {resultado.transito_max} días</p>
            </div>
            <div>
              <span style={{ color: '#718096', fontSize: '0.85rem', textTransform: 'uppercase' }}>Tarifa Unitaria ({tipoContenedor}):</span>
              <p style={{ margin: '0.2rem 0 0 0', fontWeight: 'bold', color: '#2d3748' }}>{resultado.moneda} {resultado.tarifa_min.toLocaleString()} - {resultado.moneda} {resultado.tarifa_max.toLocaleString()}</p>
            </div>
            <div>
              <span style={{ color: '#718096', fontSize: '0.85rem', textTransform: 'uppercase' }}>Fuente / Referencia:</span>
              <p style={{ margin: '0.2rem 0 0 0', fontWeight: 'bold', color: '#2d3748', fontSize: '0.85rem' }}>{resultado.fuente}</p>
            </div>
          </div>

          {/* BLOQUE DE TOTAL DESTACADO */}
          <div style={{ marginTop: '1.5rem', padding: '1.2rem', background: '#fffaf0', border: '1px solid #feebc8', borderRadius: '6px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: '#c05621', textTransform: 'uppercase', fontWeight: 'bold', letterSpacing: '0.5px' }}>
              Costo Total Estimado ({cantidad} contenedor{cantidad > 1 ? 'es' : ''})
            </span>
            <p style={{ margin: '0.4rem 0 0 0', fontSize: '1.6rem', fontWeight: 'bold', color: '#9c4221' }}>
              {resultado.moneda} {resultado.total_min.toLocaleString()} — {resultado.moneda} {resultado.total_max.toLocaleString()}
            </p>
          </div>
        </div>
      )}
    </div>
  </main>
</div>


)
}

export default App