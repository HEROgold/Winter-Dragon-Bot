import { useEffect } from "react";
import { FeaturesSection } from "../components/sections/FeaturesSection";
import { BotInformation } from "../components/sections/BotInformation";
import { InviteBotSection } from "@/components/buttons/InviteBotSection";

export default function Home() {
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
      <BotInformation />
      <FeaturesSection />
      <InviteBotSection />
    </>
  );
}
