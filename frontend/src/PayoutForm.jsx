import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

function PayoutForm({ merchantId, onSubmit, submitting }) {
  const [amount, setAmount] = useState('')
  const [bankAccountId, setBankAccountId] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()

    await onSubmit({
      merchant_id: merchantId,
      amount_paise: Number(amount),
      bank_account_id: bankAccountId,
      idempotency_key: `merchant-${merchantId}-${Date.now()}`,
    })

    setAmount('')
    setBankAccountId('')
  }

  return (
    <Card className="border-border/60 bg-card/80 backdrop-blur">
      <CardHeader>
        <CardDescription>Create Transfer</CardDescription>
        <CardTitle>New Payout</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label htmlFor="amount" className="text-sm font-medium text-foreground">
              Amount (paise)
            </label>
            <Input
              id="amount"
              type="number"
              min="1"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="5000"
              required
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="bank-account" className="text-sm font-medium text-foreground">
              Bank Account ID
            </label>
            <Input
              id="bank-account"
              type="text"
              value={bankAccountId}
              onChange={(event) => setBankAccountId(event.target.value)}
              placeholder="bank_acc_001"
              required
            />
          </div>

          <Button type="submit" className="w-full" size="lg" disabled={submitting}>
            {submitting ? 'Submitting...' : 'Create Payout'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

export default PayoutForm
