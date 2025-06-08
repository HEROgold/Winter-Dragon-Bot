import { useEffect } from "react";
import { Navbar } from "../components/navigation/Navbar";
import { Footer } from "../components/cards/Footer";
import { FeaturesSection } from "../components/sections/FeaturesSection";
import { BotInformation } from "../components/sections/BotInformation";
import { BreadCrumbs } from "../components/navigation/BreadCrumbs";

export default function Home() {
  // Add animation effect when component mounts
  useEffect(() => {
    const featuresEl = document.getElementById('features-section');
    if (featuresEl) {
      featuresEl.classList.add('animate-fadeIn');
    }
  }, []);

  return (
    <div className="min-h-screen bg-base-100">
      {/* Navigation */}
      {Navbar()}
      {BreadCrumbs()}

      {/* Hero section */}
      {BotInformation()}

      {/* Features section */}
      {FeaturesSection()}

      {/* Footer section */}
      {Footer()}
    </div>
  );
}
