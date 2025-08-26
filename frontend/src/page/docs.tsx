// Page for holding documentation related to the Winter Dragon Project
import { routeManager } from "@/hooks/routes";

routeManager.addRoute("/docs", DocsPage);

export default function DocsPage() {
  return (
    <div>
      <h1>Documentation</h1>
      <p>This is the documentation page for the Winter Dragon Project.</p>
    </div>
  );
}
