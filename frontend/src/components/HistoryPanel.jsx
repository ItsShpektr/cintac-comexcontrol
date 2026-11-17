import { useEffect, useState } from 'react'
import { Clock3, Download } from 'lucide-react'
import { API_URL, apiFetch, getToken } from '../lib/api'
export default function HistoryPanel() {
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')
  
const [descargandoId, setDescargandoId] = useState(null)

async function descargarExcel(id) {
  setError('')
  setDescargandoId(id)

  try {
    const response = await fetch(
      `${API_URL}/api/history/${id}/excel`,
      {
        headers: {
          Authorization: `Bearer ${getToken()}`
        }
      }
    )

    if (!response.ok) {
      throw new Error('No fue posible descargar la cotización')
    }

    const archivo = await response.blob()
    const url = URL.createObjectURL(archivo)

    const enlace = document.createElement('a')
    enlace.href = url
    enlace.download = `cotizacion_${id}.xlsx`

    document.body.appendChild(enlace)
    enlace.click()
    enlace.remove()

    setTimeout(() => URL.revokeObjectURL(url), 1000)

  } catch (error) {
    setError(error.message)
  } finally {
    setDescargandoId(null)
  }
}

  useEffect(() => {
    apiFetch('/api/history').then(setRows).catch((err) => setError(err.message))
  }, [])

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Trazabilidad</p>
          <h3>Historial reciente</h3>
        </div>
        <Clock3 size={24} />
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {!error && rows.length === 0 && <p className="empty-state">Todavía no hay cotizaciones registradas.</p>}

      {rows.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Usuario</th>
                <th>Ruta</th>
                <th>Contenedor</th>
                <th>Peso</th>
                <th>Versión</th>
                <th>Fecha</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>#{row.id}</td>
                  <td>{row.usuario}</td>
                  <td>{row.ruta}</td>
                  <td>{row.cantidad} × {row.contenedor}</td>
                  <td>{row.peso_toneladas} ton</td>
                  <td>#{row.version_id}</td>
                  <td>{new Date(row.created_at).toLocaleString('es-CL')}</td>
                  <td>
                    <button
                      type="button"
                      disabled={descargandoId === row.id}
                      onClick={() => descargarExcel(row.id)}
                    >
                      <Download size={16} />
                      ? 'Descargando...'
                      : 'Descargar Excel'
                    </button>
                  </td>   
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
