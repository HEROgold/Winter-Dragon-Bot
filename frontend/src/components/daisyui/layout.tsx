import React from 'react'
import { cn } from '../../lib/utils'

// Divider Component
export interface DividerProps {
  children?: React.ReactNode
  color?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'success' | 'warning' | 'info' | 'error'
  direction?: 'vertical' | 'horizontal'
  placement?: 'start' | 'end'
  className?: string
}

export const Divider: React.FC<DividerProps> = ({
  children,
  color,
  direction,
  placement,
  className
}) => {
  return (
    <div
      className={cn(
        'divider',
        color && `divider-${color}`,
        direction && `divider-${direction}`,
        placement && `divider-${placement}`,
        className
      )}
    >
      {children}
    </div>
  )
}

// Drawer Component
export interface DrawerProps {
  children: React.ReactNode
  sidebar: React.ReactNode
  id: string
  end?: boolean
  open?: boolean
  className?: string
}

export const Drawer: React.FC<DrawerProps> = ({
  children,
  sidebar,
  id,
  end,
  open,
  className
}) => {
  return (
    <div className={cn('drawer', end && 'drawer-end', open && 'drawer-open', className)}>
      <input id={id} type="checkbox" className="drawer-toggle" />
      <div className="drawer-content">{children}</div>
      <div className="drawer-side">
        <label htmlFor={id} aria-label="close sidebar" className="drawer-overlay"></label>
        {sidebar}
      </div>
    </div>
  )
}

// Drawer Toggle Button Component
export interface DrawerToggleProps {
  drawerId: string
  children: React.ReactNode
  className?: string
}

export const DrawerToggle: React.FC<DrawerToggleProps> = ({ drawerId, children, className }) => {
  return (
    <label htmlFor={drawerId} className={cn('btn drawer-button', className)}>
      {children}
    </label>
  )
}

// Footer Component
export interface FooterProps {
  children: React.ReactNode
  center?: boolean
  direction?: 'horizontal' | 'vertical'
  className?: string
}

export const Footer: React.FC<FooterProps> = ({ children, center, direction, className }) => {
  return (
    <footer
      className={cn(
        'footer',
        center && 'footer-center',
        direction && `footer-${direction}`,
        'p-10 bg-base-200 text-base-content',
        className
      )}
    >
      {children}
    </footer>
  )
}

// Footer Title Component
export interface FooterTitleProps {
  children: React.ReactNode
  className?: string
}

export const FooterTitle: React.FC<FooterTitleProps> = ({ children, className }) => {
  return <h6 className={cn('footer-title', className)}>{children}</h6>
}

// Hero Component
export interface HeroProps {
  children: React.ReactNode
  overlay?: boolean
  className?: string
}

export const Hero: React.FC<HeroProps> = ({ children, overlay, className }) => {
  return (
    <div className={cn('hero min-h-screen', className)}>
      {overlay && <div className="hero-overlay bg-opacity-60"></div>}
      <div className="hero-content text-center">
        {children}
      </div>
    </div>
  )
}

// Indicator Component
export interface IndicatorProps {
  children: React.ReactNode
  className?: string
}

export const Indicator: React.FC<IndicatorProps> = ({ children, className }) => {
  return <div className={cn('indicator', className)}>{children}</div>
}

// Indicator Item Component
export interface IndicatorItemProps {
  children: React.ReactNode
  placement?: 'start' | 'center' | 'end' | 'top' | 'middle' | 'bottom'
  className?: string
}

export const IndicatorItem: React.FC<IndicatorItemProps> = ({
  children,
  placement,
  className
}) => {
  return (
    <span
      className={cn(
        'indicator-item',
        placement && `indicator-${placement}`,
        className
      )}
    >
      {children}
    </span>
  )
}

// Join Component
export interface JoinProps {
  children: React.ReactNode
  direction?: 'vertical' | 'horizontal'
  className?: string
}

export const Join: React.FC<JoinProps> = ({ children, direction, className }) => {
  return (
    <div className={cn('join', direction && `join-${direction}`, className)}>
      {children}
    </div>
  )
}

// Join Item Component
export interface JoinItemProps {
  children: React.ReactNode
  className?: string
}

export const JoinItem: React.FC<JoinItemProps> = ({ children, className }) => {
  return <div className={cn('join-item', className)}>{children}</div>
}

// Mask Component
export interface MaskProps {
  children: React.ReactNode
  variant: 'squircle' | 'heart' | 'hexagon' | 'hexagon-2' | 'decagon' | 'pentagon' | 'diamond' | 'square' | 'circle' | 'star' | 'star-2' | 'triangle' | 'triangle-2' | 'triangle-3' | 'triangle-4'
  half?: '1' | '2'
  className?: string
}

export const Mask: React.FC<MaskProps> = ({ children, variant, half, className }) => {
  return (
    <div
      className={cn(
        'mask',
        `mask-${variant}`,
        half && `mask-half-${half}`,
        className
      )}
    >
      {children}
    </div>
  )
}

// Stack Component
export interface StackProps {
  children: React.ReactNode
  placement?: 'top' | 'bottom' | 'start' | 'end'
  className?: string
}

export const Stack: React.FC<StackProps> = ({ children, placement, className }) => {
  return (
    <div className={cn('stack', placement && `stack-${placement}`, className)}>
      {children}
    </div>
  )
}

// Carousel Component
export interface CarouselProps {
  children: React.ReactNode
  direction?: 'horizontal' | 'vertical'
  modifier?: 'start' | 'center' | 'end'
  className?: string
}

export const Carousel: React.FC<CarouselProps> = ({
  children,
  direction,
  modifier,
  className
}) => {
  return (
    <div
      className={cn(
        'carousel',
        direction && `carousel-${direction}`,
        modifier && `carousel-${modifier}`,
        className
      )}
    >
      {children}
    </div>
  )
}

// Carousel Item Component
export interface CarouselItemProps {
  children: React.ReactNode
  id?: string
  className?: string
}

export const CarouselItem: React.FC<CarouselItemProps> = ({ children, id, className }) => {
  return (
    <div id={id} className={cn('carousel-item', className)}>
      {children}
    </div>
  )
}
