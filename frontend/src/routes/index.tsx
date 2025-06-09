import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import Home from '../pages/Home';
import Layout from '../components/layout/Layout';

// Feature pages
import FeaturesIndex from '../pages/features/index';
import ModerationFeature from '../pages/features/Moderation';
import AutoModFeature from '../pages/features/AutoMod';
import CustomCommandsFeature from '../pages/features/CustomCommands';
import WelcomeFeature from '../pages/features/Welcome';
import LoggingFeature from '../pages/features/Logging';
import FunFeature from '../pages/features/Fun';

// Create routes
const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,    children: [
      { index: true, element: <Home /> },
      { path: "features", element: <FeaturesIndex /> },
      { path: "features/moderation", element: <ModerationFeature /> },
      { path: "features/auto-mod", element: <AutoModFeature /> },
      { path: "features/custom-commands", element: <CustomCommandsFeature /> },
      { path: "features/welcome", element: <WelcomeFeature /> },
      { path: "features/logging", element: <LoggingFeature /> },
      { path: "features/fun", element: <FunFeature /> },
    ],
  },
]);

export function Routes() {
  return <RouterProvider router={router} />;
}
