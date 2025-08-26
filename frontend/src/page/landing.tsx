// Landing page for the Winter Dragon Project and documentation

import { routeManager } from "@/hooks/routes";

routeManager.addRoute("/", Landing);

export default function Landing() {
  return (
    <div>
      <h1>Welcome to the Winter Dragon Project</h1>
      <p>This is the landing page for the Winter Dragon Project and its documentation.</p>
    </div>
  );
}
