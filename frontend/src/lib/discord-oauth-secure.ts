/**
 * Discord OAuth Backend Proxy
 * Secure server-side handling of OAuth token exchange
 * 
 * This file demonstrates how to implement the OAuth flow securely
 * by keeping client secrets on the backend.
 */

import { DiscordOAuth, DiscordOAuthUtils, type TokenResponse, type DiscordUser } from './discord-oauth';

export interface BackendOAuthConfig {
  // Frontend configuration (safe to expose)
  clientId: string;
  redirectUri: string;
  scopes: string[];
  // Backend endpoint URLs
  backendBaseUrl: string;
}

/**
 * Secure Discord OAuth client that uses backend endpoints
 * to handle sensitive operations (token exchange, refresh)
 */
export class SecureDiscordOAuth {
  private oauth: DiscordOAuth;
  private backendBaseUrl: string;

  constructor(config: BackendOAuthConfig) {
    this.oauth = new DiscordOAuth({
      clientId: config.clientId,
      redirectUri: config.redirectUri,
      scopes: config.scopes,
    });
    this.backendBaseUrl = config.backendBaseUrl.replace(/\/$/, ''); // Remove trailing slash
  }

  /**
   * Generate authorization URL (safe for frontend)
   */
  generateAuthUrl(options?: Parameters<DiscordOAuth['generateAuthUrl']>[0]): string {
    return this.oauth.generateAuthUrl(options);
  }

  /**
   * Exchange authorization code for access token via backend
   * @param code Authorization code from callback
   * @returns Token response from backend
   */
  async exchangeCode(code: string): Promise<TokenResponse> {
    const response = await fetch(`${this.backendBaseUrl}/auth/discord/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        code,
        redirect_uri: this.oauth['config'].redirectUri,
      }),
      credentials: 'include', // Include cookies for session management
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Token exchange failed: ${response.status} ${error}`);
    }

    return response.json();
  }

  /**
   * Refresh access token via backend
   * @param refreshToken Refresh token
   * @returns New token response
   */
  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    const response = await fetch(`${this.backendBaseUrl}/auth/discord/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Token refresh failed: ${response.status} ${error}`);
    }

    return response.json();
  }

  /**
   * Get current user (can be done directly from frontend with access token)
   */
  async getUser(accessToken: string): Promise<DiscordUser> {
    return this.oauth.getUser(accessToken);
  }

  /**
   * Get user's guilds (can be done directly from frontend with access token)
   */
  async getUserGuilds(accessToken: string, options?: Parameters<DiscordOAuth['getUserGuilds']>[1]) {
    return this.oauth.getUserGuilds(accessToken, options);
  }

  /**
   * Get user's connections (can be done directly from frontend with access token)
   */
  async getUserConnections(accessToken: string) {
    return this.oauth.getUserConnections(accessToken);
  }

  /**
   * Revoke token via backend
   * @param accessToken Access token to revoke
   */
  async revokeToken(accessToken: string): Promise<void> {
    const response = await fetch(`${this.backendBaseUrl}/auth/discord/revoke`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        access_token: accessToken,
      }),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Token revocation failed: ${response.status} ${error}`);
    }
  }

  /**
   * Get current authorization info (can be done directly from frontend)
   */
  async getCurrentAuthorizationInfo(accessToken: string) {
    return this.oauth.getCurrentAuthorizationInfo(accessToken);
  }
}

/**
 * Backend API endpoints specification
 * 
 * These are the endpoints your backend should implement:
 * 
 * POST /auth/discord/token
 * Body: { code: string, redirect_uri: string }
 * Response: TokenResponse
 * 
 * POST /auth/discord/refresh
 * Body: { refresh_token: string }
 * Response: TokenResponse
 * 
 * POST /auth/discord/revoke
 * Body: { access_token: string }
 * Response: void
 */

// Export utilities
export { DiscordOAuthUtils, DiscordScopes } from './discord-oauth';
