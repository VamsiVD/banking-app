import { useState } from 'react'
import './App.css'
import AdminHome from './AdminHome.jsx'
import UserHome from './UserHome.jsx'
import { api } from './api/client.js'
import { clearSession, loadSession, saveSession } from './auth.js'

function App() {
  // Restored on load, so a refresh does not sign an admin out mid-task.
  const [session, setSession] = useState(() => loadSession())
  const [showUserHome, setShowUserHome] = useState(false)
  const [accountType, setAccountType] = useState('user')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const isAdmin = accountType === 'admin'

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    const endpoint = isAdmin ? '/admin/login' : '/auth/login'

    try {
      // `auth: false` — there is no token yet, and sending a stale one from a
      // previous session would be the wrong credential for this request.
      const data = await api.post(endpoint, { email, password }, { auth: false })

      const next = {
        token: data.access_token,
        role: isAdmin ? 'admin' : 'user',
        email,
      }
      saveSession(next)
      setSession(next)
      setPassword('')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleSignOut = () => {
    clearSession()
    setSession(null)
    setShowUserHome(false)
    setError(null)
  }

  if (session?.role === 'admin') {
    return <AdminHome admin={session} onSignOut={handleSignOut} />
  }

  // Signed-in customers, and the standalone preview button below, both land here.
  if (session?.role === 'user' || showUserHome) {
    return <UserHome onBack={handleSignOut} />
  }

  return (
    <main className="login-page">
      <h1 className="bank-name">Banks-<span style={{ display: 'inline-block', transform: 'scaleX(-1)' }}>R</span>-Us</h1>

      <section className="login-card">
        <h2>Secure Sign In</h2>

        <div className="account-toggle">
          <button
            type="button"
            className={!isAdmin ? 'active' : ''}
            onClick={() => {
              setAccountType('user')
              setError(null)
            }}
          >
            Personal
          </button>

          <button
            type="button"
            className={isAdmin ? 'active' : ''}
            onClick={() => {
              setAccountType('admin')
              setError(null)
            }}
          >
            Admin
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          {error && (
            <p className="login-error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="sign-in-button" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign In'}
            <span>→</span>
          </button>
        </form>

        <button
          type="button"
          onClick={() => setShowUserHome(true)}
          className="sign-in-button"
        >
          User Home
        </button>

        {!isAdmin && (
          <p className="create-account">
            New customer?{' '}
            <button type="button" onClick={() => console.log('Create account')}>
              Create Account
            </button>
          </p>
        )}
      </section>
    </main>
  )
}

export default App
