import { useEffect } from "react";
import { FeaturePage } from "../../templates/FeaturePageTemplate";

export default function CustomCommandsFeature() {
  useEffect(() => {
    document.title = "Custom Commands | Winter Dragon Bot";
  }, []);

  const featureDetails = [
    {
      title: "Create Your Own Commands",
      description: "Make custom commands tailored to your server's needs",
      items: [
        "Simple text responses for FAQs",
        "Complex embed messages with formatting",
        "Randomized response selection",
        "Command cooldowns and usage limits"
      ]
    },
    {
      title: "Dynamic Content",
      description: "Add dynamic elements to your custom commands",
      items: [
        "User variables (name, ID, avatar, etc.)",
        "Server variables (member count, server age)",
        "Date and time formatting",
        "Conditional responses based on roles"
      ]
    },
    {
      title: "Triggers & Automation",
      description: "Set up commands to trigger automatically",
      items: [
        "Keyword triggers in conversation",
        "Scheduled command execution",
        "Event-based triggers (user join, reactions)",
        "Channel-specific automatic responses"
      ]
    },
    {
      title: "Command Management",
      description: "Easy tools to manage your custom commands",
      items: [
        "Web dashboard for command creation",
        "Import/export command configurations",
        "Usage statistics and analytics",
        "Permission-based command access"
      ]
    }
  ];

  const commandReferences = [
    {
      command: "/cmd create <name> <response>",
      description: "Create a simple custom command",
      permission: "Manage Server"
    },
    {
      command: "/cmd embed <name>",
      description: "Start the embed builder for a custom command",
      permission: "Manage Server"
    },
    {
      command: "/cmd edit <name> <new-response>",
      description: "Edit an existing custom command",
      permission: "Manage Server"
    },
    {
      command: "/cmd delete <name>",
      description: "Delete a custom command",
      permission: "Manage Server"
    },
    {
      command: "/cmd list",
      description: "List all custom commands on this server",
      permission: "Everyone"
    }
  ];

  return (
    <FeaturePage
      title="Custom Commands"
      subtitle="Personalize Your Server Experience"
      description="Create your own custom commands to provide server information, automate responses, or add fun interactions unique to your community. Winter Dragon Bot's powerful custom command system offers flexibility and ease of use."
      featureDetails={featureDetails}
      commandReferences={commandReferences}
    />
  );
}
