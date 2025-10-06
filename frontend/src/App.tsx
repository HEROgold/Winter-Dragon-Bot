import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";

// Import all pages individually to ensure they're loaded
import "./page/admin_login";
import "./page/docs";
import "./page/landing";
import "./page/not_found";
import "./page/user_login";

import Navbar from "./components/navbar";
import { routeManager } from "./hooks/routes";

const routes = routeManager.getRoutes();
const routeElements = routes.map(({ path, component: Component }) => (
  <Route key={path} path={path} element={<Component />} />
));

export function App() {
  console.log("Registered routes:", routes);
  return (
    <BrowserRouter>
      <Navbar />
      <div className="app">
        <Routes>{routeElements}</Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
