import { useEffect } from "react";

export default function ModerationFeature() {
  useEffect(() => {
    // Add any page-specific effects here
    document.title = "Moderation Features | Winter Dragon Bot";
  }, []);

  return (
    <div className="py-8 px-4 max-w-6xl mx-auto">
      <h1 className="text-4xl font-bold mb-6">Moderation Tools</h1>
      
      <div className="bg-base-200 p-6 rounded-lg shadow-lg mb-8">
        <h2 className="text-2xl font-semibold mb-4">Complete Server Control</h2>
        <p className="mb-4">
          Winter Dragon Bot provides server administrators and moderators with a comprehensive suite of tools 
          to maintain order and ensure a positive experience for all members.
        </p>
        
        <div className="divider my-8">Core Features</div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card bg-base-100 shadow-md">
            <div className="card-body">
              <h3 className="card-title text-xl">User Management</h3>
              <ul className="list-disc pl-5 space-y-2">
                <li>Ban users permanently or temporarily with reason tracking</li>
                <li>Kick troublesome members with notifications</li>
                <li>Timeout (mute) users for specified durations</li>
                <li>Warning system with escalating consequences</li>
              </ul>
            </div>
          </div>
          
          <div className="card bg-base-100 shadow-md">
            <div className="card-body">
              <h3 className="card-title text-xl">Message Control</h3>
              <ul className="list-disc pl-5 space-y-2">
                <li>Bulk message deletion with filters</li>
                <li>Shadow banning troublesome users</li>
                <li>Slow mode configuration for high-traffic channels</li>
                <li>Message content filtering & editing</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      <div className="bg-base-200 p-6 rounded-lg shadow-lg mb-8">
        <h2 className="text-2xl font-semibold mb-4">Command Reference</h2>
        <div className="overflow-x-auto">
          <table className="table w-full">
            <thead>
              <tr>
                <th>Command</th>
                <th>Description</th>
                <th>Permission</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><code>/ban &lt;user&gt; [reason] [duration]</code></td>
                <td>Ban a user from the server</td>
                <td>Ban Members</td>
              </tr>
              <tr>
                <td><code>/kick &lt;user&gt; [reason]</code></td>
                <td>Kick a user from the server</td>
                <td>Kick Members</td>
              </tr>
              <tr>
                <td><code>/timeout &lt;user&gt; &lt;duration&gt; [reason]</code></td>
                <td>Timeout (mute) a user for specified duration</td>
                <td>Moderate Members</td>
              </tr>
              <tr>
                <td><code>/warn &lt;user&gt; [reason]</code></td>
                <td>Issue a warning to a user</td>
                <td>Moderate Members</td>
              </tr>
              <tr>
                <td><code>/purge &lt;amount&gt; [user] [contains]</code></td>
                <td>Delete multiple messages with optional filters</td>
                <td>Manage Messages</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
