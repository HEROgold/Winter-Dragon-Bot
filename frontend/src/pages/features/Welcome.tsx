import { useEffect } from "react";
import { FeaturePage } from "../../templates/FeaturePageTemplate";

export default function WelcomeFeature() {
  useEffect(() => {
    document.title = "Welcome System | Winter Dragon Bot";
  }, []);

  const featureDetails = [
    {
      title: "Customizable Welcome Messages",
      description: "Greet new members with personalized messages",
      items: [
        "Text-based welcome messages with variables",
        "Rich embed welcome cards with user info",
        "Custom images and banners",
        "Multi-language support"
      ]
    },
    {
      title: "Welcome Channels",
      description: "Configure where and how welcome messages appear",
      items: [
        "Dedicated welcome channel setup",
        "Private DM welcomes",
        "Staff notifications for new joins",
        "Timed message deletion options"
      ]
    },
    {
      title: "Automatic Role Assignment",
      description: "Streamline new member onboarding",
      items: [
        "Assign default member roles on join",
        "Role menus for self-service role selection",
        "Temporary trial roles with auto-upgrade",
        "Verification role gates"
      ]
    },
    {
      title: "Member Screening",
      description: "Ensure quality membership",
      items: [
        "Customizable verification requirements",
        "Rules acceptance tracking",
        "Account age screening",
        "Integration with Discord's membership screening"
      ]
    }
  ];

  const commandReferences = [
    {
      command: "/welcome setup",
      description: "Start the welcome system setup wizard",
      permission: "Administrator"
    },
    {
      command: "/welcome message <message>",
      description: "Set the welcome message text/embed",
      permission: "Manage Server"
    },
    {
      command: "/welcome channel <#channel>",
      description: "Set the welcome message channel",
      permission: "Manage Server"
    },
    {
      command: "/welcome test",
      description: "Test the current welcome message configuration",
      permission: "Manage Server"
    },
    {
      command: "/welcome autorole <@role>",
      description: "Set a role to be automatically assigned to new members",
      permission: "Administrator"
    }
  ];

  return (
    <FeaturePage
      title="Welcome System"
      subtitle="First Impressions Matter"
      description="Make new members feel at home with Winter Dragon Bot's comprehensive welcome system. Create engaging first interactions, provide clear guidance, and streamline the onboarding process for your community."
      featureDetails={featureDetails}
      commandReferences={commandReferences}
    />
  );
}
