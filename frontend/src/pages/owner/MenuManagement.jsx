// Menu management page, restaurant owner: add, edit, delete dishes and mark them sold out
import { useState } from 'react'
import { api } from '../../api/client'
import { Empty, ErrorBox, Loader } from '../../components/Feedback'
import { money } from '../../utils/format'
import useApi from '../../utils/useApi'

// Empty dish form used for "Add a dish" and after saving or cancelling
const blank = { name: '', description: '', price: '', category: '', is_veg: true, is_available: true }

// Dish form on one side and the owner's menu table on the other
export default function MenuManagement() {
  const menu = useApi(() => api('/owner/menu'), [])
  const [form, setForm] = useState(blank)
  // Id of the dish being edited, or null when the form adds a new dish
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')

  // Returns an onChange handler for one form field, e.g. set('name')
  const set = (key) => (event) => {
    // Checkboxes store true/false; the other inputs store their text
    let value = event.target.value
    if (event.target.type === 'checkbox') value = event.target.checked
    setForm({ ...form, [key]: value })
  }

  // Loads a dish into the form for editing and scrolls up to the form
  const startEdit = (dish) => {
    setEditingId(dish.id)
    // Turn null fields into empty strings so the inputs stay controlled
    setForm({ ...dish, description: dish.description || '', category: dish.category || '' })
    setError('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Leaves edit mode and clears the form
  const reset = () => {
    setEditingId(null)
    setForm(blank)
    setError('')
  }

  // Creates a new dish or updates the one being edited, then reloads the menu
  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    // The price input gives a string, and id/restaurant_id are not editable fields
    const body = { ...form, price: Number(form.price) }
    delete body.id
    delete body.restaurant_id
    try {
      if (editingId) {
        await api(`/owner/menu/${editingId}`, { method: 'PUT', body })
      } else {
        await api('/owner/menu', { method: 'POST', body })
      }
      reset()
      // Reload so a new or renamed dish appears in the right place
      menu.reload()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  // Flips a dish between available and sold out
  const toggle = async (dish) => {
    try {
      const body = { is_available: !dish.is_available }
      const updated = await api(`/owner/menu/${dish.id}/availability`, { method: 'PATCH', body })
      // Swap in the updated dish instead of reloading the whole menu
      menu.setData((dishes) => dishes.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setError(err.message)
    }
  }

  // Deletes a dish after confirmation; past orders are unaffected because they store their own copy
  const remove = async (dish) => {
    if (!window.confirm(`Delete ${dish.name}? Past orders keep their copy of it.`)) return
    try {
      await api(`/owner/menu/${dish.id}`, { method: 'DELETE' })
      // Don't leave the form editing a dish that no longer exists
      if (editingId === dish.id) reset()
      menu.reload()
    } catch (err) {
      setError(err.message)
    }
  }

  // The search box filters the already-loaded menu in the browser, no extra request
  const searchText = search.toLowerCase()
  const shown = (menu.data || []).filter((dish) => dish.name.toLowerCase().includes(searchText))

  // Form heading and submit button text depend on whether we are adding or editing
  let formTitle = 'Add a dish'
  let saveLabel = 'Add dish'
  if (editingId) {
    formTitle = `Edit ${form.name || 'dish'}`
    saveLabel = 'Save changes'
  }
  if (saving) saveLabel = 'Saving...'

  return (
    <section className="menu-admin">
      <form className="panel form" onSubmit={save}>
        <h2>{formTitle}</h2>
        <label>Name<input value={form.name} onChange={set('name')} required minLength={2} /></label>
        <label>Description<textarea rows="2" value={form.description} onChange={set('description')} /></label>
        <div className="row">
          <label className="grow">Price (₹)<input type="number" min="1" step="0.01" value={form.price} onChange={set('price')} required /></label>
          <label className="grow">Category<input value={form.category} onChange={set('category')} placeholder="e.g. Mains" /></label>
        </div>
        <label className="check"><input type="checkbox" checked={form.is_veg} onChange={set('is_veg')} />Vegetarian</label>
        <label className="check"><input type="checkbox" checked={form.is_available} onChange={set('is_available')} />Available to order</label>
        {error && <p className="form-error">{error}</p>}
        <div className="row">
          <button className="btn btn-primary" disabled={saving}>{saveLabel}</button>
          {editingId && <button type="button" className="btn btn-quiet" onClick={reset}>Cancel edit</button>}
        </div>
      </form>

      <div>
        <div className="page-head">
          <h1>Menu</h1>
          <input type="search" className="search-small" placeholder="Find a dish" value={search}
            onChange={(e) => setSearch(e.target.value)} aria-label="Find a dish" />
        </div>
        <ErrorBox message={menu.error} onRetry={menu.reload} />
        {menu.loading && !menu.data && <Loader text="Loading menu..." />}
        {menu.data && shown.length === 0 && <Empty title={search ? 'No dishes match' : 'Your menu is empty. Add your first dish.'} />}
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Dish</th><th>Category</th><th>Price</th><th>Status</th><th /></tr></thead>
            <tbody>
              {shown.map((dish) => (
                <tr key={dish.id} className={dish.is_available ? '' : 'row-off'}>
                  <td><span className={dish.is_veg ? 'veg-dot' : 'nonveg-dot'} />{dish.name}</td>
                  <td>{dish.category}</td>
                  <td>{money(dish.price)}</td>
                  <td>
                    <button className={`switch ${dish.is_available ? 'on' : ''}`} role="switch" aria-checked={dish.is_available}
                      onClick={() => toggle(dish)}>
                      {dish.is_available ? 'Available' : 'Sold out'}
                    </button>
                  </td>
                  <td className="row-actions">
                    <button className="link-button" onClick={() => startEdit(dish)}>Edit</button>
                    <button className="link-button danger" onClick={() => remove(dish)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
