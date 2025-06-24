import React from 'react'
import { cn } from '../../lib/utils'

// Checkbox Component
export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  color?: 'primary' | 'secondary' | 'accent' | 'neutral' | 'success' | 'warning' | 'info' | 'error'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, color, size, ...props }, ref) => {
    return (
      <input
        type="checkbox"
        className={cn(
          'checkbox',
          color && `checkbox-${color}`,
          size && `checkbox-${size}`,
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Checkbox.displayName = 'Checkbox'

// File Input Component
export interface FileInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  styleVariant?: 'ghost'
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
}

export const FileInput = React.forwardRef<HTMLInputElement, FileInputProps>(
  ({ className, styleVariant, color, size, ...props }, ref) => {
    return (
      <input
        type="file"
        className={cn(
          'file-input',
          styleVariant && `file-input-${styleVariant}`,
          color && `file-input-${color}`,
          size && `file-input-${size}`,
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
FileInput.displayName = 'FileInput'

// Input Component
export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  styleVariant?: 'ghost'
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, styleVariant, color, size, ...props }, ref) => {
    return (
      <input
        className={cn(
          'input',
          styleVariant && `input-${styleVariant}`,
          color && `input-${color}`,
          size && `input-${size}`,
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = 'Input'

// Label Component
export interface LabelProps {
  children: React.ReactNode
  text: string
  className?: string
}

export const Label: React.FC<LabelProps> = ({ children, text, className }) => {
  return (
    <label className={cn('input', className)}>
      <span className="label">{text}</span>
      {children}
    </label>
  )
}

// Floating Label Component
export interface FloatingLabelProps {
  children: React.ReactNode
  text: string
  className?: string
}

export const FloatingLabel: React.FC<FloatingLabelProps> = ({ children, text, className }) => {
  return (
    <label className={cn('floating-label', className)}>
      {children}
      <span>{text}</span>
    </label>
  )
}

// Radio Component
export interface RadioProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'success' | 'warning' | 'info' | 'error'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
}

export const Radio = React.forwardRef<HTMLInputElement, RadioProps>(
  ({ className, color, size, ...props }, ref) => {
    return (
      <input
        type="radio"
        className={cn(
          'radio',
          color && `radio-${color}`,
          size && `radio-${size}`,
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Radio.displayName = 'Radio'

// Range Component
export interface RangeProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'success' | 'warning' | 'info' | 'error'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
}

export const Range = React.forwardRef<HTMLInputElement, RangeProps>(
  ({ className, color, size, ...props }, ref) => {
    return (
      <input
        type="range"
        className={cn(
          'range',
          color && `range-${color}`,
          size && `range-${size}`,
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Range.displayName = 'Range'

// Rating Component
export interface RatingProps {
  name: string
  value?: number
  onChange?: (value: number) => void
  half?: boolean
  hidden?: boolean
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  max?: number
  className?: string
}

export const Rating: React.FC<RatingProps> = ({
  name,
  value = 0,
  onChange,
  half,
  hidden,
  size,
  max = 5,
  className
}) => {
  return (
    <div className={cn('rating', half && 'rating-half', size && `rating-${size}`, className)}>
      {hidden && (
        <input
          type="radio"
          name={name}
          className="rating-hidden"
          checked={value === 0}
          onChange={() => onChange?.(0)}
        />
      )}
      {Array.from({ length: max }, (_, i) => (
        <input
          key={i}
          type="radio"
          name={name}
          className="mask mask-star"
          checked={value === i + 1}
          onChange={() => onChange?.(i + 1)}
        />
      ))}
    </div>
  )
}

// Select Component
export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  styleVariant?: 'ghost'
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  children: React.ReactNode
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, styleVariant, color, size, children, ...props }, ref) => {
    return (
      <select
        className={cn(
          'select',
          styleVariant && `select-${styleVariant}`,
          color && `select-${color}`,
          size && `select-${size}`,
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </select>
    )
  }
)
Select.displayName = 'Select'

// Textarea Component
export interface TextareaProps extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, 'size'> {
  styleVariant?: 'ghost'
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, styleVariant, color, size, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          'textarea',
          styleVariant && `textarea-${styleVariant}`,
          color && `textarea-${color}`,
          size && `textarea-${size}`,
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Textarea.displayName = 'Textarea'

// Toggle Component
export interface ToggleProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  color?: 'primary' | 'secondary' | 'accent' | 'neutral' | 'success' | 'warning' | 'info' | 'error'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
}

export const Toggle = React.forwardRef<HTMLInputElement, ToggleProps>(
  ({ className, color, size, ...props }, ref) => {
    return (
      <input
        type="checkbox"
        className={cn(
          'toggle',
          color && `toggle-${color}`,
          size && `toggle-${size}`,
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Toggle.displayName = 'Toggle'

// Fieldset Component
export interface FieldsetProps {
  legend: string
  children: React.ReactNode
  description?: string
  className?: string
}

export const Fieldset: React.FC<FieldsetProps> = ({ legend, children, description, className }) => {
  return (
    <fieldset className={cn('fieldset', className)}>
      <legend className="fieldset-legend">{legend}</legend>
      {children}
      {description && <p className="label">{description}</p>}
    </fieldset>
  )
}

// Validator Component
export interface ValidatorProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  hint?: string
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
}

export const Validator = React.forwardRef<HTMLInputElement, ValidatorProps>(
  ({ className, hint, size, ...props }, ref) => {
    return (
      <div>
        <input
          className={cn('input validator', size && `input-${size}`, className)}
          ref={ref}
          {...props}
        />
        {hint && <p className="validator-hint">{hint}</p>}
      </div>
    )
  }
)
Validator.displayName = 'Validator'
