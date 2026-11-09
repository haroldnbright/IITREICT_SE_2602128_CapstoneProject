// Cart page, customer: review the cart, change quantities and place the order
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { Empty } from '../../components/Feedback'
import { useAuth } from '../../context/AuthContext'
import { useCart } from '../../context/CartContext'
import { money } from '../../utils/format'

// Most of one dish allowed in a single order (the cart also caps it at this number)
const MAX_QUANTITY = 20

// Cart items with quantity controls, plus a checkout form with demo payment
export default function Cart() {
  const { user } = useAuth()
  const { cart, total, updateQuantity, removeItem, clearCart } = useCart()
  const navigate = useNavigate()
  // Start with the address saved on the user's profile, which they can edit for this order
  const [address, setAddress] = useState(user.address || '')
  const [placing, setPlacing] = useState(false)
  const [error, setError] = useState('')

  if (cart.items.length === 0) {
    return (
      <section className="narrow">
        <h1>Your cart</h1>
        <Empty title="Your cart is empty">
          <Link to="/restaurants" className="btn btn-primary">Browse restaurants</Link>
        </Empty>
      </section>
    )
  }

  // Creates the order on the server, empties the cart and opens the new order's page
  const placeOrder = async (event) => {
    event.preventDefault()
    setPlacing(true)
    setError('')
    // Only ids and quantities are sent; the server looks up current prices itself
    const orderItems = cart.items.map((item) => ({ menu_item_id: item.id, quantity: item.quantity }))
    try {
      const order = await api('/orders', {
        method: 'POST',
        body: {
          restaurant_id: cart.restaurantId,
          delivery_address: address,
          items: orderItems,
        },
      })
      clearCart()
      // justPlaced tells the order page to show a confirmation message
      navigate(`/orders/${order.id}`, { state: { justPlaced: true } })
    } catch (err) {
      setError(err.message)
      setPlacing(false)
    }
  }

  return (
    <section className="cart-layout">
      <div>
        <h1>Your cart</h1>
        <p className="muted">From <Link to={`/restaurants/${cart.restaurantId}`}>{cart.restaurantName}</Link></p>
        <div className="cart-list">
          {cart.items.map((item) => (
            <div key={item.id} className="cart-row">
              <div>
                <p className="dish-name">{item.name}</p>
                <p className="muted small">{money(item.price)} each</p>
              </div>
              <div className="qty" aria-label={`Quantity of ${item.name}`}>
                <button onClick={() => updateQuantity(item.id, item.quantity - 1)} aria-label="One less">-</button>
                <span>{item.quantity}</span>
                <button onClick={() => updateQuantity(item.id, item.quantity + 1)} aria-label="One more"
                  disabled={item.quantity >= MAX_QUANTITY}>+</button>
              </div>
              <span className="cart-line-total">{money(item.price * item.quantity)}</span>
              <button className="link-button" onClick={() => removeItem(item.id)}>Remove</button>
            </div>
          ))}
        </div>
      </div>

      <form className="checkout" onSubmit={placeOrder}>
        <h2>Checkout</h2>
        <label>
          Deliver to
          <textarea rows="2" value={address} onChange={(e) => setAddress(e.target.value)} required minLength={5}
            placeholder="Room, hostel or building" />
        </label>
        <div className="demo-pay">
          <strong>Demo payment</strong>
          <p className="small">No card needed and no money is charged. The order is marked as paid for testing.</p>
        </div>
        <div className="checkout-total">
          <span>To pay</span>
          <strong>{money(total)}</strong>
        </div>
        {error && <p className="form-error">{error}</p>}
        <button className="btn btn-primary btn-block" disabled={placing}>
          {placing ? 'Placing order...' : `Pay ${money(total)} and place order`}
        </button>
      </form>
    </section>
  )
}
