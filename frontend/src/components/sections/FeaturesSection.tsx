import { FeatureCard } from "../ui/FeatureCard";

// Feature data array to make maintenance easier
const featureData = [
  {
    title: "Moderation Tools",
    description: "Complete suite of moderation commands to keep your server safe and organized. Ban, kick, mute, warn users with logging.",
    badgeText: "Core",
    badgeColor: "primary",
    link: "/features/moderation"
  },
  {
    title: "Auto-Moderation",
    description: "Configurable auto-moderation features to filter spam, inappropriate content, and unwanted links with customizable rule sets.",
    badgeText: "Smart",
    badgeColor: "secondary",
    link: "/features/auto-mod"
  },
  {
    title: "Custom Commands",
    description: "Create your own server-specific commands with custom responses, embed messages, and automatic triggers.",
    badgeText: "Customizable",
    badgeColor: "accent",
    link: "/features/custom-commands"
  },
  {
    title: "Welcome System",
    description: "Customize welcome messages with embed templates, role assignments, and welcome channels to greet new members.",
    badgeText: "Community",
    badgeColor: "info",
    link: "/features/welcome"
  },
  {
    title: "Advanced Logging",
    description: "Comprehensive logging system for all server events including message edits, deletions, member joins/leaves, and moderation actions.",
    badgeText: "Admin",
    badgeColor: "warning",
    link: "/features/logging"
  },
  {
    title: "Fun & Games",
    description: "Variety of fun commands, games, memes, and utilities to keep your server members engaged and entertained.",
    badgeText: "Entertainment",
    badgeColor: "success",
    link: "/features/fun"
  }
] as const;

export function FeaturesSection() {
  // TODO: add #features anchor link functionality, so we can scroll to this section from links.
  return <div id="features-section" className="py-12 px-4">
    <h2 className="text-3xl font-bold text-center mb-12">Bot Features</h2>

    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
      {featureData.map((feature, index) => (
        <FeatureCard
          key={index}
          title={feature.title}
          description={feature.description}
          badgeText={feature.badgeText}
          badgeColor={feature.badgeColor}
          link={feature.link}
        />
      ))}
    </div>
  </div>;
}
