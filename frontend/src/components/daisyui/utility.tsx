import React from 'react'
import { cn } from '../../lib/utils'

// Glass Component
export interface GlassProps {
  children: React.ReactNode
  className?: string
}

export const Glass: React.FC<GlassProps> = ({ children, className }) => {
  return (
    <div className={cn('glass', className)}>
      {children}
    </div>
  )
}

// Border Radius Utilities as Components
export interface BorderRadiusProps {
  children: React.ReactNode
  variant: 'box' | 'field' | 'selector'
  className?: string
}

export const BorderRadius: React.FC<BorderRadiusProps> = ({ children, variant, className }) => {
  return (
    <div className={cn(`rounded-${variant}`, className)}>
      {children}
    </div>
  )
}

// Calendar Component (Generic wrapper for calendar libraries)
export interface CalendarProps {
  children: React.ReactNode
  library?: 'cally' | 'pikaday' | 'react-day-picker'
  className?: string
}

export const Calendar: React.FC<CalendarProps> = ({ children, library, className }) => {
  const libraryClass = library === 'cally' ? 'cally' : 
                      library === 'pikaday' ? 'pika-single' :
                      library === 'react-day-picker' ? 'react-day-picker' : ''
  
  return (
    <div className={cn(libraryClass, className)}>
      {children}
    </div>
  )
}

// List Component
export interface ListProps {
  children: React.ReactNode
  className?: string
}

export const List: React.FC<ListProps> = ({ children, className }) => {
  return (
    <ul className={cn('list', className)}>
      {children}
    </ul>
  )
}

// List Row Component
export interface ListRowProps {
  children: React.ReactNode
  colWrap?: boolean
  colGrow?: boolean
  className?: string
}

export const ListRow: React.FC<ListRowProps> = ({ children, colWrap, colGrow, className }) => {
  return (
    <li
      className={cn(
        'list-row',
        colWrap && 'list-col-wrap',
        colGrow && 'list-col-grow',
        className
      )}
    >
      {children}
    </li>
  )
}

// Collapse Component (Alternative to Accordion)
export interface CollapseProps {
  children: React.ReactNode
  title: string
  modifier?: 'arrow' | 'plus'
  open?: boolean
  close?: boolean
  className?: string
}

export const Collapse: React.FC<CollapseProps> = ({
  children,
  title,
  modifier,
  open,
  close,
  className
}) => {
  return (
    <div
      className={cn(
        'collapse',
        modifier && `collapse-${modifier}`,
        open && 'collapse-open',
        close && 'collapse-close',
        className
      )}
      tabIndex={0}
    >
      <div className="collapse-title text-xl font-medium">{title}</div>
      <div className="collapse-content">{children}</div>
    </div>
  )
}
