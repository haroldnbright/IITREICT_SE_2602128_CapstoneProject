// Not found page, public: shown for any URL that doesn't match a route
import { Link } from 'react-router-dom'

// Simple 404 message with a link back home
export default function NotFound() {
  return (
    <section className="narrow center">
      <h1>Page not found</h1>
      <p className="muted">The link may be old or mistyped.</p>
      <Link to="/" className="btn btn-primary">Go to the home page</Link>
    </section>
  )
}
