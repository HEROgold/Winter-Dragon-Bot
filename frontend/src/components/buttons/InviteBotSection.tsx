import { InviteBot } from "../sections/InviteBot";

export function InviteBotSection() {
  return <div className="bg-base-300 rounded-lg p-8 mt-12 text-center max-w-4xl mx-auto">
    <h2 className="text-2xl font-bold mb-4">Ready to enhance your server?</h2>
    <p className="mb-6">Add Winter Dragon Bot to your Discord server today and unlock all these powerful features!</p>
    <InviteBot />
  </div>;
}

