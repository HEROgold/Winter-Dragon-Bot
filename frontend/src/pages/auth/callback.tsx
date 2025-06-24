import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { oauth, DiscordOAuthUtils } from '@/contexts/AuthContext';

export function Callback() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Parse the callback URL using our utility
        const callbackData = DiscordOAuthUtils.parseCallback(window.location.href);

        if (callbackData.error) {
          throw new Error(`Discord OAuth error: ${callbackData.error} - ${callbackData.error_description}`);
        }

        if (!callbackData.code) {
          throw new Error('No authorization code received from Discord');
        }

        // Verify state parameter for security
        const storedState = sessionStorage.getItem('oauth_state');
        if (callbackData.state !== storedState) {
          throw new Error('Invalid state parameter - possible CSRF attack');
        }

        // Clean up stored state
        sessionStorage.removeItem('oauth_state');

        console.log('Exchanging code for token...');

        // ⚠️ DEVELOPMENT APPROACH - CLIENT SECRET IN FRONTEND (INSECURE!)
        // This is only for development/demo purposes
        const clientSecret = import.meta.env.VITE_DISCORD_CLIENT_SECRET;
        
        if (clientSecret) {
          console.warn('⚠️ Using client secret in frontend - DEVELOPMENT ONLY!');
          
          // Exchange code for access token using our custom library
          const tokenData = await oauth.exchangeCode(callbackData.code, clientSecret);
          
          console.log('Token received successfully');

          // Store tokens
          localStorage.setItem('access_token', tokenData.access_token);
          if (tokenData.refresh_token) {
            localStorage.setItem('refresh_token', tokenData.refresh_token);
          }

          // Get user data using our custom library
          const userData = await oauth.getUser(tokenData.access_token);

          console.log('User data received:', userData);

          // Store user data with our updated interface
          const user = {
            id: userData.id,
            username: userData.username,
            discriminator: userData.discriminator,
            global_name: userData.global_name,
            avatar: userData.avatar,
            email: userData.email,
          };

          localStorage.setItem('user', JSON.stringify(user));

          // Redirect to dashboard
          navigate('/dashboard');
        } else {
          // 🔒 PRODUCTION APPROACH - USE BACKEND ENDPOINT
          // This is how you should implement it in production
          
          console.log('Using secure backend token exchange...');
          
          // Call your backend endpoint to exchange the code
          const response = await fetch('/api/auth/discord/token', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              code: callbackData.code,
              redirect_uri: window.location.origin + '/callback',
            }),
            credentials: 'include', // Include cookies for session management
          });

          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Backend token exchange failed: ${response.status} ${errorText}`);
          }

          const tokenData = await response.json();
          
          // Store tokens
          localStorage.setItem('access_token', tokenData.access_token);
          if (tokenData.refresh_token) {
            localStorage.setItem('refresh_token', tokenData.refresh_token);
          }

          // Get user data
          const userData = await oauth.getUser(tokenData.access_token);
          
          const user = {
            id: userData.id,
            username: userData.username,
            discriminator: userData.discriminator,
            global_name: userData.global_name,
            avatar: userData.avatar,
            email: userData.email,
          };

          localStorage.setItem('user', JSON.stringify(user));
          navigate('/dashboard');        }

      } catch (err) {
        console.error('Authentication error:', err);
        let errorMessage = 'An unknown error occurred';
        
        if (err instanceof Error) {
          errorMessage = err.message;
        }
        
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    };

    handleCallback();
  }, [navigate]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <div className="loading loading-spinner loading-lg"></div>
        <p className="mt-4 text-lg">Authenticating with Discord...</p>
        <p className="mt-2 text-sm text-gray-500">Using custom Discord OAuth library</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <div className="alert alert-error max-w-md">
          <h3 className="font-bold">Authentication Error</h3>
          <div className="text-sm">{error}</div>
          {error.includes('client_secret') && (
            <div className="text-xs mt-2 opacity-75">
              For development: Set VITE_DISCORD_CLIENT_SECRET in your .env file.<br/>
              For production: Implement backend token exchange endpoint.
            </div>
          )}
        </div>
        <button 
          className="btn btn-primary mt-4"
          onClick={() => navigate('/')}
        >
          Return Home
        </button>
      </div>
    );
  }

  return null;
}