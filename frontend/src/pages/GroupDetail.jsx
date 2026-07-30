import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import * as api from '../api'
import { apiErrorMessage } from '../api'

export default function GroupDetail() {
  const { groupId } = useParams()
  const navigate = useNavigate()

  const [group, setGroup] = useState(null)
  const [people, setPeople] = useState([])
  const [expenses, setExpenses] = useState([])
  const [repayments, setRepayments] = useState([])
  const [totals, setTotals] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('expenses')

  const nameById = Object.fromEntries(people.map((p) => [p.id, p.name]))

  const loadAll = useCallback(async () => {
    setError('')
    try {
      const [groupRes, peopleRes, expensesRes, repaymentsRes, totalsRes] = await Promise.all([
        api.getGroup(groupId),
        api.listPeople(groupId),
        api.listExpenses(groupId),
        api.listRepayments(groupId),
        api.getTotals(groupId),
      ])
      setGroup(groupRes.data)
      setPeople(peopleRes.data)
      setExpenses(expensesRes.data)
      setRepayments(repaymentsRes.data)
      setTotals(totalsRes.data)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not load this group.'))
    } finally {
      setLoading(false)
    }
  }, [groupId])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  if (loading) return <div className="page">Loading…</div>
  if (error) {
    return (
      <div className="page">
        <div className="alert error">{error}</div>
        <Link to="/">
          <button>← Back to home</button>
        </Link>
      </div>
    )
  }
  if (!group) return null

  const isClosed = group.closed

  return (
    <div className="page">
      <div className="row">
        <div>
          <h1>
            {group.name} {isClosed && '🔒'}
          </h1>
          <p className="caption" style={{ margin: 0 }}>
            {people.map((p) => p.name).join(', ') || 'No one in this group yet.'} · {group.currency}
          </p>
        </div>
        <Link to="/">
          <button>← Groups</button>
        </Link>
      </div>

      {isClosed && (
        <div className="alert info">
          This group is closed. Everyone is settled up, and nothing can be changed anymore — it's still fully
          viewable, including via the share link.
        </div>
      )}

      <ShareLinkBox shareToken={group.share_token} />

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
        <button className={`tab ${tab === 'people' ? 'active' : ''}`} onClick={() => setTab('people')}>
          👥 People
        </button>
      </div>

      {tab === 'expenses' && (
        <ExpensesTab
          groupId={groupId}
          people={people}
          expenses={expenses}
          nameById={nameById}
          currency={group.currency}
          isClosed={isClosed}
          onChanged={loadAll}
        />
      )}
      {tab === 'totals' && (
        <TotalsTab group={group} totals={totals} />
      )}
      {tab === 'settle' && (
        <SettleTab
          groupId={groupId}
          people={people}
          repayments={repayments}
          totals={totals}
          currency={group.currency}
          isClosed={isClosed}
          onChanged={loadAll}
          onClosed={() => navigate(0)}
        />
      )}
      {tab === 'people' && (
        <PeopleTab groupId={groupId} people={people} isClosed={isClosed} onChanged={loadAll} />
      )}

      {!isClosed && <DeleteGroupBox groupId={groupId} groupName={group.name} />}
    </div>
  )
}

// =========================================================
// Share link box
// =========================================================
function ShareLinkBox({ shareToken }) {
  const [open, setOpen] = useState(false)
  const shareUrl = `${window.location.origin}/share/${shareToken}`

  return (
    <div className="card">
      <button onClick={() => setOpen(!open)} style={{ width: '100%', textAlign: 'left' }}>
        🔗 Share this group (view-only, no account needed) {open ? '▲' : '▼'}
      </button>
      {open && (
        <>
          <div className="spacer" />
          <input type="text" readOnly value={shareUrl} onFocus={(e) => e.target.select()} />
          <p className="caption">
            Send this link to the group. They'll see live expenses, balances and the settlement plan, with no
            login and no edit access.
          </p>
        </>
      )}
    </div>
  )
}

