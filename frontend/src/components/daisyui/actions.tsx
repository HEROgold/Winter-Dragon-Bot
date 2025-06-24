import React from 'react'
import { cn } from '../../lib/utils'

// Button Component
export interface ButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'style'> {
  variant?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error'
  styleVariant?: 'outline' | 'dash' | 'soft' | 'ghost' | 'link'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  modifier?: 'wide' | 'block' | 'square' | 'circle'
  loading?: boolean
  disabled?: boolean
  active?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, styleVariant, size, modifier, loading, active, children, disabled, ...props }, ref) => {
    return (
      <button
        className={cn(
          'btn',
          variant && `btn-${variant}`,
          styleVariant && `btn-${styleVariant}`,
          size && `btn-${size}`,
          modifier && `btn-${modifier}`,
          active && 'btn-active',
          loading && 'loading',
          className
        )}
        ref={ref}
        disabled={disabled}
        {...props}
      >
        {loading ? <span className="loading loading-spinner"></span> : children}
      </button>
    )
  }
)
Button.displayName = 'Button'

// Dropdown Component
export interface DropdownProps {
  children: React.ReactNode
  content: React.ReactNode
  placement?: 'start' | 'center' | 'end' | 'top' | 'bottom' | 'left' | 'right'
  modifier?: 'hover' | 'open'
  className?: string
}

export const Dropdown: React.FC<DropdownProps> = ({
  children,
  content,
  placement,
  modifier,
  className
}) => {
  return (
    <div className={cn('dropdown', placement && `dropdown-${placement}`, modifier && `dropdown-${modifier}`, className)}>
      <div tabIndex={0} role="button" className="m-1">
        {children}
      </div>
      <ul tabIndex={0} className="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
        {content}
      </ul>
    </div>
  )
}

// Swap Component
export interface SwapProps {
  children: [React.ReactNode, React.ReactNode]
  style?: 'rotate' | 'flip'
  active?: boolean
  indeterminate?: React.ReactNode
  className?: string
  onChange?: (checked: boolean) => void
}

export const Swap: React.FC<SwapProps> = ({
  children,
  style,
  active,
  indeterminate,
  className,
  onChange
}) => {
  const [swapOn, swapOff] = children

  return (
    <label className={cn('swap', style && `swap-${style}`, active && 'swap-active', className)}>
      <input 
        type="checkbox" 
        onChange={(e) => onChange?.(e.target.checked)}
        defaultChecked={active}
      />
      <div className="swap-on">{swapOn}</div>
      <div className="swap-off">{swapOff}</div>
      {indeterminate && <div className="swap-indeterminate">{indeterminate}</div>}
    </label>
  )
}

// Theme Controller Component
export interface ThemeControllerProps {
  theme: string
  checked?: boolean
  onChange?: (checked: boolean) => void
  className?: string
}

export const ThemeController: React.FC<ThemeControllerProps> = ({
  theme,
  checked,
  onChange,
  className
}) => {
  return (
    <input
      type="checkbox"
      value={theme}
      className={cn('theme-controller', className)}
      checked={checked}
      onChange={(e) => onChange?.(e.target.checked)}
    />
  )
}
