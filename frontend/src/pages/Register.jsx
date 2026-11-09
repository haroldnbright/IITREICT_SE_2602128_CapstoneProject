// Register page, public: new customers, restaurant owners and delivery partners sign up here
import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { HOME_BY_ROLE, useAuth } from '../context/AuthContext'

// Roles a new user can pick, with friendly labels
const ROLES = [
  { value: 'customer', label: 'Order food' },
  { value: 'owner', label: 'Run a restaurant' },
  { value: 'delivery', label: 'Deliver orders' },
]

// Starting value of every form field; new users start as customers
const EMPTY_FORM = {
  name: '', email: '', password: '', role: 'customer', phone: '', address: '', restaurant_name: '', cuisine: '',
}

// Sign-up form whose extra fields change with the chosen role
export default function Register() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY_FORM)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Already logged in, so send them to the home page for their role
  if (user) return <Navigate to={HOME_BY_ROLE[user.role]} replace />

  // Returns an onChange handler that updates one field of the form, e.g. set('email')
  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value })

  // Creates the account, which also logs the user in, then opens their home page
  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    // Send only the fields that have a value
    const body = {}
    for (const [key, value] of Object.entries(form)) {
      if (value.trim() !== '') body[key] = value
    }
    try {
      const newUser = await register(body)
      navigate(HOME_BY_ROLE[newUser.role], { replace: true })
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <section className="auth">
      <div className="auth-card">
        <h1>Create an account</h1>
        <form onSubmit={submit} className="form">
          <fieldset className="role-picker">
            <legend>I want to</legend>
            {ROLES.map((role) => (
              <label key={role.value} className={form.role === role.value ? 'selected' : ''}>
                <input type="radio" name="role" value={role.value} checked={form.role === role.value} onChange={set('role')} />
                {role.label}
              </label>
            ))}
          </fieldset>
          <label>
            Full name
            <input value={form.name} onChange={set('name')} required minLength={2} autoComplete="name" />
          </label>
          <label>
            Email
            <input type="email" value={form.email} onChange={set('email')} required autoComplete="email" />
          </label>
          <label>
            Password
            <input type="password" value={form.password} onChange={set('password')} required minLength={6}
              maxLength={72} autoComplete="new-password" />
            <span className="hint">At least 6 characters</span>
          </label>
          <label>
            Phone
            <input type="tel" value={form.phone} onChange={set('phone')} autoComplete="tel" />
          </label>
          {/* Role-specific fields */}
          {form.role === 'customer' && (
            <label>
              Delivery address
              <input value={form.address} onChange={set('address')} placeholder="Room, hostel or building" />
            </label>
          )}
          {form.role === 'owner' && (
            <>
              <label>
                Restaurant name
                <input value={form.restaurant_name} onChange={set('restaurant_name')} required />
              </label>
              <label>
                Cuisine
                <input value={form.cuisine} onChange={set('cuisine')} placeholder="e.g. South Indian" />
              </label>
            </>
          )}
          {error && <p className="form-error">{error}</p>}
          <button className="btn btn-primary btn-block" disabled={loading}>{loading ? 'Creating account...' : 'Create account'}</button>
        </form>
        <p className="muted small">Already have an account? <Link to="/login">Log in</Link></p>
      </div>
    </section>
  )
}