// =========================================================
// Expenses tab
// =========================================================
function ExpensesTab({ groupId, people, expenses, nameById, currency, isClosed, onChanged }) {
  const navigate = useNavigate()
  const [nlText, setNlText] = useState('')
  const [nlError, setNlError] = useState('')
  const [nlOpen, setNlOpen] = useState(false)

  const [receiptOpen, setReceiptOpen] = useState(false)
  const [receiptFile, setReceiptFile] = useState(null)
  const [receiptApiKey, setReceiptApiKey] = useState('')
  const [receiptError, setReceiptError] = useState('')
  const [receiptScanning, setReceiptScanning] = useState(false)

  const handleScanReceipt = async () => {
    setReceiptError('')
    if (!receiptFile) {
      setReceiptError('Upload a photo first.')
      return
    }
    if (!receiptApiKey.trim()) {
      setReceiptError('Enter your Anthropic API key.')
      return
    }
    setReceiptScanning(true)
    try {
      const res = await api.scanReceipt(groupId, receiptFile, receiptApiKey.trim())
      const prefill = {
        ok: true,
        payer_id: people[0]?.id,
        payer_name: people[0]?.name,
        amount: res.data.amount,
        label: res.data.label,
        beneficiary_ids: people.map((p) => p.id),
      }
      navigate(`/groups/${groupId}/expenses/new`, { state: { prefill } })
    } catch (err) {
      setReceiptError(apiErrorMessage(err, 'Could not read this receipt.'))
    } finally {
      setReceiptScanning(false)
    }
  }

  const handleParse = async () => {
    setNlError('')
    try {
      const res = await api.parseExpense(groupId, nlText)
      if (res.data.ok) {
        navigate(`/groups/${groupId}/expenses/new`, { state: { prefill: res.data } })
      } else {
        setNlError(res.data.error)
      }
    } catch (err) {
      setNlError(apiErrorMessage(err, 'Could not parse that sentence.'))
    }
  }

  const handleRepeat = async (expenseId) => {
    await api.repeatExpense(groupId, expenseId)
    onChanged()
  }

  const handleDelete = async (expenseId) => {
    await api.deleteExpense(groupId, expenseId)
    onChanged()
  }

  const describeBeneficiaries = (exp) => {
    const weights = Object.values(exp.beneficiaries)
    const uneven = new Set(weights).size > 1
    const allPeople = people.every((p) => exp.beneficiaries[p.id] !== undefined)
    if (allPeople && !uneven) return 'everyone, equally'
    return Object.entries(exp.beneficiaries)
      .map(([pid, w]) => `${nameById[pid] || '?'}${uneven ? ` (×${w})` : ''}`)
      .join(', ')
  }

  return (
    <div>
      {!isClosed && people.length >= 2 && (
        <div className="card">
          <button onClick={() => setNlOpen(!nlOpen)} style={{ width: '100%', textAlign: 'left' }}>
            ✨ Quick add via sentence {nlOpen ? '▲' : '▼'}
          </button>
          {nlOpen && (
            <>
              <p className="caption">e.g. "Karim paid €45 at the restaurant for everyone except Léa"</p>
              <input type="text" value={nlText} onChange={(e) => setNlText(e.target.value)} />
              {nlError && <div className="alert error">{nlError}</div>}
              <div className="spacer" />
              <button onClick={handleParse}>Parse</button>
            </>
          )}
        </div>
      )}

      {!isClosed && people.length >= 2 && (
        <div className="card">
          <button onClick={() => setReceiptOpen(!receiptOpen)} style={{ width: '100%', textAlign: 'left' }}>
            📷 Scan a receipt {receiptOpen ? '▲' : '▼'}
          </button>
          {receiptOpen && (
            <>
              <p className="caption">
                Reads the total and merchant off a photo using your own Anthropic API key. The key is only used
                for this request — it's never saved to disk or the database.
              </p>
              <label>Receipt photo</label>
              <input
                type="file"
                accept="image/jpeg,image/png"
                onChange={(e) => setReceiptFile(e.target.files?.[0] || null)}
              />
              <label>Your Anthropic API key</label>
              <input
                type="password"
                value={receiptApiKey}
                onChange={(e) => setReceiptApiKey(e.target.value)}
                placeholder="Get one at console.anthropic.com"
              />
              {receiptError && <div className="alert error">{receiptError}</div>}
              <div className="spacer" />
              <button onClick={handleScanReceipt} disabled={receiptScanning}>
                {receiptScanning ? 'Reading the receipt…' : 'Scan receipt'}
              </button>
            </>
          )}
        </div>
      )}

      {people.length < 2 && <div className="alert info">Add at least two people (People tab) before logging an expense.</div>}
      {people.length >= 2 && expenses.length === 0 && <div className="alert info">No expenses recorded yet.</div>}

      {expenses.map((exp) => (
        <div className="card row-between" key={exp.id}>
          <div>
            <strong>
              {exp.label || '(no label)'} {exp.is_recurring && '🔁'}
            </strong>{' '}
            — {exp.amount.toFixed(2)} {currency}
            <div className="caption" style={{ margin: 0 }}>
              Paid by {nameById[exp.payer_id] || '?'} · for {describeBeneficiaries(exp)}
            </div>
          </div>
          {!isClosed && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {exp.is_recurring && <button onClick={() => handleRepeat(exp.id)}>🔁 Repeat</button>}
              <Link to={`/groups/${groupId}/expenses/${exp.id}/edit`}>
                <button>Edit</button>
              </Link>
              <button onClick={() => handleDelete(exp.id)}>Delete</button>
            </div>
          )}
        </div>
      ))}

      {!isClosed && (
        <>
          <div className="spacer" />
          <Link to={`/groups/${groupId}/expenses/new`}>
            <button className="primary" disabled={people.length < 2}>
              ➕ Add an expense
            </button>
          </Link>
        </>
      )}
    </div>
  )
}

