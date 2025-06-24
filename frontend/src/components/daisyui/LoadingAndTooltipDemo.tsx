import React from 'react'
import { Loading, Tooltip, Button } from './index'

/**
 * Comprehensive demo of Loading variants and Tooltip component
 */
export const LoadingAndTooltipDemo: React.FC = () => {
  return (
    <div className="min-h-screen bg-base-200 p-8">
      <div className="max-w-4xl mx-auto space-y-12">
        <h1 className="text-4xl font-bold text-center">Loading & Tooltip Components</h1>
        
        {/* Loading Variants */}
        <section className="space-y-6">
          <h2 className="text-2xl font-semibold">Loading Variants</h2>
          
          <div className="grid grid-cols-2 md:grid-cols-3 gap-8">
            <div className="text-center space-y-2">
              <Loading variant="spinner" size="lg" />
              <p className="text-sm">Spinner</p>
            </div>
            
            <div className="text-center space-y-2">
              <Loading variant="dots" size="lg" />
              <p className="text-sm">Dots</p>
            </div>
            
            <div className="text-center space-y-2">
              <Loading variant="ring" size="lg" />
              <p className="text-sm">Ring</p>
            </div>
            
            <div className="text-center space-y-2">
              <Loading variant="ball" size="lg" />
              <p className="text-sm">Ball</p>
            </div>
            
            <div className="text-center space-y-2">
              <Loading variant="bars" size="lg" />
              <p className="text-sm">Bars</p>
            </div>
            
            <div className="text-center space-y-2">
              <Loading variant="infinity" size="lg" />
              <p className="text-sm">Infinity</p>
            </div>
          </div>
          
          {/* Loading Sizes */}
          <div className="space-y-4">
            <h3 className="text-xl font-medium">Loading Sizes</h3>
            <div className="flex items-center gap-4">
              <Loading variant="spinner" size="xs" />
              <Loading variant="spinner" size="sm" />
              <Loading variant="spinner" size="md" />
              <Loading variant="spinner" size="lg" />
              <Loading variant="spinner" size="xl" />
            </div>
          </div>
        </section>

        {/* Tooltip Examples */}
        <section className="space-y-6">
          <h2 className="text-2xl font-semibold">Tooltip Examples</h2>
          
          <div className="grid grid-cols-2 gap-8">
            <div className="space-y-4">
              <h3 className="text-xl font-medium">Positions</h3>
              <div className="flex flex-wrap gap-4">
                <Tooltip tip="Top tooltip" position="top">
                  <Button variant="primary">Top</Button>
                </Tooltip>
                
                <Tooltip tip="Bottom tooltip" position="bottom">
                  <Button variant="secondary">Bottom</Button>
                </Tooltip>
                
                <Tooltip tip="Left tooltip" position="left">
                  <Button variant="accent">Left</Button>
                </Tooltip>
                
                <Tooltip tip="Right tooltip" position="right">
                  <Button variant="neutral">Right</Button>
                </Tooltip>
              </div>
            </div>
            
            <div className="space-y-4">
              <h3 className="text-xl font-medium">Colors</h3>
              <div className="flex flex-wrap gap-4">
                <Tooltip tip="Primary tooltip" color="primary">
                  <Button variant="primary">Primary</Button>
                </Tooltip>
                
                <Tooltip tip="Success tooltip" color="success">
                  <Button variant="success">Success</Button>
                </Tooltip>
                
                <Tooltip tip="Warning tooltip" color="warning">
                  <Button variant="warning">Warning</Button>
                </Tooltip>
                
                <Tooltip tip="Error tooltip" color="error">
                  <Button variant="error">Error</Button>
                </Tooltip>
              </div>
            </div>
          </div>
          
          {/* Always Open Tooltip */}
          <div className="space-y-4">
            <h3 className="text-xl font-medium">Always Open Tooltip</h3>
            <Tooltip tip="This tooltip is always visible" open>
              <Button variant="info">Always Open</Button>
            </Tooltip>
          </div>
        </section>

        {/* Real-world Usage Examples */}
        <section className="space-y-6">
          <h2 className="text-2xl font-semibold">Real-world Examples</h2>
          
          <div className="bg-base-100 p-6 rounded-box space-y-4">
            <h3 className="text-xl font-medium">Loading States in UI</h3>
            
            <div className="flex flex-wrap gap-4">
              <Button variant="primary" disabled>
                <Loading variant="spinner" size="sm" className="mr-2" />
                Saving...
              </Button>
              
              <Button variant="secondary" disabled>
                <Loading variant="dots" size="sm" className="mr-2" />
                Loading...
              </Button>
              
              <Tooltip tip="Click to refresh data">
                <Button variant="accent">
                  🔄 Refresh
                </Button>
              </Tooltip>
              
              <Tooltip tip="Delete this item permanently" color="error">
                <Button variant="error">
                  🗑️ Delete
                </Button>
              </Tooltip>
            </div>
          </div>
          
          <div className="bg-base-100 p-6 rounded-box">
            <h3 className="text-xl font-medium">Form with Loading & Tooltips</h3>
            <div className="space-y-4 mt-4">
              <div className="flex items-center gap-2">
                <input type="email" placeholder="Email" className="input input-bordered flex-1" />
                <Tooltip tip="We'll never share your email">
                  <span className="text-info cursor-help">ℹ️</span>
                </Tooltip>
              </div>
              
              <div className="flex items-center gap-2">
                <input type="password" placeholder="Password" className="input input-bordered flex-1" />
                <Tooltip tip="Password must be at least 8 characters">
                  <span className="text-info cursor-help">ℹ️</span>
                </Tooltip>
              </div>
              
              <Button variant="primary" className="w-full">
                Sign Up
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
