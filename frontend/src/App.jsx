import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [mensaje, setMensaje] = useState('Cargando...')

  useEffect(() => {
    // Petición a la API desplegada en Render
    fetch('https://cintac-comexcontrol.onrender.com/')
      .then((res) => res.json())
      .then((data) => setMensaje(data.message))
      .catch((err) => {
        console.error(err)
        setMensaje('Error al conectar con la API')
      })
  }, [])

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif', textAlign: 'center' }}>
      <h1>CINTAC - ComexControl</h1>
      <p>Estado de la API: <strong>{mensaje}</strong></p>
    </div>
  )
}

export default App