import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "../../lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border border-white/10 px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-canvas",
  {
    variants: {
      variant: {
        default: "bg-surface-elevated text-text-primary",
        cognitive: "bg-[var(--eureka-cognitive)]/10 text-[var(--eureka-cognitive)] border-[var(--eureka-cognitive)]/20",
        scientific: "bg-[var(--eureka-scientific)]/10 text-[var(--eureka-scientific)] border-[var(--eureka-scientific)]/20",
        governance: "bg-[var(--eureka-governance)]/10 text-[var(--eureka-governance)] border-[var(--eureka-governance)]/20",
        human: "bg-[var(--eureka-human)]/10 text-[var(--eureka-human)] border-[var(--eureka-human)]/20",
        frozen: "bg-[var(--eureka-frozen)]/10 text-[var(--eureka-frozen)] border-[var(--eureka-frozen)]/20",
        authorized: "bg-[var(--eureka-authorized)]/10 text-[var(--eureka-authorized)] border-[var(--eureka-authorized)]/20",
        blocked: "bg-[var(--eureka-blocked)]/10 text-[var(--eureka-blocked)] border-[var(--eureka-blocked)]/20",
        neutral: "bg-surface-elevated text-text-muted border-border",
        outline: "text-text-primary",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
