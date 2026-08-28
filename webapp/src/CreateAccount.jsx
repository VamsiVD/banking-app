import { useState } from 'react'
import './App.css'
import { api } from './api/client.js'

function CreateAccount({ onBack }) {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setSubmitting(true)

    try {
      await api.post(
        '/auth/register',
        {
          email,
          password,
          full_name: `${firstName} ${lastName}`.trim(),
        },
        { auth: false }
      )

      setSuccess(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (success) {
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
          <h2>Account Created</h2>

          <p className="success-message">
            Your account has been created successfully.
          </p>

          <button
            type="button"
            className="sign-in-button"
            onClick={onBack}
          >
            Back to Sign In
          </button>
        </section>
      </main>
    )
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
        <h2>Create Your Account</h2>

        <form onSubmit={handleSubmit}>
          <label htmlFor="first-name">First Name</label>
          <input
            id="first-name"
            type="text"
            value={firstName}
            onChange={(event) => setFirstName(event.target.value)}
            required
          />

          <label htmlFor="last-name">Last Name</label>
          <input
            id="last-name"
            type="text"
            value={lastName}
            onChange={(event) => setLastName(event.target.value)}
            required
          />

          <label htmlFor="create-email">Email</label>
          <input
            id="create-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="create-password">Password</label>
          <input
            id="create-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            required
          />

          <label htmlFor="confirm-password">Confirm Password</label>
          <input
            id="confirm-password"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            minLength={8}
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
            {submitting ? 'Creating Account…' : 'Create Account'}
          </button>
        </form>

        <p className="create-account">
          Already have an account?{' '}
          <button type="button" onClick={onBack}>
            Back to Sign In
          </button>
        </p>
      </section>
    </main>
  )
}

export default CreateAccount