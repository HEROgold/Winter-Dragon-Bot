import { useEffect } from "react";
import { FeaturePageTemplate } from "../../components/ui/FeaturePageTemplate";

export default function LoggingFeature() {
  useEffect(() => {
    document.title = "Logging Features | Winter Dragon Bot";
  }, []);

  const featureDetails = [
    {
      title: "Message Logging",
      description: "Keep track of important message events",
      items: [
        "Message edits with before/after comparisons",
        "Message deletions with content recovery",
        "Bulk deletion tracking",
        "File and attachment logging"
      ]
    },
    {
      title: "Member Event Logging",
      description: "Monitor member activity in your server",
      items: [
        "Join/leave events with account details",
        "Nickname and username changes",
        "Avatar updates",
        "Role modifications"
      ]
    },
    {
      title: "Server Change Logging",
      description: "Track administrative changes",
      items: [
        "Channel creation/deletion/updates",
        "Role changes and permission updates",
        "Server setting modifications",
        "Webhook and integration tracking"
      ]
    },
    {
      title: "Advanced Filters",
      description: "Fine-tune your logging setup",
      items: [
        "Channel-specific logging options",
        "User and role exclusions",
        "Custom log formats",
        "Log retention policies"
      ]
    }
  ];

  const commandReferences = [
    {
      command: "/logging setup",
      description: "Configure logging channels and options",
      permission: "Administrator"
    },
    {
      command: "/logging channel <type> <#channel>",
      description: "Set a specific logging channel for different event types",
      permission: "Administrator"
    },
    {
      command: "/logging toggle <event-type>",
      description: "Enable or disable specific logging events",
      permission: "Administrator"
    },
    {
      command: "/logging ignore <#channel/@role/@user>",
      description: "Exclude a channel, role, or user from being logged",
      permission: "Administrator"
    },
    {
      command: "/logging status",
      description: "View your current logging configuration",
      permission: "Manage Server"
    }
  ];

  return (
    <FeaturePageTemplate
      title="Advanced Logging"
      subtitle="Comprehensive Server Tracking"
      description="Winter Dragon Bot provides detailed, customizable logging for all server activities. Keep track of important events, maintain server security, and have complete records of changes for moderation purposes."
      featureDetails={featureDetails}
      commandReferences={commandReferences}
    />
  );
}
