# Winter Dragon Bot - Frontend Hub Plan

## Project Overview

The Winter Dragon Bot Frontend Hub will be a React-based web application that serves as a central interface for users to interact with and configure the Winter Dragon Discord bot. Similar to interfaces for bots like MEE6 and Carl Bot, this hub will allow users to manage the bot's features, view statistics, and customize settings for their Discord servers.

## Technology Stack

- **Frontend Framework**: React with TypeScript
- **Routing**: React Router v6
- **Styling**: CSS Modules or styled-components
- **Authentication**: Discord OAuth2 (integrating with our FastAPI backend)
- **State Management**: React Context API and/or Redux Toolkit
- **API Communication**: Axios for REST API integration
- **Build Tool**: Already using Bun (as seen in the workspace structure)
- **API Integration**: Consuming the Winter Dragon Bot FastAPI service

## Data Types

The frontend will use TypeScript interfaces that mirror the backend data models. These types will ensure type safety when working with API data:

```typescript
// Core Types
interface User {
  id: string;
  username: string;
  discriminator: string;
  avatar?: string;
  email?: string;
  isAdmin: boolean;
  preferences: Record<string, any>;
  createdAt: string;
  updatedAt: string;
  lastLoginAt?: string;
}

interface Server {
  id: string;
  name: string;
  icon?: string;
  ownerId: string;
  permissions: number;
  premiumTier: number;
  memberCount: number;
  botJoinedAt: string;
  settings: Record<string, any>;
  prefix: string;
  createdAt: string;
  updatedAt: string;
  enabledFeatures: string[];
}

interface Feature {
  id: string;
  name: string;
  description: string;
  category: string;
  defaultEnabled: boolean;
  premiumOnly: boolean;
  configurableOptions: Array<Record<string, any>>;
  createdAt: string;
  updatedAt: string;
}

interface FeatureConfig {
  id: string;
  serverId: string;
  featureId: string;
  feature: Feature;
  enabled: boolean;
  settings: Record<string, any>;
  permissions: Record<string, string[]>;
  createdAt: string;
  updatedAt: string;
}

// Discord Entity Types
interface ServerChannel {
  id: string;
  serverId: string;
  name: string;
  type: string;
  position: number;
  parentId?: string;
  isNsfw: boolean;
}

interface ServerRole {
  id: string;
  serverId: string;
  name: string;
  color: number;
  position: number;
  permissions: number;
  isMentionable: boolean;
}

// Feature-specific Types
interface WelcomeConfig {
  id: string;
  serverId: string;
  channelId?: string;
  enabled: boolean;
  message?: string;
  embedConfig?: Record<string, any>;
  dmEnabled: boolean;
  dmMessage?: string;
}

interface AutoModRule {
  id: string;
  serverId: string;
  type: string;
  enabled: boolean;
  action: string;
  channelId?: string;
  threshold?: number;
  duration?: number;
  contentFilter?: Record<string, any>;
  whitelist: string[];
  exemptRoles: string[];
  exemptChannels: string[];
}

interface CustomCommand {
  id: string;
  serverId: string;
  name: string;
  response: string;
  description?: string;
  cooldown: number;
  aliases: string[];
  enabled: boolean;
  restrictedChannels: string[];
  restrictedRoles: string[];
  createdAt: string;
  createdBy?: string;
  updatedAt: string;
  updatedBy?: string;
}

// Statistics Types
interface CommandUsage {
  id: string;
  serverId: string;
  userId: string;
  command: string;
  success: boolean;
  errorMessage?: string;
  timestamp: string;
  executionTime?: number;
}

interface FeatureStatistic {
  id: string;
  serverId: string;
  featureId: string;
  date: string;
  usageCount: number;
  uniqueUsers: number;
  details?: Record<string, any>;
}

// Response Types
interface ApiResponse<T> {
  data: T;
  success: boolean;
  error?: string;
  message?: string;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}
```

## Application Structure

```dir
src/
├── assets/            # Static assets like images, icons
├── components/        # Reusable UI components
│   ├── common/        # Shared components (buttons, cards, modals)
│   ├── layout/        # Layout components (header, footer, sidebar)
│   └── features/      # Feature-specific components
├── contexts/          # React context providers
├── hooks/             # Custom React hooks
├── pages/             # Page components for each route
├── routes/            # Routing configuration
├── services/          # API and external service integrations
│   ├── api/           # API client and endpoints
│   │   ├── auth.ts    # Authentication API endpoints
│   │   ├── servers.ts # Server management endpoints
│   │   ├── features.ts # Feature configuration endpoints
│   │   ├── users.ts   # User management endpoints
│   │   └── statistics.ts # Statistics data endpoints
│   ├── auth/          # Authentication service (Discord OAuth)
│   └── bot/           # Bot-specific services
├── styles/            # Global styles and theme
├── types/             # TypeScript type definitions
└── utils/             # Utility functions
```

