# DaisyUI Components for React + TypeScript

This folder contains a complete implementation of all DaisyUI 5 components as reusable React components with TypeScript support. These components are built to be flexible, accessible, and follow DaisyUI's design principles.

## 📁 Component Organization

### `/actions.tsx`
Interactive components that trigger actions:
- **Button** - Customizable buttons with variants, sizes, and states
- **Dropdown** - Dropdown menus with positioning options
- **Swap** - Toggle between two states with animations
- **ThemeController** - Theme switching functionality

### `/data-display.tsx`
Components for displaying information:
- **Accordion** - Collapsible content sections
- **Avatar** & **AvatarGroup** - User profile images and groups
- **Badge** - Status indicators and labels
- **Card** - Content containers with optional images and actions
- **Chat** - Chat message bubbles
- **Countdown** - Animated countdown numbers
- **Diff** - Side-by-side comparison view
- **Kbd** - Keyboard shortcut display
- **Stat** & **Stats** - Statistical data display
- **Table** - Data tables with sorting and styling
- **Timeline** & **TimelineItem** - Chronological event display

### `/data-input.tsx`
Form components and input elements:
- **Checkbox** - Checkboxes with color variants
- **FileInput** - File upload inputs
- **Input** - Text inputs with validation states
- **Label** & **FloatingLabel** - Input labels
- **Radio** - Radio button groups
- **Range** - Slider controls
- **Rating** - Star rating components
- **Select** - Dropdown selects
- **Textarea** - Multi-line text inputs
- **Toggle** - Switch toggles
- **Fieldset** - Form field grouping
- **Validator** - Input validation display

### `/feedback.tsx`
User feedback and status components:
- **Alert** - Notification messages
- **Loading** - Loading spinners and indicators
- **Progress** - Progress bars
- **RadialProgress** - Circular progress indicators
- **Skeleton** - Loading state placeholders
- **Toast** - Toast notifications
- **Modal** & **ModalAction** - Modal dialogs
- **Status** - Status indicators

### `/layout.tsx`
Layout and structural components:
- **Divider** - Content separators
- **Drawer** & **DrawerToggle** - Side navigation drawers
- **Footer** & **FooterTitle** - Page footers
- **Hero** - Hero sections
- **Indicator** & **IndicatorItem** - Badge indicators
- **Join** & **JoinItem** - Grouped elements
- **Mask** - Shape masking for images
- **Stack** - Layered element positioning
- **Carousel** & **CarouselItem** - Image/content carousels

### `/mockup.tsx`
Device and interface mockups:
- **MockupBrowser** - Browser window mockups
- **MockupCode** & **MockupCodeLine** - Code block mockups
- **MockupPhone** - Phone device mockups
- **MockupWindow** - OS window mockups

### `/navigation.tsx`
Navigation and menu components:
- **Breadcrumbs** & **BreadcrumbItem** - Navigation breadcrumbs
- **Link** - Styled links
- **Menu**, **MenuItem**, **MenuTitle** - Navigation menus
- **Navbar**, **NavbarStart**, **NavbarCenter**, **NavbarEnd** - Navigation bars
- **Pagination** & **PaginationItem** - Page navigation
- **Steps** & **Step** - Step indicators
- **Tabs** & **TabItem** - Tab navigation
- **Dock** & **DockItem** - Bottom navigation dock
- **Filter** & **FilterItem** - Filter controls

### `/utility.tsx`
Utility and helper components:
- **Calendar** - Calendar component wrapper
- **List** & **ListRow** - List layouts
- **Collapse** - Alternative collapse component

## 🚀 Usage Examples

### Basic Button Usage
```tsx
import { Button } from '../components/daisyui'

// Simple button
<Button variant="primary">Click me</Button>

// Button with custom styling
<Button 
  variant="secondary" 
  styleVariant="outline" 
  size="lg"
  loading={isLoading}
>
  Submit
</Button>
```

### Card Component
```tsx
import { Card, Button } from '../components/daisyui'

<Card
  title="Product Card"
  image="https://picsum.photos/400/300"
  actions={<Button variant="primary">Buy Now</Button>}
>
  <p>Product description goes here...</p>
</Card>
```

### Form Components
```tsx
import { Input, Select, Checkbox, Button } from '../components/daisyui'

<form className="space-y-4">
  <Input 
    placeholder="Enter your email" 
    color="primary" 
    type="email"
  />
  
  <Select color="secondary">
    <option>Choose an option</option>
    <option>Option 1</option>
    <option>Option 2</option>
  </Select>
  
  <Checkbox color="accent" /> Accept terms
  
  <Button type="submit" variant="primary">
    Submit
  </Button>
</form>
```

