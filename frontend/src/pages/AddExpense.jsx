import { useEffect, useState } from 'react'
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'
import * as api from '../api'
import { apiErrorMessage } from '../api'

export default function AddExpense() {
  const { groupId, expenseId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const prefill = location.state?.prefill || null
  const isEditing = Boolean(expenseId)

  const [group, setGroup] = useState(null)
  const [people, setPeople] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const [payerId, setPayerId] = useState('')
  const [amount, setAmount] = useState('')
  const [label, setLabel] = useState('')
  const [beneficiaryIds, setBeneficiaryIds] = useState([])
  const [uneven, setUneven] = useState(false)
  const [weights, setWeights] = useState({})
  const [isRecurring, setIsRecurring] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [groupRes, peopleRes] = await Promise.all([api.getGroup(groupId), api.listPeople(groupId)])
        if (cancelled) return
        setGroup(groupRes.data)
        setPeople(peopleRes.data)

        if (isEditing) {
          const expensesRes = await api.listExpenses(groupId)
          const existing = expensesRes.data.find((e) => e.id === expenseId)
          if (existing) {
            setPayerId(existing.payer_id)
            setAmount(String(existing.amount))
            setLabel(existing.label)
            setIsRecurring(existing.is_recurring)
            setBeneficiaryIds(Object.keys(existing.beneficiaries))
            setWeights(existing.beneficiaries)
            setUneven(new Set(Object.values(existing.beneficiaries)).size > 1)
          }
        } else if (prefill) {
          setPayerId(prefill.payer_id)
          setAmount(String(prefill.amount))
          setLabel(prefill.label || '')
          setBeneficiaryIds(prefill.beneficiary_ids)
          const w = {}
          prefill.beneficiary_ids.forEach((id) => (w[id] = 1))
          setWeights(w)
        } else {
          setPayerId(peopleRes.data[0]?.id || '')
          setBeneficiaryIds(peopleRes.data.map((p) => p.id))
          const w = {}
          peopleRes.data.forEach((p) => (w[p.id] = 1))
          setWeights(w)
        }
      } catch (err) {
        setError(apiErrorMessage(err, 'Could not load this group.'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId, expenseId])

  const toggleBeneficiary = (personId) => {
    setBeneficiaryIds((prev) => {
      const next = prev.includes(personId) ? prev.filter((id) => id !== personId) : [...prev, personId]
      if (!weights[personId]) {
        setWeights((w) => ({ ...w, [personId]: 1 }))
      }
      return next
    })
  }

  const setWeight = (personId, value) => {
    setWeights((w) => ({ ...w, [personId]: value }))
  }

  const amountNumber = parseFloat(amount)
  const formError =
    !payerId
      ? 'You must choose a payer.'
      : !amountNumber || amountNumber <= 0
      ? 'The amount must be strictly positive.'
      : beneficiaryIds.length === 0
      ? 'You need at least one beneficiary.'
      : null

  const handleSave = async () => {
    setSaving(true)
    setError('')
    const beneficiaryWeights = {}
    beneficiaryIds.forEach((id) => {
      beneficiaryWeights[id] = uneven ? parseFloat(weights[id]) || 1 : 1
    })
    const payload = {
      payer_id: payerId,
      amount: amountNumber,
      label: label.trim(),
      is_recurring: isRecurring,
      beneficiary_weights: beneficiaryWeights,
    }
    try {
      if (isEditing) {
        await api.updateExpense(groupId, expenseId, payload)
      } else {
        await api.addExpense(groupId, payload)
      }
      navigate(`/groups/${groupId}`)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not save expense.'))
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setSaving(true)
    try {
      await api.deleteExpense(groupId, expenseId)
      navigate(`/groups/${groupId}`)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not delete expense.'))
      setSaving(false)
    }
  }

  if (loading) return <div className="page">Loading…</div>

  return (
    <div className="page">
      <h1>{isEditing ? '✏️ Edit expense' : '➕ New expense'}</h1>
      {prefill && !isEditing && <div className="alert info">Parsed from your sentence — check it over, then save.</div>}

      <label>Who paid?</label>
      <select value={payerId} onChange={(e) => setPayerId(e.target.value)}>
        {people.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      <label>Amount ({group?.currency})</label>
      <input type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />

      <label>Label (optional)</label>
      <input
        type="text"
        placeholder="Groceries, restaurant, gas..."
        value={label}
        onChange={(e) => setLabel(e.target.value)}
      />

      <label>For whom?</label>
      {people.map((p) => (
        <div key={p.id} style={{ margin: '0.25rem 0' }}>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', fontWeight: 400 }}>
            <input
              type="checkbox"
              checked={beneficiaryIds.includes(p.id)}
              onChange={() => toggleBeneficiary(p.id)}
              style={{ width: 'auto' }}
            />
            {p.name}
          </label>
        </div>
      ))}

      <div style={{ marginTop: '0.75rem' }}>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
          <input type="checkbox" checked={uneven} onChange={(e) => setUneven(e.target.checked)} style={{ width: 'auto' }} />
          Split unevenly (e.g. a child counts for half, a double room counts double)
        </label>
      </div>

      {uneven && (
        <>
          <p className="caption">Weight 1 = a normal full share. 0.5 = half a share. 2 = double.</p>
          {beneficiaryIds.map((id) => (
            <div key={id}>
              <label>{people.find((p) => p.id === id)?.name}'s weight</label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                value={weights[id] || 1}
                onChange={(e) => setWeight(id, e.target.value)}
              />
            </div>
          ))}
        </>
      )}

      <div style={{ marginTop: '0.75rem' }}>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="checkbox"
            checked={isRecurring}
            onChange={(e) => setIsRecurring(e.target.checked)}
            style={{ width: 'auto' }}
          />
          🔁 Mark as recurring (e.g. rent, weekly shop) so it can be repeated with one click later
        </label>
      </div>

      {(formError || error) && <div className="alert error">{error || formError}</div>}

      <div className="spacer" />
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <Link to={`/groups/${groupId}`}>
          <button>Cancel</button>
        </Link>
        {isEditing && (
          <button onClick={handleDelete} disabled={saving}>
            Delete
          </button>
        )}
        <button className="primary" onClick={handleSave} disabled={saving || Boolean(formError)}>
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  )
}
