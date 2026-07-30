import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import * as api from '../api'
import { apiErrorMessage } from '../api'

const SECURITY_QUESTIONS = [
  'What city were you born in?',
  'What was the name of your first pet?',
  "What's your mother's maiden name?",
  'What was the name of your first school?',
]

export default function Login() {
  const [tab, setTab] = useState('login')
  const navigate = useNavigate()
  const { login, signup } = useAuth()

  // ---- Log in state ----
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoginError('')
    setLoginLoading(true)
    try {
      await login(loginUsername.trim(), loginPassword)
      navigate('/')
    } catch (err) {
      setLoginError(apiErrorMessage(err, 'Incorrect username or password.'))
    } finally {
      setLoginLoading(false)
    }
  }

  // ---- Sign up state ----
  const [suUsername, setSuUsername] = useState('')
  const [suPassword, setSuPassword] = useState('')
  const [suQuestion, setSuQuestion] = useState(SECURITY_QUESTIONS[0])
  const [suAnswer, setSuAnswer] = useState('')
  const [suError, setSuError] = useState('')
  const [suLoading, setSuLoading] = useState(false)

  const handleSignup = async (e) => {
    e.preventDefault()
    setSuError('')
    if (!suUsername.trim() || !suPassword || !suAnswer.trim()) {
      setSuError('Fill in all fields, including the security answer.')
      return
    }
    if (suPassword.length < 4) {
      setSuError('Password must be at least 4 characters.')
      return
    }
    setSuLoading(true)
    try {
      await signup(suUsername.trim(), suPassword, suQuestion, suAnswer.trim())
      navigate('/')
    } catch (err) {
      setSuError(apiErrorMessage(err, 'Could not create account.'))
    } finally {
      setSuLoading(false)
    }
  }

  // ---- Forgot password state ----
  const [fpUsername, setFpUsername] = useState('')
  const [fpQuestion, setFpQuestion] = useState(null)
  const [fpAnswer, setFpAnswer] = useState('')
  const [fpNewPassword, setFpNewPassword] = useState('')
  const [fpConfirmPassword, setFpConfirmPassword] = useState('')
  const [fpError, setFpError] = useState('')
  const [fpSuccess, setFpSuccess] = useState('')
  const [fpLoading, setFpLoading] = useState(false)

  const handleForgotLookup = async (e) => {
    e.preventDefault()
    setFpError('')
    setFpLoading(true)
    try {
      const res = await api.forgotPasswordLookup({ username: fpUsername.trim() })
      setFpQuestion(res.data.security_question)
    } catch (err) {
      setFpError(apiErrorMessage(err, 'No account with this username.'))
    } finally {
      setFpLoading(false)
    }
  }

  const handleForgotReset = async (e) => {
    e.preventDefault()
    setFpError('')
    if (!fpAnswer.trim() || !fpNewPassword) {
      setFpError('Fill in all fields.')
      return
    }
    if (fpNewPassword.length < 4) {
      setFpError('Password must be at least 4 characters.')
      return
    }
    if (fpNewPassword !== fpConfirmPassword) {
      setFpError("Passwords don't match.")
      return
    }
    setFpLoading(true)
    try {
      await api.forgotPasswordReset({
        username: fpUsername.trim(),
        security_answer: fpAnswer.trim(),
        new_password: fpNewPassword,
      })
      setFpSuccess('Password reset. You can log in with your new password now.')
      setFpQuestion(null)
      setFpUsername('')
      setFpAnswer('')
      setFpNewPassword('')
      setFpConfirmPassword('')
    } catch (err) {
      setFpError(apiErrorMessage(err, 'Could not reset password.'))
    } finally {
      setFpLoading(false)
    }
  }

  return (
    <div className="page" style={{ maxWidth: 460 }}>
      <h1>💸 Who owes what?</h1>
      <p className="caption">A group's accounts, without spreadsheets or migraines.</p>

      <div className="tabs">
        <button className={`tab ${tab === 'login' ? 'active' : ''}`} onClick={() => setTab('login')}>
          Log in
        </button>
        <button className={`tab ${tab === 'signup' ? 'active' : ''}`} onClick={() => setTab('signup')}>
          Sign up
        </button>
        <button className={`tab ${tab === 'forgot' ? 'active' : ''}`} onClick={() => setTab('forgot')}>
          Forgot password?
        </button>
      </div>

      {tab === 'login' && (
        <form onSubmit={handleLogin}>
          <label>Username</label>
          <input type="text" value={loginUsername} onChange={(e) => setLoginUsername(e.target.value)} />
          <label>Password</label>
          <input type="password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} />
          {loginError && <div className="alert error">{loginError}</div>}
          <div className="spacer" />
          <button type="submit" className="primary" disabled={loginLoading}>
            {loginLoading ? 'Logging in…' : 'Log in'}
          </button>
        </form>
      )}

      {tab === 'signup' && (
        <form onSubmit={handleSignup}>
          <label>Choose a username</label>
          <input type="text" value={suUsername} onChange={(e) => setSuUsername(e.target.value)} />
          <label>Choose a password</label>
          <input type="password" value={suPassword} onChange={(e) => setSuPassword(e.target.value)} />
          <label>Security question (used to recover your account)</label>
          <select value={suQuestion} onChange={(e) => setSuQuestion(e.target.value)}>
            {SECURITY_QUESTIONS.map((q) => (
              <option key={q} value={q}>
                {q}
              </option>
            ))}
          </select>
          <label>Your answer</label>
          <input type="text" value={suAnswer} onChange={(e) => setSuAnswer(e.target.value)} />
          {suError && <div className="alert error">{suError}</div>}
          <div className="spacer" />
          <button type="submit" className="primary" disabled={suLoading}>
            {suLoading ? 'Creating account…' : 'Create account'}
          </button>
        </form>
      )}

      {tab === 'forgot' && (
        <>
          {fpSuccess && <div className="alert success">{fpSuccess}</div>}
          {fpQuestion === null ? (
            <form onSubmit={handleForgotLookup}>
              <label>Your username</label>
              <input type="text" value={fpUsername} onChange={(e) => setFpUsername(e.target.value)} />
              {fpError && <div className="alert error">{fpError}</div>}
              <div className="spacer" />
              <button type="submit" disabled={fpLoading}>
                {fpLoading ? 'Looking up…' : 'Continue'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleForgotReset}>
              <p className="caption">
                Account: <strong>{fpUsername}</strong>
              </p>
              <label>{fpQuestion}</label>
              <input type="text" value={fpAnswer} onChange={(e) => setFpAnswer(e.target.value)} />
              <label>New password</label>
              <input type="password" value={fpNewPassword} onChange={(e) => setFpNewPassword(e.target.value)} />
              <label>Confirm new password</label>
              <input
                type="password"
                value={fpConfirmPassword}
                onChange={(e) => setFpConfirmPassword(e.target.value)}
              />
              {fpError && <div className="alert error">{fpError}</div>}
              <div className="spacer" />
              <button type="submit" className="primary" disabled={fpLoading}>
                {fpLoading ? 'Resetting…' : 'Reset password'}
              </button>
              <div className="spacer" />
              <button type="button" onClick={() => setFpQuestion(null)}>
                Start over
              </button>
            </form>
          )}
        </>
      )}
    </div>
  )
}
