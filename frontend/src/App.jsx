import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { AlertCircle, CheckCircle2, Landmark } from 'lucide-react'

import Dashboard from '@/Dashboard'
import LedgerTable from '@/LedgerTable'
import PayoutForm from '@/PayoutForm'
import PayoutTable from '@/PayoutTable'
import { createPayout, fetchBalance, fetchLedger, fetchPayouts } from '@/api'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'

async function loadDashboardData(merchantId) {
  const [balance, ledger, payoutHistory] = await Promise.all([
    fetchBalance(merchantId),
    fetchLedger(merchantId),
    fetchPayouts(merchantId),
  ])

  return { balance, ledger, payoutHistory }
}

function App() {
  const [merchantId, setMerchantId] = useState('1')
  const [balanceData, setBalanceData] = useState(null)
  const [ledgerEntries, setLedgerEntries] = useState([])
  const [payouts, setPayouts] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null)

  const selectedMerchantId = useMemo(() => Number(merchantId) || 1, [merchantId])

  useEffect(() => {
    let cancelled = false

    const syncDashboard = async () => {
      setLoading(true)
      setError('')

      try {
        const { balance, ledger, payoutHistory } = await loadDashboardData(selectedMerchantId)
        if (cancelled) {
          return
        }

        setBalanceData(balance)
        setLedgerEntries(ledger)
        setPayouts(payoutHistory)
        setLastUpdatedAt(new Date())
      } catch {
        if (!cancelled) {
          setError('Could not load payout dashboard data. Check backend and CORS settings.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    syncDashboard()
    const intervalId = window.setInterval(syncDashboard, 3000)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [selectedMerchantId])

  const handlePayoutSubmit = async (payload) => {
    setSubmitting(true)
    setError('')
    setSuccess('')

    try {
      await createPayout(payload)
      setSuccess('Payout submitted successfully.')
      const { balance, ledger, payoutHistory } = await loadDashboardData(selectedMerchantId)
      setBalanceData(balance)
      setLedgerEntries(ledger)
      setPayouts(payoutHistory)
      setLastUpdatedAt(new Date())
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.detail ?? 'Failed to create payout.')
      } else {
        setError('Failed to create payout.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col border-x border-border/60 px-4 py-8 sm:px-6 lg:px-8">
        <section className="mb-6 flex flex-col gap-6 rounded-2xl border border-border/60 bg-card/80 p-6 shadow-sm backdrop-blur md:flex-row md:items-end md:justify-between">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-primary">
              <Landmark className="h-3.5 w-3.5" />
              Playto Pay
            </div>
            <div>
              <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                Payout Engine Dashboard
              </h1>
              <p className="mt-3 max-w-3xl text-sm text-muted-foreground sm:text-base">
                Track merchant balances, create payouts, inspect ledger movements, and watch
                payout statuses update live every 3 seconds.
              </p>
            </div>
          </div>

          <label className="grid gap-2 text-sm font-medium text-foreground">
            <span>Merchant ID</span>
            <Input
              type="number"
              min="1"
              value={merchantId}
              onChange={(event) => setMerchantId(event.target.value)}
              className="w-full md:w-48"
            />
          </label>
        </section>

        <div className="space-y-4">
          {error ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Request failed</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          {success ? (
            <Alert variant="success">
              <CheckCircle2 className="h-4 w-4" />
              <AlertTitle>Payout queued</AlertTitle>
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          ) : null}
        </div>

        <section className="mt-6">
          <Dashboard balanceData={balanceData} payouts={payouts} />
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <PayoutForm
            merchantId={selectedMerchantId}
            onSubmit={handlePayoutSubmit}
            submitting={submitting}
          />
          <PayoutTable payouts={payouts} loading={loading} lastUpdatedAt={lastUpdatedAt} />
        </section>

        <section className="mt-6">
          <LedgerTable entries={ledgerEntries} loading={loading} />
        </section>
      </div>
    </main>
  )
}

export default App
