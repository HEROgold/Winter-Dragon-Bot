import React from 'react'
import { cn } from '../../lib/utils'

// Breadcrumbs Component
export interface BreadcrumbsProps {
  children: React.ReactNode
  className?: string
}

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ children, className }) => {
  return (
    <div className={cn('breadcrumbs text-sm', className)}>
      <ul>{children}</ul>
    </div>
  )
}

// Breadcrumb Item Component
export interface BreadcrumbItemProps {
  children: React.ReactNode
  href?: string
  className?: string
}

export const BreadcrumbItem: React.FC<BreadcrumbItemProps> = ({ children, href, className }) => {
  return (
    <li className={className}>
      {href ? <a href={href}>{children}</a> : <span>{children}</span>}
    </li>
  )
}

// Link Component
export interface LinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'success' | 'info' | 'warning' | 'error'
  hover?: boolean
  children: React.ReactNode
}

export const Link = React.forwardRef<HTMLAnchorElement, LinkProps>(
  ({ className, color, hover, children, ...props }, ref) => {
    return (
      <a
        className={cn(
          'link',
          color && `link-${color}`,
          hover && 'link-hover',
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </a>
    )
  }
)
Link.displayName = 'Link'

// Menu Component
export interface MenuProps {
  children: React.ReactNode
  direction?: 'vertical' | 'horizontal'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export const Menu: React.FC<MenuProps> = ({ children, direction, size, className }) => {
  return (
    <ul
      className={cn(
        'menu',
        direction && `menu-${direction}`,
        size && `menu-${size}`,
        'bg-base-200 rounded-box',
        className
      )}
    >
      {children}
    </ul>
  )
}

// Menu Item Component
export interface MenuItemProps {
  children: React.ReactNode
  disabled?: boolean
  active?: boolean
  focus?: boolean
  className?: string
  onClick?: () => void
}

export const MenuItem: React.FC<MenuItemProps> = ({
  children,
  disabled,
  active,
  focus,
  className,
  onClick
}) => {
  return (
    <li
      className={cn(
        disabled && 'menu-disabled',
        active && 'menu-active',
        focus && 'menu-focus',
        className
      )}
    >
      {onClick ? (
        <button onClick={onClick} disabled={disabled}>
          {children}
        </button>
      ) : (
        children
      )}
    </li>
  )
}

// Menu Title Component
export interface MenuTitleProps {
  children: React.ReactNode
  className?: string
}

export const MenuTitle: React.FC<MenuTitleProps> = ({ children, className }) => {
  return <li className={cn('menu-title', className)}>{children}</li>
}

// Navbar Component
export interface NavbarProps {
  children: React.ReactNode
  className?: string
}

export const Navbar: React.FC<NavbarProps> = ({ children, className }) => {
  return (
    <div className={cn('navbar bg-base-100', className)}>
      {children}
    </div>
  )
}

// Navbar Start Component
export interface NavbarStartProps {
  children: React.ReactNode
  className?: string
}

export const NavbarStart: React.FC<NavbarStartProps> = ({ children, className }) => {
  return <div className={cn('navbar-start', className)}>{children}</div>
}

// Navbar Center Component
export interface NavbarCenterProps {
  children: React.ReactNode
  className?: string
}

export const NavbarCenter: React.FC<NavbarCenterProps> = ({ children, className }) => {
  return <div className={cn('navbar-center', className)}>{children}</div>
}

// Navbar End Component
export interface NavbarEndProps {
  children: React.ReactNode
  className?: string
}

export const NavbarEnd: React.FC<NavbarEndProps> = ({ children, className }) => {
  return <div className={cn('navbar-end', className)}>{children}</div>
}

// Pagination Component
export interface PaginationProps {
  children: React.ReactNode
  direction?: 'vertical' | 'horizontal'
  className?: string
}

export const Pagination: React.FC<PaginationProps> = ({ children, direction, className }) => {
  return (
    <div className={cn('join', direction && `join-${direction}`, className)}>
      {children}
    </div>
  )
}

// Pagination Item Component
export interface PaginationItemProps {
  children: React.ReactNode
  active?: boolean
  disabled?: boolean
  onClick?: () => void
  className?: string
}

export const PaginationItem: React.FC<PaginationItemProps> = ({
  children,
  active,
  disabled,
  onClick,
  className
}) => {
  return (
    <button
      className={cn(
        'join-item btn',
        active && 'btn-active',
        disabled && 'btn-disabled',
        className
      )}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  )
}

// Steps Component
export interface StepsProps {
  children: React.ReactNode
  direction?: 'vertical' | 'horizontal'
  className?: string
}

export const Steps: React.FC<StepsProps> = ({ children, direction, className }) => {
  return (
    <ul className={cn('steps', direction && `steps-${direction}`, className)}>
      {children}
    </ul>
  )
}

// Step Component
export interface StepProps {
  children: React.ReactNode
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error'
  dataContent?: string
  className?: string
}

export const Step: React.FC<StepProps> = ({ children, color, dataContent, className }) => {
  return (
    <li
      className={cn('step', color && `step-${color}`, className)}
      data-content={dataContent}
    >
      {children}
    </li>
  )
}

// Tab Component
export interface TabProps {
  children: React.ReactNode
  styleVariant?: 'box' | 'border' | 'lift'
  placement?: 'top' | 'bottom'
  className?: string
}

export const Tabs: React.FC<TabProps> = ({ children, styleVariant, placement, className }) => {
  return (
    <div
      role="tablist"
      className={cn(
        'tabs',
        styleVariant && `tabs-${styleVariant}`,
        placement && `tabs-${placement}`,
        className
      )}
    >
      {children}
    </div>
  )
}

// Tab Item Component
export interface TabItemProps {
  children: React.ReactNode
  active?: boolean
  disabled?: boolean
  name?: string
  className?: string
}

export const TabItem: React.FC<TabItemProps> = ({
  children,
  active,
  disabled,
  name,
  className
}) => {
  return (
    <input
      type="radio"
      name={name}
      role="tab"
      className={cn(
        'tab',
        active && 'tab-active',
        disabled && 'tab-disabled',
        className
      )}
      aria-label={typeof children === 'string' ? children : undefined}
      defaultChecked={active}
    />
  )
}

// Dock Component
export interface DockProps {
  children: React.ReactNode
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export const Dock: React.FC<DockProps> = ({ children, size, className }) => {
  return (
    <div className={cn('dock', size && `dock-${size}`, className)}>
      {children}
    </div>
  )
}

// Dock Item Component
export interface DockItemProps {
  children: React.ReactNode
  label?: string
  active?: boolean
  onClick?: () => void
  className?: string
}

export const DockItem: React.FC<DockItemProps> = ({
  children,
  label,
  active,
  onClick,
  className
}) => {
  return (
    <button
      className={cn(active && 'dock-active', className)}
      onClick={onClick}
    >
      {children}
      {label && <span className="dock-label">{label}</span>}
    </button>
  )
}

// Filter Component
export interface FilterProps {
  children: React.ReactNode
  name: string
  className?: string
}

export const Filter: React.FC<FilterProps> = ({ children, name, className }) => {
  return (
    <form className={cn('filter', className)}>
      <input
        className="btn btn-square"
        type="reset"
        value="×"
        aria-label="Reset filter"
      />
      {React.Children.map(children, (child, index) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, { name, key: index } as any)
        }
        return child
      })}
    </form>
  )
}

// Filter Item Component
export interface FilterItemProps {
  children: React.ReactNode
  name?: string
  value: string
  className?: string
}

export const FilterItem: React.FC<FilterItemProps> = ({
  children,
  name,
  value,
  className
}) => {
  return (
    <input
      className={cn('btn', className)}
      type="radio"
      name={name}
      value={value}
      aria-label={typeof children === 'string' ? children : value}
    />
  )
}