## Pages & Routes

1. **Landing Page** (`/`)
   - Introduction to Winter Dragon Bot
   - Features overview
   - Call-to-action for adding the bot to servers

2. **Dashboard** (`/dashboard`)
   - Overview of user's servers with the bot
   - Summary statistics
   - Quick access to common settings

3. **Server Management** (`/servers/:serverId`)
   - Specific server configuration
   - Bot status in the server
   - Server-specific statistics

4. **Feature Configuration** (`/servers/:serverId/features/:featureId`)
   - Detailed configuration for specific bot features
   - Enable/disable features
   - Customize feature behavior

5. **User Settings** (`/settings`)
   - User preference settings
   - Notification settings
   - Account linking options

6. **Documentation** (`/docs`)
   - Bot commands documentation
   - Feature explanations
   - Tutorials and guides

7. **Support** (`/support`)
   - FAQ section
   - Contact form
   - Community links

## Components Structure

### Layout Components

1. **MainLayout**
   - Wrapper for all authenticated pages
   - Includes Header, Sidebar, and Footer

2. **Header**
   - Logo
   - Navigation links
   - User profile dropdown

3. **Sidebar**
   - Server selection
   - Feature navigation
   - Collapsible categories

4. **Footer**
   - Copyright information
   - Social media links
   - Legal links

### Common Components

1. **Button** - Various button styles (primary, secondary, danger)
2. **Card** - Container for content blocks
3. **Modal** - Popup dialogs for confirmations and forms
4. **Dropdown** - Selection menus
5. **Toggle** - On/off switches for features
6. **Tooltip** - Contextual help information
7. **Alert** - Success/error/warning messages
8. **Loader** - Loading indicators

### Feature-specific Components

1. **ServerCard** - Display server information
2. **FeatureToggle** - Enable/disable bot features
3. **CommandList** - Display available commands
4. **PermissionSelector** - Configure role-based permissions
5. **StatisticsChart** - Visualize data and metrics
6. **WelcomeMessageEditor** - Configure server welcome messages
7. **AutoModSettings** - Configure moderation rules

## Authentication Flow

1. User clicks "Login with Discord" on the frontend
2. Frontend calls the `/auth/discord` endpoint from our API
3. API returns Discord authorization URL
4. Frontend redirects user to Discord OAuth authorization page
5. User authorizes the application on Discord
6. Discord redirects back to our application's callback URL with an authorization code
7. Frontend passes the code to the backend's `/auth/discord/callback` endpoint
8. Backend exchanges the code for an access token with Discord API
9. Backend creates or updates user record with Discord information
10. Backend generates JWT token and returns it with user information
11. Frontend stores the token securely (managed by backend in HTTP-only cookies)
12. User is now authenticated and can access protected routes

## Security Considerations

### Authentication & Authorization

1. **Token Security**
   - Store authentication tokens in HTTP-only cookies
   - Implement token refresh mechanism
   - Set proper expiration times

2. **Cross-Site Request Forgery (CSRF) Protection**
   - Implement CSRF tokens for state verification during OAuth flow
   - Validate origin of requests

3. **Rate Limiting**
   - Implement rate limiting on API endpoints
   - Prevent brute force attacks

### Data Protection

1. **API Security**
   - All API requests should use HTTPS
   - Validate all inputs on both client and server side
   - Implement proper error handling that doesn't expose sensitive details

2. **Server Permissions**
   - Only show servers where the user has appropriate permissions
   - Implement role-based access control for bot settings

3. **Bot Permissions**
   - Clearly communicate required bot permissions
   - Don't request unnecessary permissions

### Frontend Security

1. **Dependencies**
   - Regular audit of npm packages
   - Keep all dependencies updated

2. **Content Security Policy**
   - Implement CSP headers to prevent XSS attacks
   - Restrict loading of resources to trusted domains

3. **User Input**
   - Sanitize all user inputs
   - Validate inputs on both client and server side

## Domain & Hosting Considerations

### Domain Name Acquisition

1. **Options for domain registrars**:
   - Namecheap
   - Google Domains
   - GoDaddy
   - Cloudflare Registrar

2. **Domain name suggestions**:
   - winterdragonbot.com
   - winter-dragon.app
   - winterdragon.bot

### Hosting Options

1. **Frontend Hosting**:
   - Vercel
   - Netlify
   - GitHub Pages
   - AWS Amplify

2. **Backend Hosting**:
    - Self hosted server
    - Domain server

### DNS Configuration

1. **Record Types Needed**:
   - A Records (pointing to server IP)
   - CNAME Records (for subdomains)
   - MX Records (if email is required)
   - TXT Records (for domain verification)

2. **SSL/TLS Certificate**:
   - Let's Encrypt for free certificates
   - Managed certificates through hosting provider

### Deployment Pipeline

1. **CI/CD Options**:
   - GitHub Actions
   - GitLab CI
   - Jenkins
   - CircleCI

