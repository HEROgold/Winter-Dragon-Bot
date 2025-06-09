import { StatsSection } from "./StatsSection";

export function BotInformation() {
  return <div className="hero bg-base-200 py-12">
    <div className="hero-content text-center">
      <div className="max-w-3xl">
        <h1 className="text-5xl font-bold text-primary">Winter Dragon</h1>
        <BotAvatar />
        <p className="py-6 text-lg">Your powerful Discord companion for server management, moderation, fun interactions, and much more!</p>
        <ExplorationLinks />
        <StatsSection />
      </div>
    </div>
  </div>;
}

function BotAvatar() {
  return <div className="avatar my-6">
    <div className="w-24 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
      <img src="/dragon-icon.png" alt="Winter Dragon Bot" onError={(e) => {
        e.currentTarget.src = "https://placehold.co/200x200?text=WD";
      } } />
    </div>
  </div>;
}

function ExplorationLinks() {
  return <div className="flex justify-center gap-4 flex-wrap">
    <a href="#features" className="btn btn-primary">Explore Features</a>
    <a href="/commands" className="btn btn-accent">View Commands</a>
    <a href="/dashboard" className="btn btn-secondary">Dashboard</a>
  </div>;
}
