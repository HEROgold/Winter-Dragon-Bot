import { useEffect } from "react";
import { FeaturePage } from "../../templates/FeaturePageTemplate";

export default function FunFeature() {
  useEffect(() => {
    document.title = "Fun & Games | Winter Dragon Bot";
  }, []);

  const featureDetails = [
    {
      title: "Interactive Games",
      description: "Engage your community with fun games",
      items: [
        "Trivia contests with leaderboards",
        "Word games and hangman",
        "Rock-paper-scissors and other quick games",
        "Multi-player quiz competitions"
      ]
    },
    {
      title: "Memes & Media",
      description: "Entertain server members with media content",
      items: [
        "Random meme generator from various sources",
        "GIF search integration",
        "Image manipulation commands",
        "Animal picture commands"
      ]
    },
    {
      title: "Utility Commands",
      description: "Useful tools for everyday Discord usage",
      items: [
        "Weather forecasts for any location",
        "Wikipedia summaries and searches",
        "Unit conversions and calculations",
        "Translation between languages"
      ]
    },
    {
      title: "Social Features",
      description: "Foster community engagement",
      items: [
        "User profile cards and customization",
        "Global and server-specific economy",
        "Achievement systems and badges",
        "Birthday tracking and celebrations"
      ]
    }
  ];

  const commandReferences = [
    {
      command: "/trivia [category]",
      description: "Start a trivia game with optional category selection",
      permission: "Everyone"
    },
    {
      command: "/meme",
      description: "Get a random meme from popular subreddits",
      permission: "Everyone"
    },
    {
      command: "/weather <location>",
      description: "Get the current weather for a location",
      permission: "Everyone"
    },
    {
      command: "/profile [user]",
      description: "View your profile or another user's profile",
      permission: "Everyone"
    },
    {
      command: "/game <game-name>",
      description: "Start a specific game in the current channel",
      permission: "Everyone"
    }
  ];

  return (
    <FeaturePage
      title="Fun & Games"
      subtitle="Entertainment for Your Community"
      description="Keep your community engaged and entertained with Winter Dragon Bot's variety of fun commands, games, and utility features. From memes to trivia contests, there's something for everyone."
      featureDetails={featureDetails}
      commandReferences={commandReferences}
    />
  );
}
