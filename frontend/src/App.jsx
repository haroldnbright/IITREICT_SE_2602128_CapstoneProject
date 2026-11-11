// Top-level layout and the route table for every page in the app
import { Navigate, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import { HOME_BY_ROLE, useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Restaurants from './pages/Restaurants'
import RestaurantMenu from './pages/RestaurantMenu'
import Cart from './pages/customer/Cart'
import CustomerDashboard from './pages/customer/CustomerDashboard'
import OrderDetail from './pages/customer/OrderDetail'
import AIInsights from './pages/customer/AIInsights'
import OwnerDashboard from './pages/owner/OwnerDashboard'
import OwnerOrders from './pages/owner/OwnerOrders'
import MenuManagement from './pages/owner/MenuManagement'
import DeliveryDashboard from './pages/delivery/DeliveryDashboard'
import NotFound from './pages/NotFound'

// Sends "/" to the logged-in user's home page, or to the restaurant list for guests
function Home() {
  const { user } = useAuth()
  return <Navigate to={user ? HOME_BY_ROLE[user.role] : '/restaurants'} replace />
}

// Renders the navbar and picks the page for the current URL
// Customer, owner and delivery pages are grouped under a ProtectedRoute that checks the role
export default function App() {
  return (
    <>
      <Navbar />
      <main className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/restaurants" element={<Restaurants />} />
          <Route path="/restaurants/:id" element={<RestaurantMenu />} />

          {/* Pages below need a logged-in user with the matching role */}
          <Route element={<ProtectedRoute roles={['customer']} />}>
            <Route path="/cart" element={<Cart />} />
            <Route path="/orders" element={<CustomerDashboard />} />
            <Route path="/orders/:id" element={<OrderDetail />} />
            <Route path="/insights" element={<AIInsights />} />
          </Route>

          <Route element={<ProtectedRoute roles={['owner']} />}>
            <Route path="/owner" element={<OwnerDashboard />} />
            <Route path="/owner/orders" element={<OwnerOrders />} />
            <Route path="/owner/menu" element={<MenuManagement />} />
          </Route>

          <Route element={<ProtectedRoute roles={['delivery']} />}>
            <Route path="/delivery" element={<DeliveryDashboard />} />
          </Route>

          {/* Any other URL shows the 404 page */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  )
}
