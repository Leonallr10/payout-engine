import { IndianRupee, Wallet } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

function formatCurrency(paise) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format((paise ?? 0) / 100)
}

function Dashboard({ balanceData, payouts }) {
  const availableBalance = balanceData?.balance_paise ?? 0
  const heldBalance = payouts
    .filter((payout) => payout.status === 'PENDING' || payout.status === 'PROCESSING')
    .reduce((total, payout) => total + payout.amount_paise, 0)

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card className="border-border/60 bg-card/80 backdrop-blur">
        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
          <div>
            <CardDescription>Available Balance</CardDescription>
            <CardTitle className="mt-2 text-3xl">{formatCurrency(availableBalance)}</CardTitle>
          </div>
          <div className="rounded-full bg-primary/10 p-2 text-primary">
            <Wallet className="h-5 w-5" />
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {availableBalance} paise available for new payouts.
          </p>
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card/80 backdrop-blur">
        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
          <div>
            <CardDescription>Held Balance</CardDescription>
            <CardTitle className="mt-2 text-3xl">{formatCurrency(heldBalance)}</CardTitle>
          </div>
          <div className="rounded-full bg-amber-500/10 p-2 text-amber-600 dark:text-amber-400">
            <IndianRupee className="h-5 w-5" />
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Reserved in pending or processing payouts.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

export default Dashboard
