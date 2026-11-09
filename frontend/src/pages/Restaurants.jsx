// Restaurants page, public: the home page where anyone browses and searches restaurants
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { Empty, ErrorBox, Loader } from '../components/Feedback'
import Pagination from '../components/Pagination'
import useApi from '../utils/useApi'

// How long to wait after the last keystroke before searching, in milliseconds
const SEARCH_DELAY_MS = 300
// Number of restaurant cards on each page
const PAGE_SIZE = 9

// Searchable, paginated grid of restaurant cards
export default function Restaurants() {
  // searchInput follows every keystroke; search is the debounced value sent to the API
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  // Wait until the user stops typing before searching
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [searchInput])

  // Refetches whenever the search text or page changes
  const { data, loading, error, reload } = useApi(
    () => api('/restaurants', { params: { search, page, size: PAGE_SIZE } }),
    [search, page],
  )

  // Pick what to show below the search box: a loader, an empty message or the cards.
  // The loader only shows on first load so old results stay visible while paging.
  let results = null
  if (loading && !data) {
    results = <Loader text="Loading restaurants..." />
  } else if (data && data.items.length === 0) {
    results = (
      <Empty title="No restaurants match that search">
        <button className="btn btn-quiet" onClick={() => setSearchInput('')}>Show all restaurants</button>
      </Empty>
    )
  } else if (data) {
    results = (
      <>
        <div className="restaurant-grid">
          {data.items.map((restaurant) => (
            <Link key={restaurant.id} to={`/restaurants/${restaurant.id}`} className="restaurant-card">
              <span className="restaurant-initial" aria-hidden="true">{restaurant.name[0]}</span>
              <h2>{restaurant.name}</h2>
              <p className="muted">{restaurant.cuisine}</p>
              <p className="restaurant-desc">{restaurant.description}</p>
              <div className="restaurant-foot">
                <span>{restaurant.avg_rating ? `★ ${restaurant.avg_rating} (${restaurant.review_count})` : 'No ratings yet'}</span>
                <span className={restaurant.is_open ? 'open-tag' : 'closed-tag'}>{restaurant.is_open ? 'Open' : 'Closed'}</span>
              </div>
            </Link>
          ))}
        </div>
        <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />
      </>
    )
  }

  return (
    <section>
      <div className="hero">
        <h1>Hungry between classes?</h1>
        <p>Order from the kitchens around campus and follow your food all the way to your door.</p>
        <input className="search" type="search" placeholder="Search restaurants or cuisines"
          value={searchInput} onChange={(e) => setSearchInput(e.target.value)} aria-label="Search restaurants" />
      </div>

      <ErrorBox message={error} onRetry={reload} />
      {results}
    </section>
  )
}
