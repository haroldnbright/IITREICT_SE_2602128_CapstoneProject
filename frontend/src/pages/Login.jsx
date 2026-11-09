// Login page, public: any user signs in here with email and password
import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { HOME_BY_ROLE, useAuth } from '../context/AuthContext'

// Password shared by all the seeded demo accounts
const DEMO_PASSWORD = 'password123'

// Seeded demo accounts; clicking one fills the form so reviewers can try each role quickly
const DEMO_ACCOUNTS = [
  { label: 'Customer', email: 'customer@campusbite.com' },
  { label: 'Restaurant owner', email: 'owner1@campusbite.com' },
  { label: 'Delivery partner', email: 'delivery1@campusbite.com' },
]

// Login form, plus one-click buttons that fill in a demo account
export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Already logged in, so skip the form and go to the home page for their role
  if (user) return <Navigate to={HOME_BY_ROLE[user.role]} replace />

  // Logs the user in and redirects them, or shows the error from the API
  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const loggedIn = await login(email, password)
      // Go back to the page they wanted, otherwise to the home page for their role.
      // ProtectedRoute redirects them if the page they wanted is not for their role.
      const destination = location.state?.from || HOME_BY_ROLE[loggedIn.role]
      navigate(destination, { replace: true })
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  // Fills the form with one of the demo accounts
  const fillDemoAccount = (demoEmail) => {
    setEmail(demoEmail)
    setPassword(DEMO_PASSWORD)
  }

  return (
    <section className="auth">
      <div className="auth-card">
        <h1>Log in</h1>
        <form onSubmit={submit} className="form">
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
              autoComplete="current-password" />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button className="btn btn-primary btn-block" disabled={loading}>{loading ? 'Logging in...' : 'Log in'}</button>
        </form>
        <p className="muted small">New here? <Link to="/register">Create an account</Link></p>
      </div>

      <aside className="demo-box">
        <p className="demo-title">Demo accounts</p>
        <p className="muted small">Password for all: {DEMO_PASSWORD}</p>
        {DEMO_ACCOUNTS.map((account) => (
          <button key={account.email} type="button" className="demo-account"
            onClick={() => fillDemoAccount(account.email)}>
            <strong>{account.label}</strong>
            <span>{account.email}</span>
          </button>
        ))}
      </aside>
    </section>
  )
}
