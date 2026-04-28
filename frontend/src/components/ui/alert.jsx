import { cva } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const alertVariants = cva(
  'relative w-full rounded-lg border px-4 py-3 text-sm [&>svg~*]:pl-7',
  {
    variants: {
      variant: {
        default: 'bg-background text-foreground',
        destructive: 'border-destructive/50 text-destructive dark:border-destructive',
        success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

function Alert({ className, variant, ...props }) {
  return <div role="alert" className={cn(alertVariants({ variant }), className)} {...props} />
}

function AlertTitle({ className, ...props }) {
  return <h5 className={cn('mb-1 font-medium leading-none tracking-tight', className)} {...props} />
}

function AlertDescription({ className, ...props }) {
  return <div className={cn('text-sm [&_p]:leading-relaxed', className)} {...props} />
}

export { Alert, AlertDescription, AlertTitle }
