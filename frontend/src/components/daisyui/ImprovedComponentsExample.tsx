import React, { useState } from 'react'
import { Loading, Tooltip, Button, Alert } from './index'

/**
 * Example showing the improved components in action
 */
export const ImprovedComponentsExample: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)

  const handleSubmit = async () => {
    setLoading(true)
    setShowSuccess(false)
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    setLoading(false)
    setShowSuccess(true)
    
    // Hide success after 3 seconds
    setTimeout(() => setShowSuccess(false), 3000)
  }

  return (
    <div className="min-h-screen bg-base-200 p-8">
      <div className="max-w-2xl mx-auto space-y-8">
        <h1 className="text-3xl font-bold text-center">
          Improved DaisyUI Components
        </h1>
        
        {showSuccess && (
          <Alert variant="success">
            <span>✅ Action completed successfully!</span>
          </Alert>
        )}
        
        <div className="bg-base-100 p-6 rounded-box space-y-6">
          <h2 className="text-xl font-semibold">Enhanced Loading & Tooltips</h2>
          
          <div className="space-y-4">
            <div className="flex flex-wrap gap-4">
              <Tooltip tip="This will trigger a loading state">
                <Button 
                  variant="primary" 
                  onClick={handleSubmit}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loading variant="spinner" size="sm" className="mr-2" />
                      Processing...
                    </>
                  ) : (
                    'Submit Form'
                  )}
                </Button>
              </Tooltip>
              
              <Tooltip tip="Refresh the page data" position="bottom">
                <Button variant="secondary">
                  🔄 Refresh
                </Button>
              </Tooltip>
              
              <Tooltip tip="This action cannot be undone" color="error" position="left">
                <Button variant="error">
                  🗑️ Delete
                </Button>
              </Tooltip>
            </div>
            
            {loading && (
              <div className="text-center p-4">
                <Loading variant="dots" size="lg" />
                <p className="mt-2 text-sm opacity-70">
                  Please wait while we process your request...
                </p>
              </div>
            )}
          </div>
        </div>
        
        <div className="bg-base-100 p-6 rounded-box space-y-4">
          <h2 className="text-xl font-semibold">All Loading Variants</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <Loading variant="spinner" size="md" />
              <p className="text-xs mt-2">Spinner</p>
            </div>
            <div>
              <Loading variant="dots" size="md" />
              <p className="text-xs mt-2">Dots</p>
            </div>
            <div>
              <Loading variant="ring" size="md" />
              <p className="text-xs mt-2">Ring</p>
            </div>
            <div>
              <Loading variant="ball" size="md" />
              <p className="text-xs mt-2">Ball</p>
            </div>
            <div>
              <Loading variant="bars" size="md" />
              <p className="text-xs mt-2">Bars</p>
            </div>
            <div>
              <Loading variant="infinity" size="md" />
              <p className="text-xs mt-2">Infinity</p>
            </div>
          </div>
        </div>
        
        <div className="bg-base-100 p-6 rounded-box">
          <h2 className="text-xl font-semibold mb-4">Ready to Use!</h2>
          <p className="text-base-content/70">
            🎉 All 61 DaisyUI components are now implemented and ready to use in your React application.
            The components include full TypeScript support, all variants, and follow DaisyUI 5 specifications.
          </p>
        </div>
      </div>
    </div>
  )
}
