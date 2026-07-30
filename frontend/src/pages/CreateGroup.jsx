import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import * as api from '../api'
import { apiErrorMessage } from '../api'

const CURRENCIES = ['EUR', 'USD', 'GBP', 'CHF', 'JPY', 'CAD', 'AUD']

export default function CreateGroup() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [currency, setCurrency] = useState('EUR')
  const [people, setPeople] = useState([])
  const [personInput, setPersonInput] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const normalized = (s) => s.trim().toLowerCase()

  const handleAddPerson = (e) => {
    e.preventDefault()
    const candidate = personInput.trim()
    if (!candidate) return
    if (people.some((p) => normalized(p) === normalized(candidate))) {
      setError(`'${candidate}' is already in the group. Distinguish first names (e.g. Karim B.).`)
      return
    }
    setError('')
    setPeople([...people, candidate])
    setPersonInput('')
  }

  const handleRemovePerson = (index) => {
    setPeople(people.filter((_, i) => i !== index))
  }

  const canCreate = name.trim().length > 0 && people.length >= 2

  const handleCreate = async () => {
    setError('')
    setLoading(true)
    try {
      const res = await api.createGroup({ name: name.trim(), currency })
      const groupId = res.data.id
      // Add each person sequentially - simplest, and matches the tested backend
      // behaviour of one person per request.
      for (const personName of people) {
        await api.addPerson(groupId, { name: personName })
      }
      navigate(`/groups/${groupId}`)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not create group.'))
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <Link to="/">
        <button>← Back</button>
      </Link>
      <h1>➕ New group</h1>

      <label>Group name</label>
      <input type="text" placeholder="Etretat Weekend" value={name} onChange={(e) => setName(e.target.value)} />

      <label>Currency</label>
      <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
        {CURRENCIES.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      <div className="spacer" />
      <strong>Participants</strong>
      <p className="caption" style={{ margin: '0.25rem 0 0.75rem' }}>
        Add at least 2 people by their first name.
      </p>

      <form onSubmit={handleAddPerson} className="row">
        <input
          type="text"
          placeholder="First name"
          value={personInput}
          onChange={(e) => setPersonInput(e.target.value)}
        />
        <button type="submit">Add</button>
      </form>

      {people.map((p, i) => (
        <div className="row" key={i} style={{ marginTop: '0.5rem' }}>
          <span>• {p}</span>
          <button onClick={() => handleRemovePerson(i)}>✕</button>
        </div>
      ))}

      {error && <div className="alert error">{error}</div>}
      {!error && people.length < 2 && (
        <p className="caption">⚠️ A group must contain at least two people.</p>
      )}

      <div className="spacer" />
      <button className="primary" disabled={!canCreate || loading} onClick={handleCreate}>
        {loading ? 'Creating…' : 'Create group'}
      </button>
    </div>
  )
}
