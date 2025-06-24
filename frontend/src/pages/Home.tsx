import { useEffect } from "react";
import { FeaturesSection } from "../components/sections/FeaturesSection";
import { BotInformation } from "../components/sections/BotInformation";
import { InviteBotSection } from "@/components/buttons/InviteBotSection";
import { useAuth } from "@/contexts/AuthContext";
import { Link } from "react-router-dom";

export default function Home() {
  const { isAuthenticated, user, login } = useAuth();
  
  // Add animation effect when component mounts
  useEffect(() => {
    const featuresEl = document.getElementById('features-section');
    if (featuresEl) {
      featuresEl.classList.add('animate-fadeIn');
    }
  }, []);

  return (
    <>
      <title>About: Winter Dragon Bot</title>
      
      {/* Authentication Banner */}
      <div className="bg-base-200 p-4">
        <div className="container mx-auto">
          {isAuthenticated ? (
            <div className="alert alert-success">
              <div>
                <h3 className="font-bold">Welcome back, {user?.username}!</h3>
                <div className="text-xs">You're logged in. Check out your <Link to="/dashboard" className="link">dashboard</Link>.</div>
              </div>
            </div>
          ) : (
            <div className="alert alert-info">
              <div>
                <h3 className="font-bold">Get Started with Winter Dragon Bot</h3>
                <div className="text-xs">Login with Discord to access your dashboard and manage your bot settings.</div>
              </div>
              <div className="flex-none">
                {DiscordLoginButton(login)}
              </div>
            </div>
          )}
        </div>
      </div>
      
      <BotInformation />
      <FeaturesSection />
      <InviteBotSection />
    </>
  );
}

function DiscordLoginButton(login: () => void) {
  return <button className="btn btn-sm btn-primary" onClick={login}>
    Login with Discord
  </button>;
}
