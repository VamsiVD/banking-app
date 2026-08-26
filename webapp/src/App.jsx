import { useState } from 'react'
import './App.css'

function App() {
  const [accountType, setAccountType] = useState('user')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const isAdmin = accountType === 'admin'

  const handleSubmit = async (event) => {
    event.preventDefault()

    const endpoint = isAdmin ? '/admin/login' : '/auth/login'

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Sign in failed')
      }

      console.log('Signed in:', data)
    } catch (error) {
      console.error(error)
    }
  }

  return (
    <main className="login-page">
      <h1 className="bank-name">Banks-R-Us</h1>

      <section className="login-card">
        <h2>Secure Sign In</h2>

        <div className="account-toggle">
          <button
            type="button"
            className={!isAdmin ? 'active' : ''}
            onClick={() => setAccountType('user')}
          >
            Personal
          </button>

          <button
            type="button"
            className={isAdmin ? 'active' : ''}
            onClick={() => setAccountType('admin')}
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

          <button type="submit" className="sign-in-button">
            Sign In
            <span>→</span>
          </button>
        </form>

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