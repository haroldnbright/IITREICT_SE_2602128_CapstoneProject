// Top navigation bar shown on every page
import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'

// Links shown to each role
const LINKS = {
  guest: [{ to: '/restaurants', label: 'Restaurants' }],
  customer: [
    { to: '/restaurants', label: 'Restaurants' },
    { to: '/orders', label: 'My orders' },
    { to: '/insights', label: 'Order insights' },
  ],
  owner: [
    { to: '/owner', label: 'Dashboard', end: true },
    { to: '/owner/orders', label: 'Orders' },
    { to: '/owner/menu', label: 'Menu' },
  ],
  delivery: [{ to: '/delivery', label: 'Deliveries' }],
}

// Renders the brand, the links for the current user's role, the cart count and login/logout
// On small screens the links collapse behind a menu button
export default function Navbar() {
  const { user, logout } = useAuth()
  const { count } = useCart()
  const navigate = useNavigate()
  // Whether the mobile menu is expanded
  const [open, setOpen] = useState(false)
  // Logged-out visitors get the guest links
  let role = 'guest'
  if (user && user.role) role = user.role
  const links = LINKS[role]
  const isCustomer = role === 'customer'

  // Clicking any link closes the mobile menu
  const closeMenu = () => setOpen(false)

  // Logs out, closes the mobile menu and goes to the login page
  const handleLogout = () => {
    logout()
    closeMenu()
    navigate('/login')
  }

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="brand" onClick={closeMenu}>
          <span className="brand-mark" aria-hidden="true" />
          CampusBite
        </Link>

        <button className="menu-toggle" aria-expanded={open} aria-label="Menu" onClick={() => setOpen(!open)}>
          <span />
          <span />
          <span />
        </button>

        <nav className={`nav-links ${open ? 'open' : ''}`}>
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} onClick={closeMenu}>
              {link.label}
            </NavLink>
          ))}
          {isCustomer && (
            <NavLink to="/cart" className="cart-link" onClick={closeMenu}>
              Cart {count > 0 && <span className="cart-count">{count}</span>}
            </NavLink>
          )}
          {user ? (
            <div className="nav-user">
              <span className="nav-name">{user.name}</span>
              <button className="btn btn-quiet" onClick={handleLogout}>Log out</button>
            </div>
          ) : (
            <div className="nav-user">
              <NavLink to="/login" onClick={closeMenu}>Log in</NavLink>
              <Link to="/register" className="btn btn-primary btn-small" onClick={closeMenu}>Sign up</Link>
            </div>
          )}
        </nav>
      </div>
    </header>
  )
}
