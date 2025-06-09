import { useEffect } from "react";
import { FeaturePageTemplate } from "../../components/ui/FeaturePageTemplate";

export default function AutoModFeature() {
  useEffect(() => {
    document.title = "Auto-Moderation | Winter Dragon Bot";
  }, []);

  const featureDetails = [
    {
      title: "Content Filtering",
      description: "Automatically detect and remove inappropriate content",
      items: [
        "Profanity filtering with customizable word lists",
        "NSFW content detection and removal",
        "Spam prevention with rate limiting",
        "Mass mention protection"
      ]
    },
    {
      title: "Link Control",
      description: "Manage links posted in your server",
      items: [
        "Whitelist/blacklist domains",
        "Automatic phishing link detection",
        "Discord invite filtering",
        "Social media link controls"
      ]
    },
    {
      title: "Raid Protection",
      description: "Prevent server raids and mass join attacks",
      items: [
        "Join rate monitoring with automatic lockdown",
        "Account age verification",
        "Verification systems and captcha",
        "IP-based protection measures"
      ]
    },
    {
      title: "Rule Enforcement",
      description: "Enforce server rules automatically",
      items: [
        "Custom rule triggers with regex support",
        "Automatic warning and punishment escalation",
        "Role-based exemptions and overrides",
        "Channel-specific rule configurations"
      ]
    }
  ];

  const commandReferences = [
    {
      command: "/automod setup",
      description: "Start the auto-moderation setup wizard",
      permission: "Administrator"
    },
    {
      command: "/automod filter add <type> <value>",
      description: "Add a word/phrase/regex to the filter",
      permission: "Manage Server"
    },
    {
      command: "/automod filter remove <type> <value>",
      description: "Remove a filter entry",
      permission: "Manage Server"
    },
    {
      command: "/automod settings <feature> <enabled/disabled>",
      description: "Enable or disable specific auto-mod features",
      permission: "Manage Server"
    },
    {
      command: "/automod exempt <user/role/channel>",
      description: "Exempt users, roles, or channels from auto-moderation",
      permission: "Administrator"
    }
  ];

  return (
    <FeaturePageTemplate
      title="Auto-Moderation"
      subtitle="Automated Server Protection"
      description="Winter Dragon Bot's advanced auto-moderation system helps keep your server safe without requiring constant manual oversight. Configure powerful filters and automated responses to handle common moderation issues."
      featureDetails={featureDetails}
      commandReferences={commandReferences}
    />
  );
}
