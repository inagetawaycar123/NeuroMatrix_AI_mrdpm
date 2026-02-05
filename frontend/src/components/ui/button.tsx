import * as React from "react"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: 'default' | 'sm' | 'lg' | 'icon'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', size = 'default', ...props }, ref) => {
    const sizeClasses = {
      default: 'h-10 px-4 py-2',
      sm: 'h-9 px-3',
      lg: 'h-11 px-8',
      icon: 'h-10 w-10'
    }

    return (
      <button
        className={`inline-flex items-center justify-center rounded-md text-sm font-medium bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 ${sizeClasses[size]} ${className}`}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }