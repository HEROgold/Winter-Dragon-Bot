/**
 * Custom Discord OAuth2 Library
 * Browser-compatible replacement for discord-oauth2 package
 * 
 * Based on Discord's OAuth2 documentation:
 * https://discord.com/developers/docs/topics/oauth2
 */

// Discord OAuth2 Configuration
export interface DiscordOAuthConfig {
  clientId: string;
  redirectUri: string;
  scopes: string[];
  state?: string;
}

// Discord User Object
export interface DiscordUser {
  id: string;
  username: string;
  discriminator: string;
  global_name?: string;
  avatar: string | null;
  bot?: boolean;
  system?: boolean;
  mfa_enabled?: boolean;
  banner?: string | null;
  accent_color?: number | null;
  locale?: string;
  verified?: boolean;
  email?: string | null;
  flags?: number;
  premium_type?: number;
  public_flags?: number;
}

// Discord Guild Object (partial)
export interface DiscordGuild {
  id: string;
  name: string;
  icon: string | null;
  owner: boolean;
  permissions: string;
  features: string[];
}

// OAuth Token Response
export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token: string;
  scope: string;
}

// Discord API Base URLs
const DISCORD_API_BASE = 'https://discord.com/api/v10';
const DISCORD_CDN_BASE = 'https://cdn.discordapp.com';

/**
 * Custom Discord OAuth2 Client
 * Handles browser-based OAuth flow without Node.js dependencies
 */
export class DiscordOAuth {
  private config: DiscordOAuthConfig;

  constructor(config: DiscordOAuthConfig) {
    this.config = config;
  }

  /**
   * Generate Discord OAuth2 authorization URL
   * @param options Additional options for the OAuth flow
   * @returns Authorization URL string
   */
  generateAuthUrl(options: {
    state?: string;
    prompt?: 'consent' | 'none';
    permissions?: string;
    guildId?: string;
    disableGuildSelect?: boolean;
  } = {}): string {
    const params = new URLSearchParams({
      client_id: this.config.clientId,
      redirect_uri: this.config.redirectUri,
      response_type: 'code',
      scope: this.config.scopes.join(' '),
    });

    // Add optional parameters
    if (options.state || this.config.state) {
      params.append('state', options.state || this.config.state!);
    }

    if (options.prompt) {
      params.append('prompt', options.prompt);
    }

    if (options.permissions) {
      params.append('permissions', options.permissions);
    }

    if (options.guildId) {
      params.append('guild_id', options.guildId);
    }

    if (options.disableGuildSelect) {
      params.append('disable_guild_select', 'true');
    }

    return `${DISCORD_API_BASE}/oauth2/authorize?${params.toString()}`;
  }

  /**
   * Exchange authorization code for access token
   * Note: This should be done on the backend for security!
   * This method is provided for development purposes only.
   * 
   * @param code Authorization code from callback
   * @param clientSecret Client secret (should be backend-only!)
   * @returns Token response
   */
  async exchangeCode(code: string, clientSecret: string): Promise<TokenResponse> {
    console.warn('⚠️ WARNING: Client secret should never be exposed in frontend code!');
    console.warn('⚠️ Move this token exchange to your backend for production!');

    const response = await fetch(`${DISCORD_API_BASE}/oauth2/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        client_id: this.config.clientId,
        client_secret: clientSecret,
        grant_type: 'authorization_code',
        code,
        redirect_uri: this.config.redirectUri,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Token exchange failed: ${response.status} ${error}`);
    }

