import { useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

export default function TarifarioPanel() {
  const [tarifas, setTarifas] = useState([])
  const [archivo, setArchivo] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    apiFetch('/api/tariffs/active')
      .then((data) => {
        setTarifas(data.tarifas)
        setArchivo(data.archivo || '')
      })
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false))
  }, [])

  const resultados = tarifas.filter((tarifa) => {
    const texto = `${tarifa.origen} ${tarifa.destino} ${tarifa.pais}`
    return texto.toLowerCase().includes(busqueda.toLowerCase())
  })

  const usd = (valor) =>
    Number(valor).toLocaleString('es-CL', {
      style: 'currency',
      currency: 'USD'
    })

  return (
    <section className="panel tarifario-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Consulta de datos</p>
          <h3>Tarifario marítimo</h3>
          <p className="muted">
            Archivo activo: {archivo || 'Ninguno'}
          </p>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {cargando && <p>Cargando tarifas...</p>}

      {!cargando && !error && (
        <>
          <label className="field">
            <span>Buscar puerto o país</span>
            <input
              type="text"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Ej. Shanghai, San Antonio, China"
            />
          </label>

          <p className="muted">
            Mostrando {resultados.length} de {tarifas.length} rutas
          </p>

          <div className="table-wrap">
            <table className="tarifario-table">
              <thead>
                <tr>
                  <th>Origen</th>
                  <th>Destino</th>
                  <th>Tipo</th>
                  <th>20' mín.</th>
                  <th>20' máx.</th>
                  <th>40' mín.</th>
                  <th>40' máx.</th>
                  <th>Tránsito</th>
                </tr>
              </thead>

              <tbody>
                {resultados.map((t) => (
                  <tr key={t.clave + t.tipo_ruta}>
                    <td>{t.origen}</td>
                    <td>{t.destino}</td>
                    <td>{t.tipo_ruta}</td>
                    <td>{usd(t.tarifa_20_min)}</td>
                    <td>{usd(t.tarifa_20_max)}</td>
                    <td>{usd(t.tarifa_40_min)}</td>
                    <td>{usd(t.tarifa_40_max)}</td>
                    <td>{t.transito_min}–{t.transito_max} días</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {resultados.length === 0 && (
            <p className="empty-state">
              No hay tarifas que coincidan con la búsqueda.
            </p>
          )}
        </>
      )}
    </section>
  )
}
