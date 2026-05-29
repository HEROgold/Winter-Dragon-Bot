# Frontend Guide

## Overview

The Winter Dragon frontend is a **React + Bun** application built with **TSRX**, providing an authenticated user dashboard with Discord OAuth integration.

## Features

### Home Page

- **Counter Demo**: Interactive counter showcasing local state management
- **Navigation**: Links to user dashboard and authentication

### User Dashboard

- **Authentication Required**: Protected route using Discord OAuth tokens
- **Profile Display**: Shows authenticated user's Discord profile information
- **Data Management**: View and manage Discord-related data
- **GDPR Compliance**: Request data deletion with audit trail

## Architecture

```
Frontend (React + Bun + TSRX)
├── Pages
│   ├── Home
│   ├── Dashboard (OAuth-protected)
│   └── Callback (OAuth handler)
├── Components
│   ├── Navigation
│   ├── Profile
│   └── DataManager
└── Services
    └── API Client
```

## Running Locally

### Prerequisites

- Node.js 20+ or Bun installed
- Backend API running at `http://localhost:8001`

### Development Mode

```bash
cd frontend
bun install
bun run serve
```

The app will reload automatically on file changes at http://localhost:3000.

### Build for Production

```bash
bun run build
```

## API Integration

### Authentication Flow

1. User clicks "Sign in with Discord"
2. Frontend redirects to `/api/auth/discord/login`
3. Discord OAuth redirects back to callback handler
4. Backend exchanges code for token
5. Frontend stores token and redirects to dashboard

### API Endpoints

See [API Usage](api-usage.md) for detailed endpoint documentation.

## Environment Configuration

Configure via environment variables:

```env
VITE_API_URL=http://localhost:8001
VITE_DISCORD_CLIENT_ID=your-client-id
```

## Troubleshooting

### CORS Errors

Ensure backend is running and CORS is configured:
```bash
docker compose logs api
```

### OAuth Callback Fails

1. Verify `DISCORD_CLIENT_ID` matches your application
2. Check Discord OAuth redirect URL is `http://localhost:3000/callback`
3. Ensure frontend is accessible at configured URL
