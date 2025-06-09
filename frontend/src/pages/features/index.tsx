import { useEffect } from "react";
import { Link } from "react-router-dom";
import { FeatureCard } from "../../components/ui/FeatureCard";

// Feature data similar to what's used in FeaturesSection but with shorter descriptions
const featureData = [
  {
    title: "Moderation Tools",
    description: "Complete suite of moderation commands to keep your server safe and organized.",
    badgeText: "Core",
    badgeColor: "primary",
    link: "/features/moderation"
  },
  {
    title: "Auto-Moderation",
    description: "Configurable auto-moderation features to filter spam and unwanted content.",
    badgeText: "Smart",
    badgeColor: "secondary",
    link: "/features/auto-mod"
  },
  {
    title: "Custom Commands",
    description: "Create your own server-specific commands with custom responses.",
    badgeText: "Customizable",
    badgeColor: "accent",
    link: "/features/custom-commands"
  },
  {
    title: "Welcome System",
    description: "Customize welcome messages and role assignments for new members.",
    badgeText: "Community",
    badgeColor: "info",
    link: "/features/welcome"
  },
  {
    title: "Advanced Logging",
    description: "Comprehensive logging system for all server events.",
    badgeText: "Admin",
    badgeColor: "warning",
    link: "/features/logging"
  },
  {
    title: "Fun & Games",
    description: "Variety of fun commands, games, and utilities to keep your server engaged.",
    badgeText: "Entertainment",
    badgeColor: "success",
    link: "/features/fun"
  }
] as const;

export default function FeaturesIndex() {
  // Add animation effect when component mounts - same as in Home.tsx
  useEffect(() => {
    const featuresEl = document.getElementById('features-section');
    if (featuresEl) {
      featuresEl.classList.add('animate-fadeIn');
    }
  }, []);

  return (
    <div id="features-section" className="py-8 px-4 max-w-7xl mx-auto">
      <h1 className="text-4xl font-bold text-center mb-8">All Features</h1>
      <p className="text-lg text-center mb-12 max-w-3xl mx-auto">
        Winter Dragon Bot offers a comprehensive set of features designed to enhance your Discord server. 
        Click on any feature to learn more about its capabilities and commands.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {featureData.map((feature, index) => (
          <Link to={feature.link} key={index} className="transition-transform hover:scale-105">
            <div className="card bg-base-200 shadow-xl h-full">
              <div className="card-body">
                <div className={`badge badge-${feature.badgeColor} mb-2`}>{feature.badgeText}</div>
                <h2 className="card-title">{feature.title}</h2>
                <p>{feature.description}</p>
                <div className="card-actions justify-end mt-4">
                  <span className="text-primary-content/80 text-sm font-medium">Learn More →</span>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="divider my-16">Additional Features</div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <div className="card bg-base-200 shadow-xl">
          <div className="card-body">
            <div className="badge badge-neutral mb-2">Utility</div>
            <h2 className="card-title">Server Statistics</h2>
            <p>Track member activity, engagement metrics, and growth trends for your server.</p>
            <div className="card-actions justify-end mt-4">
              <span className="text-primary-content/80 text-sm font-medium">Coming Soon</span>
            </div>
          </div>
        </div>
        
        <div className="card bg-base-200 shadow-xl">
          <div className="card-body">
            <div className="badge badge-neutral mb-2">Utility</div>
            <h2 className="card-title">Event Scheduler</h2>
            <p>Create, manage, and automate server events with custom reminders.</p>
            <div className="card-actions justify-end mt-4">
              <span className="text-primary-content/80 text-sm font-medium">Coming Soon</span>
            </div>
          </div>
        </div>
        
        <div className="card bg-base-200 shadow-xl">
          <div className="card-body">
            <div className="badge badge-neutral mb-2">Premium</div>
            <h2 className="card-title">Advanced Analytics</h2>
            <p>In-depth reports and insights about server activity and member engagement.</p>
            <div className="card-actions justify-end mt-4">
              <Link to="/premium" className="text-primary text-sm font-medium">Premium Feature →</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}