// =========================================================
// Totals tab
// =========================================================
function TotalsTab({ group, totals }) {
  if (!totals) return null
  const currency = group.currency

  const summaryText = buildSummaryText(group, totals, currency)

  return (
    <div>
      <div className="card">
        <div className="caption" style={{ margin: 0 }}>
          Total spent by the group
        </div>
        <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>
          {totals.total_spent.toFixed(2)} {currency}
        </div>
      </div>

      <strong>By person</strong>
      {totals.balances.map((b) => (
        <div className="card" key={b.person_id}>
          <strong>{b.name}</strong> — paid {b.paid.toFixed(2)} {currency} · share is {b.share.toFixed(2)} {currency}
          <div>
            {b.outstanding > 0.005 && `🟢 Is owed ${b.outstanding.toFixed(2)} ${currency}`}
            {b.outstanding < -0.005 && `🔴 Owes ${Math.abs(b.outstanding).toFixed(2)} ${currency}`}
            {Math.abs(b.outstanding) <= 0.005 && '⚪ Settled up'}
          </div>
        </div>
      ))}

      <div className="spacer" />
      <strong>📋 Copy-paste summary</strong>
      <p className="caption" style={{ margin: '0.25rem 0 0.5rem' }}>
        Ready to drop straight into the group chat.
      </p>
      <textarea readOnly rows={8} value={summaryText} onFocus={(e) => e.target.select()} />
    </div>
  )
}

function buildSummaryText(group, totals, currency) {
  const lines = [`💸 ${group.name} — summary`, `Total spent: ${totals.total_spent.toFixed(2)} ${currency}`, '']
  for (const b of totals.balances) {
    if (b.outstanding > 0.005) lines.push(`🟢 ${b.name} is owed ${b.outstanding.toFixed(2)} ${currency}`)
    else if (b.outstanding < -0.005) lines.push(`🔴 ${b.name} owes ${Math.abs(b.outstanding).toFixed(2)} ${currency}`)
    else lines.push(`⚪ ${b.name} is settled up`)
  }
  lines.push('')
  if (totals.settlement_plan.length === 0) {
    lines.push('Everyone is settled up ✅')
  } else {
    lines.push('To settle up:')
    for (const t of totals.settlement_plan) {
      lines.push(`- ${t.from_name} → ${t.to_name}: ${t.amount.toFixed(2)} ${currency}`)
    }
  }
  return lines.join('\n')
}

