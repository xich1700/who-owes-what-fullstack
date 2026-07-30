import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import * as api from '../api'
import { apiErrorMessage } from '../api'
import { useAuth } from '../context/AuthContext'

export default function GroupsList() {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const { logout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false
    api
      .listGroups()
      .then((res) => {
        if (!cancelled) setGroups(res.data)
      })
      .catch((err) => {
        if (!cancelled) setError(apiErrorMessage(err, 'Could not load your groups.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="page">
      <div className="row">
        <div>
          <h1>💸 Who owes what?</h1>
        </div>
        <button onClick={handleLogout}>Log out</button>
      </div>

      {loading && <p className="caption">Loading…</p>}
      {error && <div className="alert error">{error}</div>}

      {!loading && !error && groups.length === 0 && (
        <div className="alert info">No groups yet. Create your first group to get started.</div>
      )}

      {!loading &&
        groups.map((g) => (
          <div className="card row" key={g.id}>
            <div>
              <strong>{g.name}</strong>
              <div className="caption" style={{ margin: 0 }}>
                {g.currency}
                {g.closed && ' · 🔒 closed'}
              </div>
            </div>
            <Link to={`/groups/${g.id}`}>
              <button>Open</button>
            </Link>
          </div>
        ))}

      <div className="spacer" />
      <Link to="/groups/new">
        <button className="primary">➕ New group</button>
      </Link>
    </div>
  )
}
