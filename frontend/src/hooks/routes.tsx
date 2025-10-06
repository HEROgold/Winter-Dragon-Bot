// A hook that manages routes, and generates a navbar.

import { Link } from "react-router-dom";

class RouteManager {
  private routes: Array<{ path: string; component: React.ComponentType }> = [];

  constructor() {
    this.routes = [];
  }

  addRoute(path: string, component: React.ComponentType) {
    this.routes.push({ path, component });
  }

  getRoutes() {
    return this.routes;
  }
}

export function NavbarLinks() {
  const routes = routeManager.getRoutes();

  return (
    <ul className="navbar-nav">
      {routes.map((route) => (
        <li className="nav-item" key={route.path}>
          <Link className="nav-link" to={route.path}>
            {route.path}
          </Link>
        </li>
      ))}
    </ul>
  );
}

export const routeManager = new RouteManager();
