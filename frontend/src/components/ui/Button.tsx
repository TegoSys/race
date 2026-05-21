import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cn } from "../../lib/utils"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', asChild = false, ...props }, ref) => {
    const SlotComponent = asChild ? Slot : "button"

    const variants = {
      primary: "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20",
      secondary: "bg-white/10 hover:bg-white/20 text-white backdrop-blur-md border border-white/20",
      ghost: "hover:bg-white/10 text-slate-300 hover:text-white",
      outline: "border border-white/20 hover:bg-white/10 text-white backdrop-blur-sm"
    }

    const sizes = {
      sm: "px-3 py-1.5 text-sm",
      md: "px-4 py-2",
      lg: "px-6 py-3 text-lg"
    }

    return (
      <SlotComponent
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-full font-medium transition-all active:scale-95",
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