2. **Deployment Strategy**:
   - Blue/Green deployment
   - Canary releases for testing new features

## Implementation Plan & Milestones

### Phase 1: Project Setup and Core Structure

- Set up project with React, TypeScript, and build tools
- Configure routing with React Router
- Implement basic layout and styling
- Create API integration layer to communicate with backend
- Create authentication flow with Discord OAuth via the backend API

### Phase 2: Dashboard and Server Management

- Implement dashboard interface
- Integrate with server listing API endpoint (`/servers`)
- Create server listing and selection interface
- Build server management interface with API integration
- Add basic bot configuration options connected to the API endpoints

### Phase 3: Feature-specific Interfaces

- Implement interfaces for each bot feature
- Create configuration options for each feature integrated with API endpoints
- Implement feature toggle functionality using the API
- Build visualization components for statistics using data from statistics endpoints
- Add real-time or polling updates for dynamic content

### Phase 4: Documentation and Support

- Create documentation pages
- Implement support interface
- Add user guides and tutorials

### Phase 5: Testing, Optimization, and Launch

- Perform comprehensive testing
- Optimize performance
- Implement analytics
- Launch MVP version

## Future Enhancements

1. **Bot Marketplace**
   - Allow users to discover and add custom plugins

2. **Advanced Analytics**
   - Detailed usage statistics and insights

3. **Custom Dashboards**
   - Customizable dashboard layouts for users

4. **Internationalization**
   - Support for multiple languages

5. **Integration with Other Services**
   - Twitch, YouTube, Twitter integrations

## API Integration

This frontend will communicate with the Winter Dragon Bot API (as detailed in `/backend/api_plan.md`) through the following integration points:

### API Client Setup

1. **Base Client Configuration**
   - Create an Axios instance with base URL configuration
   - Configure request/response interceptors for:
     - Authentication token handling
     - Error processing
     - Loading state management

2. **API Service Modules**
   - Implement service modules that map to the API's endpoints:
     - `AuthService` - Handle authentication flows
     - `UserService` - User profile management
     - `ServerService` - Server listing and configuration
     - `FeatureService` - Feature management for servers
     - `StatisticsService` - Fetch and process statistics data

### Key API Endpoints Integration

1. **Authentication Endpoints**
   - `/auth/discord` - Initiate Discord login
   - `/auth/discord/callback` - Process Discord callback
   - `/auth/logout` - User logout
   - `/auth/me` - Get current user info

2. **User Management**
   - `/users/me` - Fetch and update user profile
   - Update user preferences

3. **Server Management**
   - `/servers` - List available servers
   - `/servers/{server_id}` - Get server details
   - Update server settings

4. **Feature Configuration**
   - `/servers/{server_id}/features` - List features
   - `/servers/{server_id}/features/{feature_id}` - Get/update feature settings

5. **Statistics Data**
   - `/servers/{server_id}/statistics` - Fetch server statistics
   - Feature-specific statistics

### Data Handling Patterns

1. **State Management**
   - Implement Redux slices or Context providers for each main data domain:
     - Authentication state
     - User data
     - Server list and details
     - Feature configurations
     - Statistics data

2. **Caching Strategy**
   - Implement client-side caching for:
     - Server configurations
     - Frequently accessed statistics
     - User preferences
   - Cache invalidation on relevant updates

3. **Error Handling**
   - Global error handler for API responses
   - Specific error handling for authentication issues
   - User-friendly error messages and recovery options

4. **Real-time Updates**
   - Polling mechanism for statistics updates
   - Future enhancement: WebSocket integration for real-time dashboard updates

### Security Integration

1. **Token Management**
   - Handle JWT token storage (via secure HTTP-only cookies)
   - Implement token refresh logic when tokens expire
   - Clear tokens on logout

2. **Protected Routes**
   - Implement route guards for authenticated-only content
   - Handle unauthorized redirects
   - Permission-based component rendering

3. **Request Security**
   - Add CSRF protection tokens to requests
   - Validate data before sending to API
   - Implement proper error handling

### Database Model Consumption

The frontend will consume the API endpoints that expose the data from the following database models as defined in the API plan:

1. **Core Models**:
   - `User` - For user profile and authentication information
   - `Server` - For Discord server management
   - `Feature` - For bot feature definitions
   - `FeatureConfig` - For server-specific feature settings

2. **Discord Entity Models**:
   - `ServerChannel` - For channel selection in configuration
   - `ServerRole` - For role-based permissions and settings

3. **Feature-specific Models**:
   - `WelcomeConfig` - For welcome message settings
   - `AutoModRule` - For moderation rule configuration
   - `CustomCommand` - For custom command management

4. **Tracking Models**:
   - `CommandUsage` - For command usage statistics
   - `FeatureStatistic` - For feature usage analytics

The frontend will maintain synchronized state with these database models through the API endpoints, ensuring that all user interactions properly persist to the backend database.
