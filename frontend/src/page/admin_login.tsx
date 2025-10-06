import { routeManager } from "@/hooks/routes";

routeManager.addRoute("/admin/login", AdminLoginPage);

export default function AdminLoginPage() {
  return (
    <div>
      <h1>Admin Login</h1>
      <p>Please enter your credentials to access the admin panel.</p>
    </div>
  );
}
