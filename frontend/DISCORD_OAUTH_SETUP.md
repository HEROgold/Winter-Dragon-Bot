# Discord OAuth2 Setup with discord-oauth2 Package

This application uses the `discord-oauth2` npm package for Discord OAuth2 authentication. Follow these steps to set it up:

## 1. Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "OAuth2" section in the sidebar

## 2. Configure OAuth2 Settings

1. In the "OAuth2" section, find "Redirects"
2. Add your callback URL: `http://localhost:3000/callback` (for development)
3. For production, add your production domain: `https://yourdomain.com/callback`

## 3. Get Your Credentials

1. In the "OAuth2" section, copy your "Client ID"
2. In the "OAuth2" section, copy your "Client Secret"

## 4. Set Environment Variables

1. Copy `.env.example` to `.env`
2. Replace the placeholder values with your actual Discord credentials:

```env
VITE_DISCORD_CLIENT_ID=your_actual_client_id
VITE_DISCORD_CLIENT_SECRET=your_actual_client_secret
```

## 5. Required OAuth2 Scopes

The application uses the following Discord OAuth2 scopes:

- `identify` - To get basic user information (username, ID, avatar)
- `email` - To get the user's email address

## 6. Security Notes

- **⚠️ IMPORTANT**: This implementation includes the client secret in the frontend code for development purposes
- **🚨 PRODUCTION WARNING**: Never expose your client secret in production frontend code
- For production, implement a backend API endpoint to handle token exchange
- Consider using environment-specific configurations for different deployment environments
- The client secret should be handled server-side only

## 7. discord-oauth2 Package Features Used

This implementation uses the following features of the discord-oauth2 package:

- **URL Generation**: `oauth.generateAuthUrl()` for creating secure Discord OAuth URLs
- **Token Exchange**: `oauth.tokenRequest()` for exchanging authorization codes for access tokens
- **User Data**: `oauth.getUser()` for fetching authenticated user information
- **State Parameter**: Automatic secure state generation for CSRF protection

## 8. Application Features

- Login/Logout functionality with Discord
- Protected dashboard route (requires authentication)
- User avatar and information display
- Persistent login state using localStorage
- Secure state parameter verification
- Comprehensive error handling
