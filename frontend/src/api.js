import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const fetchBalance = async (merchantId) => {
  const response = await api.get(`/merchants/${merchantId}/balance`)
  return response.data
}

export const fetchLedger = async (merchantId) => {
  const response = await api.get('/ledger', {
    params: { merchant_id: merchantId },
  })
  return response.data
}

export const fetchPayouts = async (merchantId) => {
  const response = await api.get('/payouts', {
    params: { merchant_id: merchantId },
  })
  return response.data
}

export const createPayout = async (payload) => {
  const response = await api.post('/payouts', payload)
  return response.data
}

export default api
