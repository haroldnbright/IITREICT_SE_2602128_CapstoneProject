// Shopping cart state shared across the app through React context
import { createContext, useContext, useEffect, useState } from 'react'
import { useAuth } from './AuthContext'

// localStorage key for the saved cart
const CART_KEY = 'campusbite_cart'
// Most of one dish a customer can have in the cart
const MAX_QUANTITY = 20
// Starting value for a cart with nothing in it
const EMPTY_CART = { restaurantId: null, restaurantName: '', items: [] }
const CartContext = createContext(null)

// Turns a dish into a cart line: only the fields the cart needs, plus a quantity of 1
const newCartLine = (dish) => ({ id: dish.id, name: dish.name, price: dish.price, quantity: 1 })

// Reads the saved cart from localStorage, or returns an empty cart if nothing is saved
function loadSavedCart() {
  const saved = JSON.parse(localStorage.getItem(CART_KEY) || 'null')
  if (saved) return saved
  return EMPTY_CART
}

// The cart holds dishes from one restaurant at a time, and is saved in localStorage
export function CartProvider({ children }) {
  const { user } = useAuth()
  // Restore the saved cart on first load, or start empty
  const [cart, setCart] = useState(loadSavedCart)

  // Save the cart every time it changes so it survives a page refresh
  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(cart))
  }, [cart])

  // Clear the cart when the user logs out
  useEffect(() => {
    if (!user) setCart(EMPTY_CART)
  }, [user])

  // Returns false if the dish is from another restaurant and the user keeps their cart
  const addItem = (restaurant, dish) => {
    // Switching restaurants asks first, then replaces the cart with this dish
    const isOtherRestaurant = cart.restaurantId && cart.restaurantId !== restaurant.id
    if (isOtherRestaurant) {
      const ok = window.confirm(`Your cart has dishes from ${cart.restaurantName}. Start a new cart for ${restaurant.name}?`)
      if (!ok) return false
      setCart({ restaurantId: restaurant.id, restaurantName: restaurant.name, items: [newCartLine(dish)] })
      return true
    }
    setCart((currentCart) => {
      // Same dish again bumps its quantity (up to the max), otherwise it is added as a new line
      const alreadyInCart = currentCart.items.some((item) => item.id === dish.id)
      let items
      if (alreadyInCart) {
        items = currentCart.items.map((item) => {
          if (item.id !== dish.id) return item
          return { ...item, quantity: Math.min(item.quantity + 1, MAX_QUANTITY) }
        })
      } else {
        items = [...currentCart.items, newCartLine(dish)]
      }
      return { restaurantId: restaurant.id, restaurantName: restaurant.name, items }
    })
    return true
  }

  // Sets a dish's quantity, capped at the max; going below 1 removes it
  const updateQuantity = (dishId, quantity) => {
    if (quantity < 1) return removeItem(dishId)
    setCart((currentCart) => {
      const items = currentCart.items.map((item) => {
        if (item.id !== dishId) return item
        return { ...item, quantity: Math.min(quantity, MAX_QUANTITY) }
      })
      return { ...currentCart, items }
    })
  }

  // Removes one dish, and resets the cart fully once it is empty
  const removeItem = (dishId) => {
    setCart((currentCart) => {
      const items = currentCart.items.filter((item) => item.id !== dishId)
      if (items.length === 0) return EMPTY_CART
      return { ...currentCart, items }
    })
  }

  // Empties the cart, for example after an order is placed
  const clearCart = () => setCart(EMPTY_CART)

  // Total number of items (for the navbar badge) and the cart's price total
  let count = 0
  let total = 0
  for (const item of cart.items) {
    count += item.quantity
    total += item.price * item.quantity
  }

  return (
    <CartContext.Provider value={{ cart, count, total, addItem, updateQuantity, removeItem, clearCart }}>
      {children}
    </CartContext.Provider>
  )
}

// Hook for reading and changing the cart in any component
export const useCart = () => useContext(CartContext)
