import React, { useState } from 'react'
import {
  // Actions
  Button, Dropdown, Swap, ThemeController,
  
  // Data Display
  Accordion, Avatar, AvatarGroup, Badge, Card, Chat, Countdown,
  Diff, Kbd, Stat, Stats, Table, Timeline, TimelineItem,
  
  // Data Input
  Checkbox, FileInput, Input, Label, FloatingLabel, Radio, Range,
  Rating, Select, Textarea, Toggle, Fieldset, Validator,
  
  // Feedback
  Alert, Loading, Progress, RadialProgress, Skeleton, Toast,
  Modal, ModalAction, Status,
  
  // Layout
  Divider, Drawer, DrawerToggle, Footer, FooterTitle, Hero,
  Indicator, IndicatorItem, Join, JoinItem, Mask, Stack,
  Carousel, CarouselItem,
  
  // Mockup
  MockupBrowser, MockupCode, MockupCodeLine, MockupPhone, MockupWindow,
  
  // Navigation
  Breadcrumbs, BreadcrumbItem, Link, Menu, MenuItem, MenuTitle,
  Navbar, NavbarStart, NavbarCenter, NavbarEnd, Pagination, PaginationItem,
  Steps, Step, Tabs, TabItem, Dock, DockItem, Filter, FilterItem,
  
  // Utility
  Calendar, List, ListRow, Collapse
} from '../daisyui'