### Navigation Example
```tsx
import { Navbar, NavbarStart, NavbarCenter, NavbarEnd, Menu, MenuItem } from '../components/daisyui'

<Navbar>
  <NavbarStart>
    <div className="btn btn-ghost normal-case text-xl">Brand</div>
  </NavbarStart>
  
  <NavbarCenter>
    <Menu direction="horizontal">
      <MenuItem><a href="/">Home</a></MenuItem>
      <MenuItem><a href="/about">About</a></MenuItem>
      <MenuItem><a href="/contact">Contact</a></MenuItem>
    </Menu>
  </NavbarCenter>
  
  <NavbarEnd>
    <Button variant="primary">Get Started</Button>
  </NavbarEnd>
</Navbar>
```

## 🎨 Theming

All components support DaisyUI's theming system. You can use any of the built-in themes or create custom themes:

```tsx
// Theme controller for switching themes
<ThemeController 
  theme="dark" 
  onChange={(checked) => setTheme(checked ? 'dark' : 'light')}
/>
```

## 🔧 Customization

### CSS Classes
All components accept a `className` prop for additional customization:

```tsx
<Button className="my-custom-class" variant="primary">
  Custom Button
</Button>
```

### Tailwind CSS Integration
Components are designed to work seamlessly with Tailwind CSS utilities:

```tsx
<Card className="max-w-md mx-auto shadow-2xl">
  Content
</Card>
```

## 📱 Responsive Design

Many components include responsive variants:

```tsx
// Responsive menu
<Menu className="menu-vertical lg:menu-horizontal">
  {/* Menu items */}
</Menu>

// Responsive card layout
<Card className="card-side sm:card-normal">
  {/* Card content */}
</Card>
```

## ♿ Accessibility

Components include proper ARIA attributes and semantic HTML:

- Form components have proper labeling
- Interactive elements have appropriate roles
- Focus management is handled correctly
- Screen reader support is built-in

## 🧪 Testing

Components are built with testing in mind:

```tsx
import { render, screen } from '@testing-library/react'
import { Button } from '../components/daisyui'

test('renders button with text', () => {
  render(<Button>Click me</Button>)
  expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
})
```

## 📦 Bundle Size

These components are tree-shakeable, so you only bundle what you use:

```tsx
// Only imports the Button component
import { Button } from '../components/daisyui'

// Import multiple components
import { Button, Card, Input } from '../components/daisyui'
```

## 🔄 State Management

Components support both controlled and uncontrolled patterns:

```tsx
// Controlled
const [checked, setChecked] = useState(false)
<Checkbox checked={checked} onChange={(e) => setChecked(e.target.checked)} />

// Uncontrolled
<Checkbox defaultChecked />
```

## 🐛 TypeScript Support

Full TypeScript support with proper type definitions:

```tsx
import type { ButtonProps } from '../components/daisyui'

const MyButton: React.FC<ButtonProps> = (props) => {
  return <Button {...props} />
}
```

## 📋 Complete Component List

This implementation includes **all** DaisyUI 5 components:

✅ **Actions**: Button, Dropdown, Modal, Swap, Theme Controller  
✅ **Data Display**: Accordion, Avatar, Badge, Card, Carousel, Chat, Collapse, Countdown, Diff, Kbd, Stat, Table, Timeline  
✅ **Data Input**: Checkbox, File Input, Input, Radio, Range, Rating, Select, Textarea, Toggle, Form Validation  
✅ **Feedback**: Alert, Loading, Progress, Radial Progress, Skeleton, Toast  
✅ **Layout**: Artboard, Divider, Drawer, Footer, Hero, Indicator, Join, Mask, Stack  
✅ **Mockup**: Browser, Code, Phone, Window  
✅ **Navigation**: Breadcrumbs, Bottom Navigation, Link, Menu, Navbar, Pagination, Steps, Tab  

## 🚀 Getting Started

1. Import the components you need:
```tsx
import { Button, Card, Input } from '../components/daisyui'
```

2. Use them in your JSX:
```tsx
function App() {
  return (
    <div>
      <Card title="Welcome">
        <Input placeholder="Enter your name" />
        <Button variant="primary">Submit</Button>
      </Card>
    </div>
  )
}
```

3. Customize with props and Tailwind classes as needed!

For more examples, check out `DaisyUIShowcase.tsx` which demonstrates all components in action.
