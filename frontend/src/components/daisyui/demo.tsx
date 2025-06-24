import React, { useState } from 'react'
import { Button, Card, Input, Alert } from './index'

/**
 * Simple demo component showing DaisyUI components in action
 */
export const DaisyUIDemo: React.FC = () => {
  const [name, setName] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = () => {
    if (name.trim()) {
      setSubmitted(true)
      setTimeout(() => setSubmitted(false), 3000)
    }
  }

  return (
    <div className="min-h-screen bg-base-200 p-8">
      <div className="max-w-md mx-auto space-y-6">
        <h1 className="text-3xl font-bold text-center">DaisyUI Demo</h1>
        
        {submitted && (
          <Alert variant="success">
            <span>Hello {name}! Welcome to DaisyUI components!</span>
          </Alert>
        )}
        
        <Card title="Welcome Form" className="bg-base-100">
          <div className="space-y-4">
            <Input
              placeholder="Enter your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              color="primary"
            />
            
            <Button
              variant="primary"
              modifier="block"
              onClick={handleSubmit}
              disabled={!name.trim()}
            >
              Submit
            </Button>
          </div>
        </Card>
        
        <Card title="Component Features" className="bg-base-100">
          <ul className="list-disc list-inside space-y-2">
            <li>✅ Full TypeScript support</li>
            <li>✅ All DaisyUI 5 components</li>
            <li>✅ Flexible and reusable</li>
            <li>✅ Tailwind CSS integration</li>
            <li>✅ Accessibility built-in</li>
          </ul>
        </Card>
      </div>
    </div>
  )
}
