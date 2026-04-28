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

function LedgerTable({ entries, loading }) {
  return (
    <Card className="border-border/60 bg-card/80 backdrop-blur">
      <CardHeader>
        <CardDescription>Transactions</CardDescription>
        <CardTitle>Ledger History</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Reference</TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="text-right">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {!loading && entries.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground">
                  No ledger activity yet.
                </TableCell>
              </TableRow>
            ) : null}

            {entries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="font-medium">{entry.reference}</TableCell>
                <TableCell>
                  <Badge variant={entry.entry_type === 'CREDIT' ? 'success' : 'destructive'}>
                    {entry.entry_type}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">{formatCurrency(entry.amount_paise)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

export default LedgerTable
