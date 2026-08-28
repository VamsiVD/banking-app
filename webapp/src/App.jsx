import { useEffect, useState } from 'react'
import './App.css'
import AdminHome from './AdminHome.jsx'
import UserHome from './UserHome.jsx'
import CreateAccount from './CreateAccount.jsx'
import { api } from './api/client.js'
import { clearSession, loadSession, saveSession } from './auth.js'

function App() {
  // restore the saved session when the page loads
  const [session, setSession] = useState(() => loadSession())
  const [showCreateAccount, setShowCreateAccount] = useState(false)
  const [accountType, setAccountType] = useState('user')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const isAdmin = accountType === 'admin'

  useEffect(() => {
    // The API client fires this the moment any authenticated request comes
    // back 401 — session expired, revoked, or tampered with. Without this,
    // the stored session is already gone but the UI would keep showing the
    // dashboard until something else happened to trigger a re-render.
    const handleExpiry = () => {
      setSession(null)
      setError('Your session expired. Please sign in again.')
    }

    window.addEventListener('session-expired', handleExpiry)
    return () => window.removeEventListener('session-expired', handleExpiry)
  }, [])

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    const endpoint = isAdmin ? '/admin/login' : '/auth/login'

    try {
      // no token exists yet, so do not send an old session token
      const data = await api.post(
        endpoint,
        { email, password },
        { auth: false }
      )

      const next = { // this is where the frontend takes the token returned from the backend
        token: data.access_token,
        role: isAdmin ? 'admin' : 'user',
        email,
      }

      saveSession(next)
      setSession(next) // save the session in state and establishes a login happening
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
    setShowCreateAccount(false)
    setError(null)
  }

  if (showCreateAccount) {
    return (
      <CreateAccount
        onBack={() => {
          setShowCreateAccount(false)
          setError(null)
        }}
      />
    )
  }

  if (session?.role === 'admin') {
    return <AdminHome admin={session} onSignOut={handleSignOut} />
  }

  if (session?.role === 'user') {
    return <UserHome user={session} onBack={handleSignOut} />
  }

  return (
    <main className="login-page">
      <h1 className="bank-name">
        Banks-
        <span
          style={{
            display: 'inline-block',
            transform: 'scaleX(-1)',
          }}
        >
          R
        </span>
        -Us
      </h1>

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

          <button
            type="submit"
            className="sign-in-button"
            disabled={submitting}
          >
            {submitting ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        {!isAdmin && (
          <p className="create-account">
            New customer?{' '}
            <button
              type="button"
              onClick={() => {
                setShowCreateAccount(true)
                setError(null)
              }}
            >
              Create Account
            </button>
          </p>
        )}
      </section>
    </main>
  )
}

export default App