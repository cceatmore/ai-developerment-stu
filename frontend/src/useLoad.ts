import { useCallback, useEffect, useState } from 'react'
import { api } from './api'

export function useLoad<T>(url: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const reload = useCallback(async () => {
    if (!url) return
    setLoading(true)
    try {
      setData(await api.get<T>(url))
      setError(null)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [url])

  useEffect(() => {
    setData(null)
    reload()
  }, [reload])

  return { data, error, loading, reload, setData }
}
