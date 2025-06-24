import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import Home from '@/pages/Home';
import Layout from '../templates/Layout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

// Feature pages
import FeaturesIndex from '@/pages/features/index';
import ModerationFeature from '@/pages/features/Moderation';
import AutoModFeature from '@/pages/features/AutoMod';
import CustomCommandsFeature from '@/pages/features/CustomCommands';
import WelcomeFeature from '@/pages/features/Welcome';
import LoggingFeature from '@/pages/features/Logging';
import FunFeature from '@/pages/features/Fun';
import DashboardIndex from '@/pages/dashboard';
import PremiumIndex from '@/pages/premium';
import { Callback } from '@/pages/auth/callback';

// Create routes
export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: "features", element: <FeaturesIndex /> },
      { path: "features/moderation", element: <ModerationFeature /> },
      { path: "features/auto-mod", element: <AutoModFeature /> },
      { path: "features/custom-commands", element: <CustomCommandsFeature /> },
      { path: "features/welcome", element: <WelcomeFeature /> },
      { path: "features/logging", element: <LoggingFeature /> },
      { path: "features/fun", element: <FunFeature /> },
      { path: "dashboard", element: <ProtectedRoute><DashboardIndex /></ProtectedRoute> },
      { path: "premium", element: <PremiumIndex /> },
      { path: "callback", element: <Callback /> },
    ],
  },
]);

export function Routes() {
  return <RouterProvider router={router} />;
}
