
import { routeManager } from "@/hooks/routes";

routeManager.addRoute("/login", UserLoginPage);

export default function UserLoginPage() {
  return (
    <div>
      <h1>User Login</h1>
      <p>Please enter your credentials to access your account.</p>
    </div>
  );
}
