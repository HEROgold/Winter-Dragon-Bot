import { ModerationCard } from "../cards/ModerationCard";
import { AutoModerationCard } from "../cards/AutoModerationCard";
import { CustomCommandsCard } from "../cards/CustomCommandsCard";
import { WelcomeSystemCard } from "../cards/WelcomeSystemCard";
import { LoggingCard } from "../cards/LoggingCard";
import { CommandsCard } from "../cards/CommandsCard";
import { StatsSection } from "./StatsSection";
import { CTASection } from "./CTASection";

export function FeaturesSection() {
  return <div id="features-section" className="py-12 px-4">
    <h2 className="text-3xl font-bold text-center mb-12">Bot Features</h2>

    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
      {/* Moderation Card */}
      {ModerationCard()}

      {/* Auto-moderation Card */}
      {AutoModerationCard()}

      {/* Custom Commands Card */}
      {CustomCommandsCard()}

      {/* Welcome System Card */}
      {WelcomeSystemCard()}

      {/* Logging Card */}
      {LoggingCard()}

      {/* Fun Commands Card */}
      {CommandsCard()}
    </div>

    {/* Stats section */}
    {StatsSection()}

    {/* CTA section */}
    {CTASection()}
  </div>;
}