export const DaisyUIShowcase: React.FC = () => {
  const [modalOpen, setModalOpen] = useState(false)
  const [rating, setRating] = useState(3)
  const [theme, setTheme] = useState('light')

  return (
    <div className="p-8 space-y-12">
      <h1 className="text-4xl font-bold text-center">DaisyUI Components Showcase</h1>
      
      {/* Actions Section */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Actions</h2>
        <div className="flex gap-4 flex-wrap">
          <Button variant="primary">Primary Button</Button>
          <Button variant="secondary" styleVariant="outline">Outline Secondary</Button>
          <Button variant="accent" size="lg" loading>Loading Button</Button>
          <Button variant="error" modifier="circle">×</Button>
        </div>
        
        <Dropdown
          content={
            <>
              <li><a>Item 1</a></li>
              <li><a>Item 2</a></li>
            </>
          }
        >
          <Button>Dropdown</Button>
        </Dropdown>
        
        <Swap>
          {[<span>😊</span>, <span>😢</span>]}
        </Swap>
        
        <ThemeController 
          theme={theme} 
          onChange={(checked) => setTheme(checked ? 'dark' : 'light')}
        />
      </section>

      {/* Data Display Section */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Data Display</h2>
        
        <div className="flex gap-4 items-center">
          <AvatarGroup>
            <Avatar src="https://picsum.photos/100/100?random=1" />
            <Avatar src="https://picsum.photos/100/100?random=2" />
            <Avatar placeholder>+99</Avatar>
          </AvatarGroup>
        </div>
        
        <div className="flex gap-2 flex-wrap">
          <Badge variant="primary">Primary</Badge>
          <Badge variant="secondary" styleVariant="outline">Outline</Badge>
          <Badge variant="accent" size="lg">Large Badge</Badge>
        </div>
        
        <Card
          title="Card Title"
          image="https://picsum.photos/400/200"
          actions={<Button variant="primary">Action</Button>}
        >
          <p>This is a sample card with some content.</p>
        </Card>
        
        <div className="space-y-2">
          <Chat placement="start" image="https://picsum.photos/40/40?random=3">
            Hello! How are you?
          </Chat>
          <Chat placement="end" bubbleColor="primary">
            I'm doing great, thanks!
          </Chat>
        </div>
        
        <Stats>
          <Stat title="Total Users" value="25.6K" desc="21% more than last month" />
          <Stat title="Page Views" value="2.6M" desc="↗︎ 400 (22%)" />
        </Stats>
        
        <Timeline>
          <TimelineItem
            start="1984"
            middle="🎯"
            end="First Macintosh computer"
          />
          <TimelineItem
            start="1998"
            middle="💻"
            end="iMac"
          />
        </Timeline>
      </section>

      {/* Data Input Section */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Data Input</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input placeholder="Enter text" color="primary" />
          <Select color="secondary">
            <option>Option 1</option>
            <option>Option 2</option>
          </Select>
          
          <Textarea placeholder="Enter message" rows={3} />
          <FileInput color="accent" />
        </div>
        
        <div className="flex gap-4 items-center">
          <Checkbox color="primary" />
          <Radio name="radio-group" color="secondary" />
          <Toggle color="accent" />
        </div>
        
        <Rating
          name="rating-example"
          value={rating}
          onChange={setRating}
          max={5}
        />
        
        <Range min={0} max={100} defaultValue={50} color="primary" />
      </section>

      {/* Feedback Section */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Feedback</h2>
        
        <Alert variant="info">
          <span>New software update available.</span>
        </Alert>
        
        <Alert variant="success">
          <span>Your purchase has been confirmed!</span>
        </Alert>
        
        <div className="flex gap-4 items-center">
          <Loading variant="spinner" size="lg" />
          <Loading variant="dots" />
          <Loading variant="ring" />
        </div>
        
        <Progress value={70} max={100} color="primary" />
        
        <RadialProgress value={75}>75%</RadialProgress>
        
        <div className="space-y-2">
          <Skeleton width="w-full" height="h-4" />
          <Skeleton width="w-3/4" height="h-4" />
          <Skeleton width="w-1/2" height="h-4" />
        </div>
      </section>

      {/* Layout Section */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Layout</h2>
        
        <Divider>Section Divider</Divider>
        
        <Join>
          <JoinItem>
            <Button>Button 1</Button>
          </JoinItem>
          <JoinItem>
            <Button>Button 2</Button>
          </JoinItem>
          <JoinItem>
            <Button>Button 3</Button>
          </JoinItem>
        </Join>
        
        <Indicator>
          <IndicatorItem>
            <Badge variant="secondary">new</Badge>
          </IndicatorItem>
          <Button>Inbox</Button>
        </Indicator>
        
        <Stack>
          <div className="bg-primary text-primary-content w-20 h-20 rounded">1</div>
          <div className="bg-accent text-accent-content w-20 h-20 rounded">2</div>
          <div className="bg-secondary text-secondary-content w-20 h-20 rounded">3</div>
        </Stack>
      </section>

      {/* Navigation Section */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Navigation</h2>
        
        <Breadcrumbs>
          <BreadcrumbItem href="/">Home</BreadcrumbItem>
          <BreadcrumbItem href="/documents">Documents</BreadcrumbItem>
          <BreadcrumbItem>Current Page</BreadcrumbItem>
        </Breadcrumbs>
        
        <Navbar>
          <NavbarStart>
            <Link className="btn btn-ghost normal-case text-xl">daisyUI</Link>
          </NavbarStart>
          <NavbarCenter>
            <Menu direction="horizontal">
              <MenuItem><Link href="#home">Home</Link></MenuItem>
              <MenuItem><Link href="#about">About</Link></MenuItem>
              <MenuItem><Link href="#contact">Contact</Link></MenuItem>
            </Menu>
          </NavbarCenter>
          <NavbarEnd>
            <Button variant="primary">Get Started</Button>
          </NavbarEnd>
        </Navbar>
        
        <Steps>
          <Step color="primary">Register</Step>
          <Step color="primary">Choose plan</Step>
          <Step>Purchase</Step>
          <Step>Receive Product</Step>
        </Steps>
        
        <Pagination>
          <PaginationItem>«</PaginationItem>
          <PaginationItem>1</PaginationItem>
          <PaginationItem active>2</PaginationItem>
          <PaginationItem>3</PaginationItem>
          <PaginationItem>»</PaginationItem>
        </Pagination>
      </section>

      {/* Mockup Section */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Mockups</h2>
        
        <MockupBrowser url="https://daisyui.com">
          <div className="flex justify-center items-center h-32">
            Hello world!
          </div>
        </MockupBrowser>
        
        <MockupCode>
          <MockupCodeLine prefix="$">npm i daisyui</MockupCodeLine>
          <MockupCodeLine prefix=">">installing...</MockupCodeLine>
          <MockupCodeLine prefix=">">Done!</MockupCodeLine>
        </MockupCode>
        
        <MockupWindow>
          <div className="flex justify-center items-center h-32">
            App Window Content
          </div>
        </MockupWindow>
      </section>

      {/* Modal Example */}
      <Button onClick={() => setModalOpen(true)}>Open Modal</Button>
      
      {modalOpen && (
        <Modal id="example-modal" open={modalOpen}>
          <h3 className="font-bold text-lg">Hello!</h3>
          <p className="py-4">This modal works with component state!</p>
          <ModalAction>
            <Button onClick={() => setModalOpen(false)}>Close</Button>
          </ModalAction>
        </Modal>
      )}
    </div>
  )
}
