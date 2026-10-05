import { useEffect, useMemo, useState } from 'react'
import { Calculator, Container, Route, Ship } from 'lucide-react'
import { apiFetch } from '../lib/api'

function money(value, currency = 'USD') {
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency,
    maximumFractionDigits: currency === 'CLP' ? 0 : 2,
  }).format(value)
}

export default function QuotePanel() {
  const [catalog, setCatalog] = useState({ version_id: null, origenes: [], destinos: [], rutas: [] })
  const [form, setForm] = useState({
    puerto_origen: '',
    puerto_destino: '',
    tipo_contenedor: "20'",
    peso: '',
    unidad_peso: 'ton',
    contingencia_dias: 0,
    tipo_cambio_clp_usd: '',
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    apiFetch('/api/routes')
      .then((data) => setCatalog(data))
      .catch((err) => setError(err.message))
  }, [])

  const destinationsForOrigin = useMemo(() => {
    if (!form.puerto_origen) return []
    return [...new Set(
      catalog.rutas
        .filter((route) => route.origen === form.puerto_origen)
        .map((route) => route.destino),
    )].sort()
  }, [catalog.rutas, form.puerto_origen])

  const weightInTons = useMemo(() => {
    const value = Number(form.peso)
    if (!Number.isFinite(value) || value <= 0) return 0
    return form.unidad_peso === 'kg' ? value / 1000 : value
  }, [form.peso, form.unidad_peso])

  const containerCount = useMemo(
    () => (weightInTons > 0 ? Math.ceil(weightInTons / 25) : 0),
    [weightInTons],
  )

  const update = (key, value) => {
    setForm((current) => {
      const next = { ...current, [key]: value }
      if (key === 'puerto_origen') next.puerto_destino = ''
      return next
    })
  }

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const payload = {
        puerto_origen: form.puerto_origen,
        puerto_destino: form.puerto_destino,
        tipo_contenedor: form.tipo_contenedor,
        peso_toneladas: weightInTons,
        contingencia_dias: Number(form.contingencia_dias || 0),
        tipo_cambio_clp_usd: form.tipo_cambio_clp_usd ? Number(form.tipo_cambio_clp_usd) : null,
      }

      setResult(await apiFetch('/api/cotizar', {
        method: 'POST',
        body: JSON.stringify(payload),
      }))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="stack-lg">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Cotizador marítimo</p>
          <h2>Evaluación de flete internacional</h2>
          <p className="muted">La cotización usa exclusivamente la versión activa y validada de tarifas.</p>
        </div>
        <Ship size={44} strokeWidth={1.5} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>Nueva cotización</h3>
            <p className="muted">El sistema calcula automáticamente un contenedor por cada 25 toneladas.</p>
          </div>
          <span className="status-pill">Versión #{catalog.version_id || '—'}</span>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form className="quote-grid" onSubmit={submit}>
          <label className="field">
            <span>Puerto de origen</span>
            <select value={form.puerto_origen} onChange={(e) => update('puerto_origen', e.target.value)} required>
              <option value="">Seleccione un origen</option>
              {catalog.origenes.map((origin) => <option key={origin}>{origin}</option>)}
            </select>
          </label>

          <label className="field">
            <span>Puerto de destino</span>
            <select
              value={form.puerto_destino}
              onChange={(e) => update('puerto_destino', e.target.value)}
              required
              disabled={!form.puerto_origen}
            >
              <option value="">Seleccione un destino</option>
              {destinationsForOrigin.map((destination) => <option key={destination}>{destination}</option>)}
            </select>
          </label>

          <label className="field">
            <span>Tipo de contenedor</span>
            <select value={form.tipo_contenedor} onChange={(e) => update('tipo_contenedor', e.target.value)}>
              <option value="20'">20 pies</option>
              <option value="40'">40 pies</option>
            </select>
          </label>

          <label className="field">
            <span>Peso total de carga</span>
            <div className="inline-inputs">
              <input
                type="number"
                min="0.01"
                max={form.unidad_peso === 'kg' ? '10000000' : '10000'}
                step="0.01"
                value={form.peso}
                onChange={(e) => update('peso', e.target.value)}
                required
                placeholder={form.unidad_peso === 'kg' ? 'Ej. 48500' : 'Ej. 48.5'}
              />
              <select value={form.unidad_peso} onChange={(e) => update('unidad_peso', e.target.value)}>
                <option value="ton">ton</option>
                <option value="kg">kg</option>
              </select>
            </div>
            <small>
              {weightInTons > 0
                ? `${weightInTons.toFixed(3)} ton · ${containerCount} contenedor(es) estimados`
                : 'Máximo 25 ton por contenedor'}
            </small>
          </label>

          <label className="field">
            <span>Contingencia (días)</span>
            <input
              type="number"
              min="0"
              max="30"
              value={form.contingencia_dias}
              onChange={(e) => update('contingencia_dias', e.target.value)}
            />
          </label>

          <label className="field">
            <span>Tipo de cambio CLP por USD (opcional)</span>
            <input
              type="number"
              min="1"
              step="0.01"
              value={form.tipo_cambio_clp_usd}
              onChange={(e) => update('tipo_cambio_clp_usd', e.target.value)}
              placeholder="Valor validado por COMEX"
            />
            <small>El sistema no inventa ni descarga automáticamente un tipo de cambio.</small>
          </label>

          <button className="button button-primary quote-submit" type="submit" disabled={loading || !catalog.version_id}>
            <Calculator size={18} /> {loading ? 'Calculando…' : 'Calcular cotización'}
          </button>
        </form>
      </section>

      {result && (
        <section className="panel">
          <div className="result-summary">
            <div><Route size={20} /><span>{result.puerto_origen} → {result.puerto_destino}</span></div>
            <div><Container size={20} /><span>{result.cantidad_contenedores} contenedor(es) de {result.tipo_contenedor}</span></div>
          </div>

          <div className="alternatives-grid">
            {result.alternativas.map((item) => (
              <article className="alternative-card" key={item.tarifa_id}>
                <div className="alternative-top">
                  <span className="route-type">{item.tipo_ruta}</span>
                  <span className="source">{item.fuente}</span>
                </div>
                <div className="price-range">{money(item.total_min_usd)} – {money(item.total_max_usd)}</div>
                {item.total_min_clp != null && (
                  <div className="clp-range">
                    Aprox. {money(item.total_min_clp, 'CLP')} – {money(item.total_max_clp, 'CLP')}
                  </div>
                )}
                <div className="result-meta">
                  <span>Tránsito: {item.transito_min_dias}–{item.transito_max_dias} días</span>
                  {result.contingencia_dias > 0 && <span>Incluye {result.contingencia_dias} día(s) de contingencia</span>}
                </div>
              </article>
            ))}
          </div>

          <p className="footnote">
            Cotización #{result.cotizacion_id}. Las alternativas se presentan para comparación; el sistema no decide automáticamente cuál es la mejor.
          </p>
        </section>
      )}
    </div>
  )
}
