// Custom hook for loading data from the API with shared loading and error state
import { useCallback, useEffect, useState } from 'react'

// Loads data when the component mounts (and when `deps` change).
// Returns { data, loading, error, reload } so every page handles loading and errors the same way.
export default function useApi(loader, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Only rebuild the loader when the caller's deps change, not on every render
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(loader, deps)

  // Runs the loader again, resetting the error and showing the loading state
  const reload = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await load())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [load])

  // Load on mount and whenever the loader changes
  useEffect(() => {
    reload()
  }, [reload])

  // setData lets pages update the loaded data locally after an action
  return { data, setData, loading, error, reload }
}
