import React from 'react'
import { cn } from '../../lib/utils'

// Accordion/Collapse Component
export interface AccordionProps {
  children: React.ReactNode
  title: string
  modifier?: 'arrow' | 'plus'
  open?: boolean
  close?: boolean
  name?: string
  checked?: boolean
  className?: string
}

export const Accordion: React.FC<AccordionProps> = ({
  children,
  title,
  modifier,
  open,
  close,
  name,
  checked,
  className
}) => {
  return (
    <div className={cn('collapse', modifier && `collapse-${modifier}`, open && 'collapse-open', close && 'collapse-close', className)}>
      <input type="radio" name={name} defaultChecked={checked} />
      <div className="collapse-title text-xl font-medium">{title}</div>
      <div className="collapse-content">{children}</div>
    </div>
  )
}

// Avatar Component
export interface AvatarProps {
  src?: string
  alt?: string
  size?: string
  online?: boolean
  offline?: boolean
  placeholder?: boolean
  className?: string
  children?: React.ReactNode
}

export const Avatar: React.FC<AvatarProps> = ({
  src,
  alt,
  size = 'w-24',
  online,
  offline,
  placeholder,
  className,
  children
}) => {
  return (
    <div className={cn('avatar', online && 'avatar-online', offline && 'avatar-offline', placeholder && 'avatar-placeholder', className)}>
      <div className={cn(size, 'rounded-full')}>
        {src ? <img src={src} alt={alt} /> : children}
      </div>
    </div>
  )
}

// Avatar Group Component
export interface AvatarGroupProps {
  children: React.ReactNode
  className?: string
}

export const AvatarGroup: React.FC<AvatarGroupProps> = ({ children, className }) => {
  return <div className={cn('avatar-group -space-x-6', className)}>{children}</div>
}

// Badge Component
export interface BadgeProps {
  children: React.ReactNode
  variant?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error'
  styleVariant?: 'outline' | 'dash' | 'soft' | 'ghost'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant,
  styleVariant,
  size,
  className
}) => {
  return (
    <span
      className={cn(
        'badge',
        variant && `badge-${variant}`,
        styleVariant && `badge-${styleVariant}`,
        size && `badge-${size}`,
        className
      )}
    >
      {children}
    </span>
  )
}

// Card Component
export interface CardProps {
  children: React.ReactNode
  title?: string
  image?: string
  imageAlt?: string
  actions?: React.ReactNode
  side?: boolean
  imageFull?: boolean
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  styleVariant?: 'border' | 'dash'
  className?: string
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  image,
  imageAlt,
  actions,
  side,
  imageFull,
  size,
  styleVariant,
  className
}) => {
  return (
    <div
      className={cn(
        'card',
        side && 'card-side',
        imageFull && 'image-full',
        size && `card-${size}`,
        styleVariant && `card-${styleVariant}`,
        'bg-base-100 shadow-xl',
        className
      )}
    >
      {image && (
        <figure>
          <img src={image} alt={imageAlt} />
        </figure>
      )}
      <div className="card-body">
        {title && <h2 className="card-title">{title}</h2>}
        {children}
        {actions && <div className="card-actions justify-end">{actions}</div>}
      </div>
    </div>
  )
}

// Chat Component
export interface ChatProps {
  children: React.ReactNode
  placement: 'start' | 'end'
  image?: string
  header?: string
  footer?: string
  bubbleColor?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error'
  className?: string
}

export const Chat: React.FC<ChatProps> = ({
  children,
  placement,
  image,
  header,
  footer,
  bubbleColor,
  className
}) => {
  return (
    <div className={cn('chat', `chat-${placement}`, className)}>
      {image && (
        <div className="chat-image avatar">
          <div className="w-10 rounded-full">
            <img alt="Avatar" src={image} />
          </div>
        </div>
      )}
      {header && <div className="chat-header">{header}</div>}
      <div className={cn('chat-bubble', bubbleColor && `chat-bubble-${bubbleColor}`)}>{children}</div>
      {footer && <div className="chat-footer opacity-50">{footer}</div>}
    </div>
  )
}

