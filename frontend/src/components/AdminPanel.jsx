import { useEffect, useRef, useState } from 'react'
import { FileUp, ShieldCheck, UserPlus } from 'lucide-react'
import { apiFetch } from '../lib/api'

export default function AdminPanel() {
  const [versions, setVersions] = useState([])
  const [users, setUsers] = useState([])
  const [auditRows, setAuditRows] = useState([])
  const [file, setFile] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const fileInputRef = useRef(null)
  const [userForm, setUserForm] = useState({
    nombre: '',
    email: '',
    password: '',
    rol: 'Analista COMEX',
  })

  const refresh = async () => {
    const [versionRows, userRows, auditData] = await Promise.all([
      apiFetch('/api/admin/tariff-versions'),
      apiFetch('/api/admin/users'),
      apiFetch('/api/admin/audit'),
    ])
    setVersions(versionRows)
    setUsers(userRows)
    setAuditRows(auditData)
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message))
  }, [])

  const upload = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')

    if (!file) {
      setError('Seleccione un archivo .xlsx')
      return
    }

    const body = new FormData()
    body.append('file', file)

    try {
      const data = await apiFetch('/api/admin/tariff-versions', { method: 'POST', body })
      setMessage(data.mensaje)
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      await refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  const activate = async (id) => {
    setError('')
    setMessage('')
    try {
      const data = await apiFetch(`/api/admin/tariff-versions/${id}/activate`, { method: 'POST' })
      setMessage(data.mensaje)
      await refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  const createUser = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')

    try {
      await apiFetch('/api/admin/users', {
        method: 'POST',
        body: JSON.stringify(userForm),
      })
      setMessage('Usuario creado correctamente')
      setUserForm({ nombre: '', email: '', password: '', rol: 'Analista COMEX' })
      await refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="stack-lg">
      {error && <div className="alert alert-error">{error}</div>}
      {message && <div className="alert alert-success">{message}</div>}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Control de datos</p>
            <h3>Versiones de tarifas</h3>
          </div>
          <FileUp />
        </div>

        <form className="upload-row" onSubmit={upload}>
          <input ref={fileInputRef} type="file" accept=".xlsx" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <button className="button button-primary" type="submit">Validar y cargar</button>
        </form>

        <p className="footnote">
          Una carga válida queda PENDIENTE. Solo se utiliza cuando un administrador la activa explícitamente.
        </p>

        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Versión</th><th>Archivo</th><th>Estado</th><th>Validación</th><th>Acción</th></tr>
            </thead>
            <tbody>
              {versions.map((version) => (
                <tr key={version.id}>
                  <td>#{version.id}</td>
                  <td>{version.archivo}</td>
                  <td><span className={`badge badge-${version.estado.toLowerCase()}`}>{version.estado}</span></td>
                  <td>{version.filas_validas} válidas / {version.filas_invalidas} inválidas</td>
                  <td>
                    {version.estado !== 'ACTIVA' && (
                      <button className="button button-small" type="button" onClick={() => activate(version.id)}>Activar</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel admin-grid">
        <div>
          <div className="panel-heading">
            <div><p className="eyebrow">RBAC</p><h3>Crear usuario</h3></div>
            <UserPlus />
          </div>

          <form className="stack-md" onSubmit={createUser}>
            <label className="field">
              <span>Nombre</span>
              <input required minLength="2" value={userForm.nombre} onChange={(e) => setUserForm({ ...userForm, nombre: e.target.value })} />
            </label>
            <label className="field">
              <span>Correo</span>
              <input required type="email" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} />
            </label>
            <label className="field">
              <span>Contraseña temporal segura</span>
              <input required type="password" minLength="10" maxLength="72" value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} />
            </label>
            <label className="field">
              <span>Rol</span>
              <select value={userForm.rol} onChange={(e) => setUserForm({ ...userForm, rol: e.target.value })}>
                <option>Analista COMEX</option>
                <option>Jefatura COMEX</option>
                <option>Administrador</option>
              </select>
            </label>
            <button className="button button-primary" type="submit">Crear usuario</button>
          </form>
        </div>

        <div>
          <p className="eyebrow">Usuarios existentes</p>
          <h3>Accesos registrados</h3>
          <div className="user-list">
            {users.map((user) => (
              <div className="user-row" key={user.id}>
                <div><strong>{user.nombre}</strong><span>{user.email}</span></div>
                <span className="status-pill">{user.rol}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><p className="eyebrow">Auditoría</p><h3>Acciones sensibles recientes</h3></div>
          <ShieldCheck />
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Recurso</th><th>Detalle</th></tr>
            </thead>
            <tbody>
              {auditRows.map((row) => (
                <tr key={row.id}>
                  <td>{new Date(row.created_at).toLocaleString('es-CL')}</td>
                  <td>{row.usuario}</td>
                  <td>{row.accion}</td>
                  <td>{row.recurso}{row.recurso_id ? ` #${row.recurso_id}` : ''}</td>
                  <td>{row.detalle || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
