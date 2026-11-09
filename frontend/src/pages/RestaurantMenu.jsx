// Restaurant menu page, public: anyone can view the menu, customers add dishes to their cart
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { Empty, ErrorBox, Loader } from '../components/Feedback'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import { dateTime, money } from '../utils/format'
import useApi from '../utils/useApi'

// Default menu filters, also used by the Clear filters button
const emptyFilters = { search: '', min_price: '', max_price: '', veg_only: false, sort: 'category' }
// How long to wait after the last filter change before reloading the menu, in milliseconds
const FILTER_DELAY_MS = 300
// How long the "Added" label stays on a dish's button, in milliseconds
const ADDED_FLASH_MS = 1200
// Number of recent reviews shown under the menu
const REVIEW_COUNT = 5

// Restaurant details, filterable menu, recent reviews and a cart shortcut bar
export default function RestaurantMenu() {
  const { id } = useParams()
  const { user } = useAuth()
  const { cart, count, total, addItem } = useCart()
  const navigate = useNavigate()
  // filters follows the inputs; applied is the debounced copy sent to the API
  const [filters, setFilters] = useState(emptyFilters)
  const [applied, setApplied] = useState(emptyFilters)
  // Id of the dish just added, used to flash "Added" on its button
  const [added, setAdded] = useState(null)

  // Apply filters shortly after the user stops typing
  useEffect(() => {
    const timer = setTimeout(() => setApplied(filters), FILTER_DELAY_MS)
    return () => clearTimeout(timer)
  }, [filters])

  // Three independent requests: restaurant details, the filtered menu and the latest reviews
  const restaurant = useApi(() => api(`/restaurants/${id}`), [id])
  const menu = useApi(() => {
    const params = { ...applied }
    // Leave veg_only out unless it is ticked so the API doesn't filter on false
    if (!applied.veg_only) params.veg_only = undefined
    return api(`/restaurants/${id}/menu`, { params })
  }, [id, applied])
  const reviews = useApi(() => api(`/restaurants/${id}/reviews`, { params: { size: REVIEW_COUNT } }), [id])

  // Returns an onChange handler for one filter, e.g. set('search')
  const set = (key) => (event) => {
    // Checkboxes store true/false; the other inputs store their text
    let value = event.target.value
    if (event.target.type === 'checkbox') value = event.target.checked
    setFilters({ ...filters, [key]: value })
  }

  // Adds a dish to the cart and briefly marks it as added; guests are sent to log in first
  const handleAdd = (dish) => {
    if (!user) {
      // Remember this page so login can bring them straight back
      navigate('/login', { state: { from: `/restaurants/${id}` } })
      return
    }
    // addItem returns false if the customer declines to start a new cart for this restaurant
    if (addItem(restaurant.data, dish)) {
      setAdded(dish.id)
      setTimeout(() => setAdded(null), ADDED_FLASH_MS)
    }
  }

  // Text for a dish's Add button
  const addButtonLabel = (dish) => {
    if (!dish.is_available) return 'Sold out'
    if (added === dish.id) return 'Added'
    return 'Add'
  }

  if (restaurant.loading) return <Loader />
  if (restaurant.error) return <ErrorBox message={restaurant.error} onRetry={restaurant.reload} />
  const details = restaurant.data

  // Group dishes by category when sorted by category, otherwise put them all in one "Dishes" group
  const groups = {}
  for (const dish of menu.data || []) {
    let groupName = 'Dishes'
    if (applied.sort === 'category') groupName = dish.category || 'Other'
    if (!groups[groupName]) groups[groupName] = []
    groups[groupName].push(dish)
  }

  // Owners and riders can view menus but not order; guests see Add and are asked to log in
  const canOrder = !user || user.role === 'customer'
  // Only show the cart bar when the cart holds dishes from this restaurant
  const cartHere = cart.restaurantId === details.id && count > 0

  // Pick what to show for the menu: a loader on first load, an empty message or the dish groups
  let menuContent
  if (menu.loading && !menu.data) {
    menuContent = <Loader text="Loading menu..." />
  } else if (menu.data && menu.data.length === 0) {
    menuContent = (
      <Empty title="No dishes match these filters">
        <button className="btn btn-quiet" onClick={() => setFilters(emptyFilters)}>Clear filters</button>
      </Empty>
    )
  } else {
    menuContent = Object.entries(groups).map(([category, dishes]) => (
      <div key={category} className="menu-group">
        <h2>{category}</h2>
        {dishes.map((dish) => (
          <div key={dish.id} className={`dish ${dish.is_available ? '' : 'dish-off'}`}>
            <div>
              <p className="dish-name">
                <span className={dish.is_veg ? 'veg-dot' : 'nonveg-dot'} title={dish.is_veg ? 'Veg' : 'Non-veg'} />
                {dish.name}
              </p>
              {dish.description && <p className="muted small">{dish.description}</p>}
            </div>
            <div className="dish-buy">
              <span className="dish-price">{money(dish.price)}</span>
              {canOrder && (
                <button className="btn btn-primary btn-small" disabled={!dish.is_available || !details.is_open}
                  onClick={() => handleAdd(dish)}>
                  {addButtonLabel(dish)}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    ))
  }

  return (
    <section className="menu-page">
      <div className="menu-header">
        <div>
          <Link to="/restaurants" className="back-link">All restaurants</Link>
          <h1>{details.name}</h1>
          <p className="muted">{details.cuisine} | {details.address}</p>
          <p>{details.description}</p>
        </div>
        <div className="rating-block">
          {details.avg_rating ? (
            <><strong>★ {details.avg_rating}</strong><span>{details.review_count} reviews</span></>
          ) : (
            <span>No ratings yet</span>
          )}
        </div>
      </div>
      {!details.is_open && <p className="error-box">This restaurant isn't taking orders right now.</p>}

      <div className="filters">
        <label className="grow">
          Search dishes
          <input type="search" value={filters.search} onChange={set('search')} placeholder="e.g. biryani" />
        </label>
        <label>
          Min price
          <input type="number" min="0" value={filters.min_price} onChange={set('min_price')} />
        </label>
        <label>
          Max price
          <input type="number" min="0" value={filters.max_price} onChange={set('max_price')} />
        </label>
        <label>
          Sort by
          <select value={filters.sort} onChange={set('sort')}>
            <option value="category">Category</option>
            <option value="price_asc">Price: low to high</option>
            <option value="price_desc">Price: high to low</option>
            <option value="name">Name</option>
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={filters.veg_only} onChange={set('veg_only')} />
          Veg only
        </label>
      </div>

      <ErrorBox message={menu.error} onRetry={menu.reload} />
      {menuContent}

      <div className="menu-group">
        <h2>Recent reviews</h2>
        {reviews.data?.items.length ? (
          reviews.data.items.map((review) => (
            <div key={review.id} className="review">
              <p><strong>{'★'.repeat(review.rating)}</strong> <span className="muted small">{review.customer_name} | {dateTime(review.created_at)}</span></p>
              {review.comment && <p>{review.comment}</p>}
            </div>
          ))
        ) : (
          <p className="muted">No reviews yet.</p>
        )}
      </div>

      {cartHere && (
        <Link to="/cart" className="cart-bar">
          <span>{count} item{count > 1 ? 's' : ''} | {money(total)}</span>
          <strong>View cart</strong>
        </Link>
      )}
    </section>
  )
}
