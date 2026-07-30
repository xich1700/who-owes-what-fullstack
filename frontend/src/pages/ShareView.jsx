import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as api from '../api'
import { apiErrorMessage } from '../api'

export default function ShareView() {
  const { token } = useParams()
  const navigate = useNavigate()

  const [group, setGroup] = useState(null)
  const [people, setPeople] = useState([])
  const [expenses, setExpenses] = useState([])
  const [totals, setTotals] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('expenses')

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [groupRes, peopleRes, expensesRes, totalsRes] = await Promise.all([
          api.getSharedGroup(token),
          api.getSharedPeople(token),
          api.getSharedExpenses(token),
          api.getSharedTotals(token),
        ])
        if (cancelled) return
        setGroup(groupRes.data)
        setPeople(peopleRes.data)
        setExpenses(expensesRes.data)
        setTotals(totalsRes.data)
      } catch (err) {
        if (!cancelled) setError(apiErrorMessage(err, "This link doesn't match any group."))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [token])

  if (loading) return <div className="page">Loading…</div>

  if (error || !group) {
    return (
      <div className="page">
        <h1>💸 Who owes what?</h1>
        <div className="alert error">{error || "This link doesn't match any group."}</div>
      </div>
    )
  }

  const currency = group.currency
  const nameById = Object.fromEntries(people.map((p) => [p.id, p.name]))

  return (
    <div className="page">
      <h1>
        💸 {group.name} {group.closed && '🔒'}
      </h1>
      <p className="caption">
        {group.closed ? '🔒 Closed group · ' : '👀 Read-only view · '}
        {people.map((p) => p.name).join(', ') || 'no one yet'} · {currency}
      </p>

      <div className="tabs">
        <button className={`tab ${tab === 'expenses' ? 'active' : ''}`} onClick={() => setTab('expenses')}>
          📋 Expenses
        </button>
        <button className={`tab ${tab === 'totals' ? 'active' : ''}`} onClick={() => setTab('totals')}>
          🧮 Totals
        </button>
        <button className={`tab ${tab === 'settle' ? 'active' : ''}`} onClick={() => setTab('settle')}>
          🤝 Settle up
        </button>
      </div>

      {tab === 'expenses' && (
        <div>
          {expenses.length === 0 && <div className="alert info">No expenses recorded yet.</div>}
          {expenses.map((exp) => {
            const weights = Object.values(exp.beneficiaries)
            const uneven = new Set(weights).size > 1
            const allPeople = people.every((p) => exp.beneficiaries[p.id] !== undefined)
            const benefDesc =
              allPeople && !uneven
                ? 'everyone, equally'
                : Object.entries(exp.beneficiaries)
                    .map(([pid, w]) => `${nameById[pid] || '?'}${uneven ? ` (×${w})` : ''}`)
                    .join(', ')
            return (
              <div className="card" key={exp.id}>
                <strong>
                  {exp.label || '(no label)'} {exp.is_recurring && '🔁'}
                </strong>{' '}
                — {exp.amount.toFixed(2)} {currency}
                <div className="caption" style={{ margin: 0 }}>
                  Paid by {nameById[exp.payer_id] || '?'} · for {benefDesc}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {tab === 'totals' && totals && (
        <div>
          <div className="card">
            <div className="caption" style={{ margin: 0 }}>
              Total spent by the group
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>
              {totals.total_spent.toFixed(2)} {currency}
            </div>
          </div>
          {totals.balances.map((b) => (
            <div className="card" key={b.person_id}>
              <strong>{b.name}</strong> — paid {b.paid.toFixed(2)} {currency} · share is {b.share.toFixed(2)}{' '}
              {currency}
              <div>
                {b.outstanding > 0.005 && `🟢 Is owed ${b.outstanding.toFixed(2)} ${currency}`}
                {b.outstanding < -0.005 && `🔴 Owes ${Math.abs(b.outstanding).toFixed(2)} ${currency}`}
                {Math.abs(b.outstanding) <= 0.005 && '⚪ Settled up'}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'settle' && totals && (
        <div>
          {totals.settlement_plan.length === 0 && <div className="alert success">Everyone is settled up ✅</div>}
          {totals.settlement_plan.map((t, i) => (
            <div className="card" key={i}>
              <strong>{t.from_name}</strong> gives <strong>{t.to_name}</strong> {t.amount.toFixed(2)} {currency}
            </div>
          ))}
        </div>
      )}

      <div className="spacer" />
      <button onClick={() => navigate('/')}>Manage your own groups</button>
    </div>
  )
}