// =========================================================
// Settle up tab
// =========================================================
function SettleTab({ groupId, people, repayments, totals, currency, isClosed, onChanged, onClosed }) {
  const [repayFrom, setRepayFrom] = useState(people[0]?.id || '')
  const [repayTo, setRepayTo] = useState(people[1]?.id || '')
  const [repayAmount, setRepayAmount] = useState('')
  const [repayError, setRepayError] = useState('')
  const [reminderPerson, setReminderPerson] = useState('')
  const [confirmClose, setConfirmClose] = useState(false)
  const [closeError, setCloseError] = useState('')

  const nameById = Object.fromEntries(people.map((p) => [p.id, p.name]))

  if (!totals) return null

  const handleRecord = async (fromId, toId, amount) => {
    await api.addRepayment(groupId, { from_person_id: fromId, to_person_id: toId, amount })
    onChanged()
  }

  const handleManualRepay = async (e) => {
    e.preventDefault()
    setRepayError('')
    if (repayFrom === repayTo) {
      setRepayError('Pick two different people.')
      return
    }
    try {
      await api.addRepayment(groupId, { from_person_id: repayFrom, to_person_id: repayTo, amount: parseFloat(repayAmount) })
      setRepayAmount('')
      onChanged()
    } catch (err) {
      setRepayError(apiErrorMessage(err, 'Could not record repayment.'))
    }
  }

  const handleUndo = async (repaymentId) => {
    await api.deleteRepayment(groupId, repaymentId)
    onChanged()
  }

  const allSettled = totals.balances.every((b) => Math.abs(b.outstanding) < 0.005)

  const handleClose = async () => {
    setCloseError('')
    try {
      await api.closeGroup(groupId)
      onClosed()
    } catch (err) {
      setCloseError(apiErrorMessage(err, 'Could not close group.'))
    }
  }

  const debtorNames = [...new Set(totals.settlement_plan.map((t) => t.from_name))]
  const reminderTransactions = totals.settlement_plan.filter((t) => t.from_name === reminderPerson)
  const reminderText =
    reminderTransactions.length > 0
      ? `Hey ${reminderPerson}! 👋 Just a friendly nudge — looks like you still owe ${reminderTransactions
          .map((t) => `${t.amount.toFixed(2)} ${currency} to ${t.to_name}`)
          .join(', ')}. No rush, just didn't want it to slip through the cracks. Thanks!`
      : ''

  return (
    <div>
      <strong>Suggested repayment plan</strong>
      <p className="caption" style={{ margin: '0.25rem 0 0.75rem' }}>
        As few transfers as possible. Recorded repayments below are already subtracted.
      </p>
      {totals.settlement_plan.length === 0 && <div className="alert success">Everyone is settled up ✅</div>}
      {totals.settlement_plan.map((t, i) => (
        <div className="card row" key={i}>
          <span>
            <strong>{t.from_name}</strong> gives <strong>{t.to_name}</strong> {t.amount.toFixed(2)} {currency}
          </span>
          {!isClosed && <button onClick={() => handleRecord(t.from_id, t.to_id, t.amount)}>Record</button>}
        </div>
      ))}

      {!isClosed && (
        <>
          <div className="spacer" />
          <strong>Record a repayment manually</strong>
          <form onSubmit={handleManualRepay}>
            <label>Who's paying?</label>
            <select value={repayFrom} onChange={(e) => setRepayFrom(e.target.value)}>
              {people.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <label>Who's receiving?</label>
            <select value={repayTo} onChange={(e) => setRepayTo(e.target.value)}>
              {people.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <label>Amount ({currency})</label>
            <input type="number" step="0.01" min="0.01" value={repayAmount} onChange={(e) => setRepayAmount(e.target.value)} />
            {repayError && <div className="alert error">{repayError}</div>}
            <div className="spacer" />
            <button type="submit">Record repayment</button>
          </form>
        </>
      )}

      {repayments.length > 0 && (
        <>
          <div className="spacer" />
          <strong>Repayment history</strong>
          {repayments.map((r) => (
            <div className="card row" key={r.id}>
              <span>
                {nameById[r.from_person_id] || '?'} → {nameById[r.to_person_id] || '?'}: {r.amount.toFixed(2)}{' '}
                {currency}
              </span>
              {!isClosed && <button onClick={() => handleUndo(r.id)}>Undo</button>}
            </div>
          ))}
        </>
      )}

      {debtorNames.length > 0 && (
        <>
          <div className="spacer" />
          <strong>✉️ Send a reminder</strong>
          <select value={reminderPerson} onChange={(e) => setReminderPerson(e.target.value)}>
            <option value="">Who still owes money?</option>
            {debtorNames.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          {reminderText && <textarea readOnly rows={4} value={reminderText} onFocus={(e) => e.target.select()} />}
        </>
      )}

      <div className="spacer" />
      {isClosed ? (
        <p className="caption">🔒 This group is closed.</p>
      ) : allSettled ? (
        <div className="card">
          <p className="caption" style={{ margin: 0 }}>
            Everyone is settled up. Closing keeps everything viewable but locks out further changes.
          </p>
          {!confirmClose ? (
            <button onClick={() => setConfirmClose(true)}>Close group…</button>
          ) : (
            <>
              <div className="alert error">Close this group? You won't be able to add or edit anything afterward.</div>
              {closeError && <div className="alert error">{closeError}</div>}
              <button className="primary" onClick={handleClose}>
                Yes, close it
              </button>{' '}
              <button onClick={() => setConfirmClose(false)}>Cancel</button>
            </>
          )}
        </div>
      ) : (
        <p className="caption">Balances must all be zero before this group can be closed.</p>
      )}
    </div>
  )
}

// =========================================================
// People tab
// =========================================================
function PeopleTab({ groupId, people, isClosed, onChanged }) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  const handleAdd = async (e) => {
    e.preventDefault()
    setError('')
    const candidate = name.trim()
    if (!candidate) return
    try {
      await api.addPerson(groupId, { name: candidate })
      setName('')
      onChanged()
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not add person.'))
    }
  }

  const handleRemove = async (personId) => {
    setError('')
    try {
      await api.removePerson(groupId, personId)
      onChanged()
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not remove person.'))
    }
  }

  if (isClosed) {
    return (
      <div>
        {people.map((p) => (
          <div key={p.id}>• {p.name}</div>
        ))}
      </div>
    )
  }

  return (
    <div>
      <p className="caption">You can add someone at any time, even if the group already has expenses.</p>
      <form onSubmit={handleAdd} className="row">
        <input type="text" placeholder="First name" value={name} onChange={(e) => setName(e.target.value)} />
        <button type="submit">Add to group</button>
      </form>
      {error && <div className="alert error">{error}</div>}

      <div className="spacer" />
      {people.map((p) => (
        <div className="row" key={p.id} style={{ marginTop: '0.5rem' }}>
          <span>• {p.name}</span>
          <button onClick={() => handleRemove(p.id)}>Remove</button>
        </div>
      ))}
    </div>
  )
}

// =========================================================
// Delete group box
// =========================================================
function DeleteGroupBox({ groupId, groupName }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [confirm, setConfirm] = useState(false)

  const handleDelete = async () => {
    await api.deleteGroup(groupId)
    navigate('/')
  }

  return (
    <div className="card" style={{ marginTop: '1.5rem' }}>
      <button onClick={() => setOpen(!open)} style={{ width: '100%', textAlign: 'left' }}>
        ⚠️ Delete this group {open ? '▲' : '▼'}
      </button>
      {open && (
        <>
          <div className="alert error">This permanently deletes the group and all its expenses. This can't be undone.</div>
          {!confirm ? (
            <button onClick={() => setConfirm(true)}>Delete group…</button>
          ) : (
            <>
              <p>Are you sure you want to delete '{groupName}' and all its expenses?</p>
              <button className="primary" onClick={handleDelete}>
                Yes, delete permanently
              </button>{' '}
              <button onClick={() => setConfirm(false)}>Cancel</button>
            </>
          )}
        </>
      )}
    </div>
  )
}
