import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

function formatCurrency(paise) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format((paise ?? 0) / 100)
}

function PayoutTable({ payouts, loading, lastUpdatedAt }) {
  const statusVariant = (status) => {
    if (status === 'COMPLETED') return 'success'
    if (status === 'FAILED') return 'destructive'
    return 'warning'
  }

  return (
    <Card className="border-border/60 bg-card/80 backdrop-blur">
      <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardDescription>Payout Processing</CardDescription>
          <CardTitle>Payout History</CardTitle>
        </div>
        <span className="text-sm text-muted-foreground">
          {lastUpdatedAt ? `Updated ${lastUpdatedAt.toLocaleTimeString()}` : 'Waiting for data'}
        </span>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Bank Account</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Attempts</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {!loading && payouts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  No payouts created yet.
                </TableCell>
              </TableRow>
            ) : null}

            {payouts.map((payout) => (
              <TableRow key={payout.id}>
                <TableCell className="font-medium">#{payout.id}</TableCell>
                <TableCell>{payout.bank_account_id}</TableCell>
                <TableCell className="text-right">{formatCurrency(payout.amount_paise)}</TableCell>
                <TableCell>
                  <Badge variant={statusVariant(payout.status)}>{payout.status}</Badge>
                </TableCell>
                <TableCell className="text-right">{payout.attempts}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

export default PayoutTable
