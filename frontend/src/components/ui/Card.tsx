import * as React from "react"
import { cn } from "../../lib/utils"

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'glass' | 'solid'
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'glass', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-2xl transition-all overflow-hidden",
          variant === 'glass'
            ? "bg-white/10 backdrop-blur-lg border border-white/20 shadow-xl"
            : "bg-slate-800 border border-slate-700 shadow-md",
          className
        )}
        {...props}
      />
    )
  }
)
Card.displayName = "Card"

const CardHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("p-6 pb-3", className)} {...props} />
)

const CardTitle = ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={cn("text-2xl font-bold text-white", className)} {...props} />
)

const CardContent = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("p-6 pt-0", className)} {...props} />
)

export { Card, CardHeader, CardTitle, CardContent }
