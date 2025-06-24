import { useAuth } from "@/contexts/AuthContext";

export default function DashboardIndex() {
  const { user } = useAuth();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="card w-96 bg-base-100 shadow-xl">
        <div className="card-body">
          <h1 className="card-title text-4xl font-bold mb-6">Dashboard</h1>
          <p className="text-lg text-gray-700 mb-4">Welcome to your dashboard!</p>
          
          {user && (
            <div className="bg-base-200 p-4 rounded-lg">
              <h2 className="text-xl font-semibold mb-2">User Information</h2>
              <div className="space-y-2">
                <p><strong>Username:</strong> {user.username}#{user.discriminator}</p>
                <p><strong>Discord ID:</strong> {user.id}</p>
                {user.avatar && (
                  <div className="flex items-center gap-2">
                    <strong>Avatar:</strong>
                    <img 
                      src={`https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`}
                      alt={`${user.username}'s avatar`}
                      className="w-8 h-8 rounded-full"
                    />
                  </div>
                )}
              </div>
            </div>
          )}
          
          <p className="text-md text-gray-500 mt-4">This is a placeholder for your dashboard content.</p>
          {/* Add more dashboard components or links as needed */}
        </div>
      </div>
    </div>
  );
}