// Countdown Component
export interface CountdownProps {
  value: number
  className?: string
}

export const Countdown: React.FC<CountdownProps> = ({ value, className }) => {
  return (
    <span className={cn('countdown', className)}>
      <span style={{ '--value': value } as React.CSSProperties}>{value}</span>
    </span>
  )
}

// Diff Component
export interface DiffProps {
  item1: React.ReactNode
  item2: React.ReactNode
  aspectRatio?: string
  className?: string
}

export const Diff: React.FC<DiffProps> = ({ item1, item2, aspectRatio, className }) => {
  return (
    <figure className={cn('diff', aspectRatio, className)}>
      <div className="diff-item-1">{item1}</div>
      <div className="diff-item-2">{item2}</div>
      <div className="diff-resizer"></div>
    </figure>
  )
}

// Kbd Component
export interface KbdProps {
  children: React.ReactNode
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export const Kbd: React.FC<KbdProps> = ({ children, size, className }) => {
  return <kbd className={cn('kbd', size && `kbd-${size}`, className)}>{children}</kbd>
}

// Stat Component
export interface StatProps {
  title?: string
  value: string | number
  desc?: string
  figure?: React.ReactNode
  actions?: React.ReactNode
  className?: string
}

export const Stat: React.FC<StatProps> = ({ title, value, desc, figure, actions, className }) => {
  return (
    <div className={cn('stat', className)}>
      {figure && <div className="stat-figure">{figure}</div>}
      {title && <div className="stat-title">{title}</div>}
      <div className="stat-value">{value}</div>
      {desc && <div className="stat-desc">{desc}</div>}
      {actions && <div className="stat-actions">{actions}</div>}
    </div>
  )
}

// Stats Container Component
export interface StatsProps {
  children: React.ReactNode
  direction?: 'horizontal' | 'vertical'
  className?: string
}

export const Stats: React.FC<StatsProps> = ({ children, direction, className }) => {
  return (
    <div className={cn('stats', direction && `stats-${direction}`, 'shadow', className)}>
      {children}
    </div>
  )
}

// Table Component
export interface TableProps {
  children: React.ReactNode
  zebra?: boolean
  pinRows?: boolean
  pinCols?: boolean
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export const Table: React.FC<TableProps> = ({
  children,
  zebra,
  pinRows,
  pinCols,
  size,
  className
}) => {
  return (
    <div className="overflow-x-auto">
      <table
        className={cn(
          'table',
          zebra && 'table-zebra',
          pinRows && 'table-pin-rows',
          pinCols && 'table-pin-cols',
          size && `table-${size}`,
          className
        )}
      >
        {children}
      </table>
    </div>
  )
}

// Timeline Component
export interface TimelineItemProps {
  start?: React.ReactNode
  middle?: React.ReactNode
  end?: React.ReactNode
  className?: string
}

export const TimelineItem: React.FC<TimelineItemProps> = ({ start, middle, end, className }) => {
  return (
    <li className={className}>
      {start && <div className="timeline-start">{start}</div>}
      {middle && <div className="timeline-middle">{middle}</div>}
      {end && <div className="timeline-end">{end}</div>}
    </li>
  )
}

export interface TimelineProps {
  children: React.ReactNode
  direction?: 'vertical' | 'horizontal'
  snapIcon?: boolean
  compact?: boolean
  className?: string
}

export const Timeline: React.FC<TimelineProps> = ({
  children,
  direction,
  snapIcon,
  compact,
  className
}) => {
  return (
    <ul
      className={cn(
        'timeline',
        direction && `timeline-${direction}`,
        snapIcon && 'timeline-snap-icon',
        compact && 'timeline-compact',
        className
      )}
    >
      {children}
    </ul>
  )
}
