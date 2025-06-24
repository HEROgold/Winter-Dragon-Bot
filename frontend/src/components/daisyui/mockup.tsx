import React from 'react'
import { cn } from '../../lib/utils'

// Mockup Browser Component
export interface MockupBrowserProps {
  children: React.ReactNode
  url?: string
  className?: string
}

export const MockupBrowser: React.FC<MockupBrowserProps> = ({ children, url, className }) => {
  return (
    <div className={cn('mockup-browser bg-base-300 border', className)}>
      <div className="mockup-browser-toolbar">
        <div className="input">{url || 'https://daisyui.com'}</div>
      </div>
      <div className="bg-base-200 flex justify-center px-4 py-16">
        {children}
      </div>
    </div>
  )
}

// Mockup Code Component
export interface MockupCodeProps {
  children: React.ReactNode
  className?: string
}

export const MockupCode: React.FC<MockupCodeProps> = ({ children, className }) => {
  return (
    <div className={cn('mockup-code', className)}>
      {children}
    </div>
  )
}

// Mockup Code Line Component
export interface MockupCodeLineProps {
  children: React.ReactNode
  prefix?: string
  className?: string
}

export const MockupCodeLine: React.FC<MockupCodeLineProps> = ({ children, prefix, className }) => {
  return (
    <pre data-prefix={prefix} className={className}>
      <code>{children}</code>
    </pre>
  )
}

// Mockup Phone Component
export interface MockupPhoneProps {
  children: React.ReactNode
  className?: string
}

export const MockupPhone: React.FC<MockupPhoneProps> = ({ children, className }) => {
  return (
    <div className={cn('mockup-phone', className)}>
      <div className="camera"></div>
      <div className="display">
        <div className="artboard artboard-demo phone-1">
          {children}
        </div>
      </div>
    </div>
  )
}

// Mockup Window Component
export interface MockupWindowProps {
  children: React.ReactNode
  className?: string
}

export const MockupWindow: React.FC<MockupWindowProps> = ({ children, className }) => {
  return (
    <div className={cn('mockup-window bg-base-300 border', className)}>
      <div className="bg-base-200 flex justify-center px-4 py-16">
        {children}
      </div>
    </div>
  )
}
