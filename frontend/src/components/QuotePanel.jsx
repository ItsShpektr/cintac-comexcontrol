import { useEffect, useMemo, useState } from 'react'
import { Calculator, Container, FileDown, Route, Ship } from 'lucide-react'
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
    valor_carga_usd: '',
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

  const capacidadContenedor = form.tipo_contenedor === "20'" ? 23 : 25
  const containerCount = useMemo(
    () => (weightInTons > 0 ? Math.ceil(weightInTons / capacidadContenedor) : 0),
    [weightInTons, capacidadContenedor],
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
        valor_carga_usd: form.valor_carga_usd === '' ? null : Number(form.valor_carga_usd),
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

  const downloadReport = () => {
    if (!result) return

    const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    })[character])
    const fecha = new Date().toLocaleString('es-CL')
    const peso = Number(result.peso_toneladas ?? weightInTons)
    const pesoKg = peso * 1000
    const capacidadPorContenedor = result.tipo_contenedor === "20'" ? 23 : 25
    const capacidadTotal = result.cantidad_contenedores * capacidadPorContenedor
    const ocupacionPct = capacidadTotal > 0 ? (peso / capacidadTotal) * 100 : 0
    const formatNumber = (value, maximumFractionDigits = 3) => Number(value).toLocaleString('es-CL', {
      maximumFractionDigits,
    })
    const formatRange = (min, max, currency = 'USD') => min === max
      ? money(min, currency)
      : `${money(min, currency)} – ${money(max, currency)}`
    const formatDays = (min, max) => min === max ? `${min} días` : `${min}–${max} días`
    const filasAlternativas = result.alternativas
      .map((item) => {
        const baseMin = item.transito_base_min_dias ?? Math.max(0, item.transito_min_dias - result.contingencia_dias)
        const baseMax = item.transito_base_max_dias ?? Math.max(0, item.transito_max_dias - result.contingencia_dias)
        const unitMin = item.tarifa_min_usd ?? item.flete_min_usd / result.cantidad_contenedores
        const unitMax = item.tarifa_max_usd ?? item.flete_max_usd / result.cantidad_contenedores
        const tonMin = peso > 0 ? item.flete_min_usd / peso : 0
        const tonMax = peso > 0 ? item.flete_max_usd / peso : 0

        return `
        <tr>
          <td><strong>${escapeHtml(item.tipo_ruta)}</strong></td>
          <td>${formatRange(unitMin, unitMax)}<div class="sub">por contenedor</div></td>
          <td>${formatRange(item.flete_min_usd, item.flete_max_usd)}</td>
          <td><strong>${formatRange(item.total_min_usd, item.total_max_usd)}</strong></td>
          <td>${item.total_min_clp != null && item.total_max_clp != null
            ? formatRange(item.total_min_clp, item.total_max_clp, 'CLP')
            : 'No aplicado'}</td>
          <td>${formatRange(tonMin, tonMax)}/ton</td>
          <td><strong>${formatDays(item.transito_min_dias, item.transito_max_dias)}</strong>
            ${result.contingencia_dias > 0 ? `<div class="sub">${formatDays(baseMin, baseMax)} base + ${escapeHtml(result.contingencia_dias)} día(s) contingencia</div>` : ''}
          </td>
        </tr>`
      })
      .join('')

    const tipoCambio = result.tipo_cambio_clp_usd
    const valorCarga = Number(result.valor_carga_usd || 0)
    const win = window.open('', '_blank', 'width=1100,height=850')
    if (!win) {
      setError('Permite las ventanas emergentes en tu navegador para descargar el informe.')
      return
    }

    win.document.write(`
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <meta charset="UTF-8" />
        <title>Informe Cotización #${escapeHtml(result.cotizacion_id)}</title>
        <style>
          body { font-family: Arial, sans-serif; color: #0f172a; padding: 32px; max-width: 1100px; margin: auto; }
          .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 20px; }
          .header h1 { margin: 0; font-size: 20px; }
          .header p { margin: 4px 0 0; font-size: 13px; color: #475569; }
          .meta { text-align: right; font-size: 12px; color: #475569; line-height: 1.5; }
          .section-title { font-size: 12px; text-transform: uppercase; letter-spacing: .05em; color: #475569; margin: 18px 0 8px; font-weight: bold; }
          .summary { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 20px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 14px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 13px; }
          .formula-box { background: #f1f5f9; border-left: 4px solid #334155; padding: 10px 14px; font-size: 12.5px; margin-bottom: 18px; line-height: 1.6; }
          table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px; }
          th, td { border: 1px solid #cbd5e1; padding: 8px; text-align: left; vertical-align: top; }
          th { background: #f1f5f9; color: #334155; }
          .sub { font-size: 10.5px; color: #64748b; margin-top: 3px; }
          .note { font-size: 12px; color: #475569; background: #f8fafc; padding: 12px; border-left: 4px solid #0f172a; }
          @media print { body { padding: 0; } }
        </style>
      </head>
      <body>
        <div class="header">
          <div><h1>CINTAC ComexControl</h1><p>Informe Técnico y Referencial de Cotización Marítima</p></div>
          <div class="meta"><div><strong>Cotización #${escapeHtml(result.cotizacion_id)}</strong></div><div>Versión tarifario: #${escapeHtml(result.version_id ?? '—')}</div><div>Emitido: ${escapeHtml(fecha)}</div></div>
        </div>
        <div class="section-title">1. Parámetros de la operación</div>
        <div class="summary">
          <div><strong>Ruta:</strong> ${escapeHtml(result.puerto_origen)} → ${escapeHtml(result.puerto_destino)}</div>
          <div><strong>Equipamiento:</strong> ${escapeHtml(result.cantidad_contenedores)} × contenedor ${escapeHtml(result.tipo_contenedor)} (máx. ${capacidadPorContenedor} ton c/u)</div>
          <div><strong>Peso de carga:</strong> ${formatNumber(peso)} ton (${formatNumber(pesoKg, 0)} kg)</div>
          <div><strong>Contingencia:</strong> ${escapeHtml(result.contingencia_dias)} día(s)</div>
          <div><strong>Valor declarado de carga:</strong> ${valorCarga > 0 ? money(valorCarga) : 'No informado (US$0)'}</div>
          <div><strong>Tipo de cambio aplicado:</strong> ${tipoCambio ? `${money(tipoCambio, 'CLP')} / USD` : 'No aplicado'}</div>
        </div>
        <div class="section-title">2. Trazabilidad del cubicaje y fórmulas</div>
        <div class="formula-box">
          <div><strong>Contenedores requeridos:</strong> techo(${formatNumber(peso)} ton ÷ ${capacidadPorContenedor} ton/cont.) = ${escapeHtml(result.cantidad_contenedores)} contenedor(es).</div>
          <div><strong>Capacidad total:</strong> ${formatNumber(capacidadTotal)} ton. <strong>Ocupación estimada:</strong> ${formatNumber(ocupacionPct, 1)}% (${formatNumber(peso)} ÷ ${formatNumber(capacidadTotal)} ton).</div>
          <div><strong>Total referencial USD:</strong> flete (${result.cantidad_contenedores} × tarifa unitaria) + valor declarado de carga${valorCarga > 0 ? ` (${money(valorCarga)})` : ' (US$0)'}; el valor de carga es un dato declarado, no un cobro de flete.</div>
          ${tipoCambio ? `<div><strong>Conversión CLP:</strong> total referencial USD × ${money(tipoCambio, 'CLP')} por USD.</div>` : ''}
        </div>
        <table>
          <thead><tr><th>Alternativa</th><th>Tarifa unitaria USD/cont.</th><th>Subtotal flete USD</th><th>Total referencial USD*</th><th>Total referencial CLP*</th><th>Flete USD/ton</th><th>Tránsito estimado</th></tr></thead>
          <tbody>${filasAlternativas}</tbody>
        </table>
        <div class="note"><strong>Nota:</strong> Valores correspondientes a <strong>flete internacional sin IVA</strong>. *El total referencial suma el flete y, cuando se informa, el valor declarado de la carga; no representa impuestos ni otros costos locales. Las alternativas se presentan para comparación y el sistema no decide automáticamente cuál es la mejor.</div>
        <script>window.onload = function () { window.print(); };</script>
      </body>
      </html>
    `)
    win.document.close()
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
            <p className="muted">El sistema estima automáticamente los contenedores según su capacidad: 23 ton para 20 pies y 25 ton para 40 pies.</p>
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
                : `Máximo ${capacidadContenedor} ton por contenedor`}
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
            <span>Valor declarado de la carga (USD, opcional)</span>
            <input type="number" min="0" max="10000000" step="0.01" value={form.valor_carga_usd}
              onChange={(e) => update('valor_carga_usd', e.target.value)} placeholder="Se puede dejar en blanco" />
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
          <div className="result-summary" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <div><Route size={20} /><span>{result.puerto_origen} → {result.puerto_destino}</span></div>
              <div><Container size={20} /><span>{result.cantidad_contenedores} contenedor(es) de {result.tipo_contenedor}</span></div>
            </div>
            <button type="button" className="button" onClick={downloadReport}>
              <FileDown size={18} /> Descargar informe
            </button>
          </div>

          <div className="alternatives-grid">
            {result.alternativas.map((item) => (
              <article className="alternative-card" key={item.tarifa_id}>
                <div className="alternative-top">
                  <span className="route-type">{item.tipo_ruta}</span>
                </div>
                <div className="result-meta">
                  <span>Flete marítimo ({result.cantidad_contenedores} × {result.tipo_contenedor}): {money(item.flete_min_usd)} – {money(item.flete_max_usd)}</span>
                  {result.valor_carga_usd > 0 && (
                    <span>Valor declarado de la carga: {money(result.valor_carga_usd)}</span>
                  )}
                </div>
                <div className="price-range">Total referencial (flete + valor declarado): {money(item.total_min_usd)} – {money(item.total_max_usd)}</div>
                {item.total_min_clp != null && item.total_max_clp != null && (
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
            Cotización #{result.cotizacion_id}. Valores correspondientes a flete internacional sin IVA. Las alternativas se presentan para comparación; el sistema no decide automáticamente cuál es la mejor.
          </p>
        </section>
      )}
    </div>
  )
}
