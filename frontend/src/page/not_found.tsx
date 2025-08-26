
import { routeManager } from "@/hooks/routes";

routeManager.addRoute("/404", NotFoundPage);

export default function NotFoundPage() {
  return (
    <div>
      <h1>404 - Not Found</h1>
      <p>The page you are looking for does not exist.</p>
    </div>
  );
}
