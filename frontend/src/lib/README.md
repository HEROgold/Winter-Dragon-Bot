# Custom Discord OAuth Library

This directory contains a custom Discord OAuth2 implementation that replaces the problematic `discord-oauth2` package that was causing "global is not defined" errors in browser environments.

## Files

- **`discord-oauth.ts`** - Main OAuth library with full Discord API support
- **`discord-oauth-secure.ts`** - Secure backend-proxy implementation (recommended for production)

## Why We Created This

The original `discord-oauth2` package had several issues:

1. **Node.js Dependencies**: Used Node.js core modules (`events`, `https`, `zlib`) that don't exist in browsers
2. **Global Object**: Required Node.js `global` object not available in browsers  
3. **Security Issues**: Encouraged client-side use of client secrets
4. **Browser Incompatibility**: Not designed for modern browser environments

## Features

### ✅ Browser-Native Implementation
- Uses `fetch` API instead of Node.js HTTP modules
- No Node.js dependencies - pure browser-compatible code
- Uses Web Crypto API for secure random generation

### ✅ TypeScript Support
- Full TypeScript interfaces for Discord API responses
- Type-safe OAuth configuration and responses
- Proper error handling with typed exceptions

### ✅ Security Best Practices
- Secure state parameter generation using Web Crypto API
- Warnings when client secrets are used in frontend code
- Built-in CSRF protection with state validation
- Support for backend-proxy implementation

### ✅ Complete Discord OAuth Flow
- Authorization URL generation with all Discord parameters
- Token exchange (with security warnings for frontend use)
- Token refresh functionality
- User data fetching
- Guild information retrieval
- Token revocation

### ✅ Utility Functions
- CDN URL generators for avatars and guild icons
- Discord snowflake ID validation
- Callback URL parsing
- All common Discord scopes as constants

## Usage

### Basic Usage (Development)

```typescript
import { DiscordOAuth, DiscordScopes, DiscordOAuthUtils } from '@/lib/discord-oauth';

const oauth = new DiscordOAuth({
  clientId: 'your-client-id',
  redirectUri: 'http://localhost:3000/callback',
  scopes: [DiscordScopes.IDENTIFY, DiscordScopes.GUILDS],
});

// Generate auth URL
const authUrl = oauth.generateAuthUrl({
  state: DiscordOAuthUtils.generateState(),
});

// Exchange code for token (DEVELOPMENT ONLY!)
const tokenData = await oauth.exchangeCode(code, clientSecret);

// Get user data
const user = await oauth.getUser(tokenData.access_token);
```

### Secure Production Usage

```typescript
import { SecureDiscordOAuth } from '@/lib/discord-oauth-secure';

const oauth = new SecureDiscordOAuth({
  clientId: 'your-client-id',
  redirectUri: 'https://yourdomain.com/callback',
  scopes: [DiscordScopes.IDENTIFY, DiscordScopes.GUILDS],
  backendBaseUrl: 'https://api.yourdomain.com',
});

// Frontend generates auth URL (safe)
const authUrl = oauth.generateAuthUrl();

// Backend handles token exchange (secure)
const tokenData = await oauth.exchangeCode(code);
```

## Available Scopes

The library includes constants for all Discord OAuth scopes:

```typescript
import { DiscordScopes } from '@/lib/discord-oauth';

// Basic user info
DiscordScopes.IDENTIFY
DiscordScopes.EMAIL

// Guild access
DiscordScopes.GUILDS
DiscordScopes.GUILDS_JOIN
DiscordScopes.GUILDS_MEMBERS_READ

// And many more...
```

## Security Considerations

### 🚨 Development vs Production

- **Development**: You can use client secrets in frontend for testing (with warnings)
- **Production**: NEVER expose client secrets - use backend proxy endpoints

### 🔒 Backend Implementation Required

For production, implement these backend endpoints:

```
POST /auth/discord/token
POST /auth/discord/refresh  
POST /auth/discord/revoke
```

### 🛡️ Security Features

- Automatic state parameter generation and validation
- CSRF protection built-in
- Secure random generation using Web Crypto API
- Warning messages for insecure practices

## Migration from discord-oauth2

Replace your imports:

```typescript
// OLD
import DiscordOAuth2 from 'discord-oauth2';

// NEW
import { DiscordOAuth, DiscordScopes } from '@/lib/discord-oauth';
```

The API is similar but with better TypeScript support and browser compatibility.

## Error Handling

The library provides detailed error messages and handles Discord API errors gracefully:

```typescript
try {
  const user = await oauth.getUser(accessToken);
} catch (error) {
  console.error('Discord API error:', error.message);
  // Handle error appropriately
}
```

## Utilities

### Avatar URLs
```typescript
const avatarUrl = DiscordOAuthUtils.getAvatarUrl(userId, avatarHash, 256);
```

### Callback Parsing
```typescript
const { code, state, error } = DiscordOAuthUtils.parseCallback(window.location.href);
```

### State Generation
```typescript
const state = DiscordOAuthUtils.generateState();
```

This implementation provides a secure, browser-compatible, and feature-complete replacement for the problematic `discord-oauth2` package.
