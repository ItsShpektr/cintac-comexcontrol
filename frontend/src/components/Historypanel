import { useEffect, useState } from 'react'
import { Clock3 } from 'lucide-react'
import { apiFetch } from '../lib/api'

export default function HistoryPanel() {
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')

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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
