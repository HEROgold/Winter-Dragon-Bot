import React from 'react'
import { cn } from '../../lib/utils'

// Alert Component
export interface AlertProps {
  children: React.ReactNode
  variant?: 'info' | 'success' | 'warning' | 'error'
  styleVariant?: 'outline' | 'dash' | 'soft'
  direction?: 'vertical' | 'horizontal'
  className?: string
}

export const Alert: React.FC<AlertProps> = ({
  children,
  variant,
  styleVariant,
  direction,
  className
}) => {
  return (
    <div
      role="alert"
      className={cn(
        'alert',
        variant && `alert-${variant}`,
        styleVariant && `alert-${styleVariant}`,
        direction && `alert-${direction}`,
        className
      )}
    >
      {children}
    </div>
  )
}

// Loading Component
export interface LoadingProps {
  variant?: 'spinner' | 'dots' | 'ring' | 'ball' | 'bars' | 'infinity'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export const Loading: React.FC<LoadingProps> = ({ variant = 'spinner', size, className }) => {
  return (
    <span
      className={cn(
        'loading',
        `loading-${variant}`,
        size && `loading-${size}`,
        className
      )}
    ></span>
  )
}

// Progress Component
export interface ProgressProps extends React.ProgressHTMLAttributes<HTMLProgressElement> {
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error'
}

export const Progress = React.forwardRef<HTMLProgressElement, ProgressProps>(
  ({ className, color, ...props }, ref) => {
    return (
      <progress
        className={cn('progress', color && `progress-${color}`, className)}
        ref={ref}
        {...props}
      />
    )
  }
)
Progress.displayName = 'Progress'

// Radial Progress Component
export interface RadialProgressProps {
  value: number
  size?: string
  thickness?: string
  children?: React.ReactNode
  className?: string
}

export const RadialProgress: React.FC<RadialProgressProps> = ({
  value,
  size = '5rem',
  thickness,
  children,
  className
}) => {
  const style = {
    '--value': value,
    '--size': size,
    ...(thickness && { '--thickness': thickness })
  } as React.CSSProperties

  return (
    <div
      className={cn('radial-progress', className)}
      style={style}
      role="progressbar"
      aria-valuenow={value}
    >
      {children ?? `${value}%`}
    </div>
  )
}

// Skeleton Component
export interface SkeletonProps {
  className?: string
  width?: string
  height?: string
}

export const Skeleton: React.FC<SkeletonProps> = ({ className, width, height }) => {
  return (
    <div
      className={cn('skeleton', width, height, className)}
    ></div>
  )
}

// Toast Component
export interface ToastProps {
  children: React.ReactNode
  placement?: 'start' | 'center' | 'end' | 'top' | 'middle' | 'bottom'
  className?: string
}

export const Toast: React.FC<ToastProps> = ({ children, placement, className }) => {
  return (
    <div className={cn('toast', placement && `toast-${placement}`, className)}>
      {children}
    </div>
  )
}

// Modal Component
export interface ModalProps {
  children: React.ReactNode
  id: string
  placement?: 'top' | 'middle' | 'bottom' | 'start' | 'end'
  open?: boolean
  className?: string
}

export const Modal: React.FC<ModalProps> = ({
  children,
  id,
  placement,
  open,
  className
}) => {
  return (
    <dialog
      id={id}
      className={cn('modal', placement && `modal-${placement}`, open && 'modal-open', className)}
    >
      <div className="modal-box">
        {children}
      </div>
      <form method="dialog" className="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
  )
}

// Modal Action Component
export interface ModalActionProps {
  children: React.ReactNode
  className?: string
}

export const ModalAction: React.FC<ModalActionProps> = ({ children, className }) => {
  return <div className={cn('modal-action', className)}>{children}</div>
}

// Modal Toggle (Legacy)
export interface ModalToggleProps {
  children: React.ReactNode
  modalId: string
  className?: string
}

export const ModalToggle: React.FC<ModalToggleProps> = ({ children, modalId, className }) => {
  return (
    <>
      <label htmlFor={modalId} className={cn('btn', className)}>
        {children}
      </label>
      <input type="checkbox" id={modalId} className="modal-toggle" />
    </>
  )
}

// Status Component
export interface StatusProps {
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export const Status: React.FC<StatusProps> = ({ color, size, className }) => {
  return (
    <span
      className={cn(
        'status',
        color && `status-${color}`,
        size && `status-${size}`,
        className
      )}
    ></span>
  )
}

// Tooltip Component
export interface TooltipProps {
  children: React.ReactNode
  tip: string
  position?: 'top' | 'bottom' | 'left' | 'right'
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error'
  open?: boolean
  className?: string
}

export const Tooltip: React.FC<TooltipProps> = ({
  children,
  tip,
  position = 'top',
  color,
  open,
  className
}) => {
  return (
    <div
      className={cn(
        'tooltip',
        `tooltip-${position}`,
        color && `tooltip-${color}`,
        open && 'tooltip-open',
        className
      )}
      data-tip={tip}
    >
      {children}
    </div>
  )
}
