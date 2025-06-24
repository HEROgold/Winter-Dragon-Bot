import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { DiscordOAuth, DiscordOAuthUtils, DiscordScopes, type DiscordUser } from '@/lib/discord-oauth';

export interface User {
  id: string;
  username: string;
  discriminator: string;
  global_name?: string;
  avatar: string | null;
  email?: string;
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

// Discord OAuth2 configuration from environment variables
const DISCORD_CLIENT_ID = 1226868250713784331 || process.env.BUN_PUBLIC_DISCORD_CLIENT_ID;
const REDIRECT_URI = `${window.location.origin}/callback`;

// Initialize our custom Discord OAuth2 client
const oauth = new DiscordOAuth({
  clientId: DISCORD_CLIENT_ID,
  redirectUri: REDIRECT_URI,
  scopes: [DiscordScopes.IDENTIFY, DiscordScopes.EMAIL, DiscordScopes.GUILDS],
});

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in by checking localStorage
    const storedUser = localStorage.getItem('user');
    const storedAccessToken = localStorage.getItem('access_token');
    
    if (storedUser && storedAccessToken) {
      try {
        const userData = JSON.parse(storedUser);
        setUser(userData);
      } catch (error) {
        console.error('Error parsing stored user data:', error);
        localStorage.removeItem('user');
        localStorage.removeItem('access_token');
      }
    }
    setIsLoading(false);
  }, []);

  const login = () => {
    try {
      if (!DISCORD_CLIENT_ID) {
        console.error('Discord client ID is not set in environment variables');
        return;
      }

      // Generate Discord OAuth2 URL using our custom library
      const state = DiscordOAuthUtils.generateState();
      const authUrl = oauth.generateAuthUrl({
        state: state,
      });
      
      // Store the state in sessionStorage for verification in callback
      sessionStorage.setItem('oauth_state', state);
      
      console.log('Redirecting to Discord OAuth2 URL:', authUrl);
      
      // Redirect to Discord OAuth2
      window.location.href = authUrl;
    } catch (error) {
      console.error('Error generating Discord OAuth URL:', error);
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('user');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  };

  const setUserData = (userData: User) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const isAuthenticated = user !== null;
  return (
    <AuthContext.Provider value={{
      user,
      isLoading,
      login,
      logout,
      isAuthenticated,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Export the oauth client and utilities for use in callback components
export { oauth, DiscordOAuthUtils };
export const setAuthUserData = (userData: User) => {
  localStorage.setItem('user', JSON.stringify(userData));
};