    return response.json();
  }

  /**
   * Refresh an access token using refresh token
   * @param refreshToken The refresh token
   * @param clientSecret Client secret (should be backend-only!)
   * @returns New token response
   */
  async refreshToken(refreshToken: string, clientSecret: string): Promise<TokenResponse> {
    console.warn('⚠️ WARNING: Client secret should never be exposed in frontend code!');

    const response = await fetch(`${DISCORD_API_BASE}/oauth2/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        client_id: this.config.clientId,
        client_secret: clientSecret,
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Token refresh failed: ${response.status} ${error}`);
    }

    return response.json();
  }

  /**
   * Get current user information
   * @param accessToken Access token
   * @returns Discord user object
   */
  async getUser(accessToken: string): Promise<DiscordUser> {
    const response = await fetch(`${DISCORD_API_BASE}/users/@me`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get user: ${response.status} ${error}`);
    }

    return response.json();
  }

  /**
   * Get user's guilds
   * @param accessToken Access token
   * @param options Query options
   * @returns Array of user's guilds
   */
  async getUserGuilds(accessToken: string, options: {
    before?: string;
    after?: string;
    limit?: number;
    withCounts?: boolean;
  } = {}): Promise<DiscordGuild[]> {
    const params = new URLSearchParams();
    
    if (options.before) params.append('before', options.before);
    if (options.after) params.append('after', options.after);
    if (options.limit) params.append('limit', options.limit.toString());
    if (options.withCounts) params.append('with_counts', 'true');

    const url = `${DISCORD_API_BASE}/users/@me/guilds${params.toString() ? `?${params.toString()}` : ''}`;
    
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get guilds: ${response.status} ${error}`);
    }

    return response.json();
  }

  /**
   * Get user's connections (linked accounts)
   * @param accessToken Access token
   * @returns Array of user connections
   */
  async getUserConnections(accessToken: string): Promise<any[]> {
    const response = await fetch(`${DISCORD_API_BASE}/users/@me/connections`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get connections: ${response.status} ${error}`);
    }

    return response.json();
  }

  /**
   * Revoke an access token
   * @param accessToken Access token to revoke
   * @param clientSecret Client secret (should be backend-only!)
   */
  async revokeToken(accessToken: string, clientSecret: string): Promise<void> {
    console.warn('⚠️ WARNING: Client secret should never be exposed in frontend code!');

    const credentials = btoa(`${this.config.clientId}:${clientSecret}`);
    
    const response = await fetch(`${DISCORD_API_BASE}/oauth2/token/revoke`, {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${credentials}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        token: accessToken,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to revoke token: ${response.status} ${error}`);
    }
  }

  /**
   * Get current authorization information
   * @param accessToken Access token
   * @returns Authorization information
   */
  async getCurrentAuthorizationInfo(accessToken: string): Promise<any> {
    const response = await fetch(`${DISCORD_API_BASE}/oauth2/@me`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get authorization info: ${response.status} ${error}`);
    }

    return response.json();
  }
}

/**
 * Utility functions for Discord OAuth
 */
export class DiscordOAuthUtils {
  /**
   * Generate a cryptographically secure state parameter
   * @returns Random state string
   */
  static generateState(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Parse authorization callback URL
   * @param url Callback URL with query parameters
   * @returns Parsed parameters
   */
  static parseCallback(url: string): {
    code?: string;
    state?: string;
    error?: string;
    error_description?: string;
  } {
    const urlObj = new URL(url);
    const params = new URLSearchParams(urlObj.search);
    
    return {
      code: params.get('code') || undefined,
      state: params.get('state') || undefined,
      error: params.get('error') || undefined,
      error_description: params.get('error_description') || undefined,
    };
  }

  /**
   * Get Discord CDN avatar URL
   * @param userId User ID
   * @param avatarHash Avatar hash
   * @param size Avatar size (default: 128)
   * @returns Avatar URL
   */
  static getAvatarUrl(userId: string, avatarHash: string | null, size: number = 128): string {
    if (!avatarHash) {
      // Default avatar
      const defaultAvatar = (parseInt(userId) >> 22) % 6;
      return `${DISCORD_CDN_BASE}/embed/avatars/${defaultAvatar}.png`;
    }
    
    const extension = avatarHash.startsWith('a_') ? 'gif' : 'png';
    return `${DISCORD_CDN_BASE}/avatars/${userId}/${avatarHash}.${extension}?size=${size}`;
  }

  /**
   * Get Discord CDN guild icon URL
   * @param guildId Guild ID
   * @param iconHash Icon hash
   * @param size Icon size (default: 128)
   * @returns Icon URL
   */
  static getGuildIconUrl(guildId: string, iconHash: string | null, size: number = 128): string {
    if (!iconHash) {
      return '';
    }
    
    const extension = iconHash.startsWith('a_') ? 'gif' : 'png';
    return `${DISCORD_CDN_BASE}/icons/${guildId}/${iconHash}.${extension}?size=${size}`;
  }

  /**
   * Validate Discord snowflake ID
   * @param id Snowflake ID to validate
   * @returns Whether the ID is valid
   */
  static isValidSnowflake(id: string): boolean {
    if (!/^\d+$/.test(id)) return false;
    const snowflake = BigInt(id);
    const discordEpoch = BigInt(1420070400000);
    const timestamp = (snowflake >> BigInt(22)) + discordEpoch;
    const now = BigInt(Date.now());
    return timestamp > discordEpoch && timestamp <= now;
  }
}

/**
 * Common Discord OAuth scopes
 */
export const DiscordScopes = {
  // Basic user information
  IDENTIFY: 'identify',
  EMAIL: 'email',
  
  // Guild information
  GUILDS: 'guilds',
  GUILDS_JOIN: 'guilds.join',
  GUILDS_MEMBERS_READ: 'guilds.members.read',
  
  // Connected accounts
  CONNECTIONS: 'connections',
  
  // Role connections
  ROLE_CONNECTIONS_WRITE: 'role_connections.write',
  
  // Application commands
  APPLICATIONS_COMMANDS: 'applications.commands',
  APPLICATIONS_COMMANDS_UPDATE: 'applications.commands.update',
  APPLICATIONS_COMMANDS_PERMISSIONS_UPDATE: 'applications.commands.permissions.update',
  
  // Bot scope (for bot invites)
  BOT: 'bot',
  
  // Webhook scope
  WEBHOOK_INCOMING: 'webhook.incoming',
  
  // Message content (privileged)
  MESSAGES_READ: 'messages.read',
  
  // RPC scopes
  RPC: 'rpc',
  RPC_NOTIFICATIONS_READ: 'rpc.notifications.read',
  RPC_VOICE_READ: 'rpc.voice.read',
  RPC_VOICE_WRITE: 'rpc.voice.write',
  RPC_ACTIVITIES_WRITE: 'rpc.activities.write',
} as const;

export type DiscordScope = typeof DiscordScopes[keyof typeof DiscordScopes];
