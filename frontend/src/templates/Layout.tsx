import { Outlet } from "react-router-dom";
import { Navbar } from "../components/navigation/Navbar";
import { Footer } from "../components/sections/Footer"; 

/**
 * Main layout component that wraps all pages
 * Provides consistent structure with navigation and footer
 */
export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-base-100">
      <Navbar />
      <main className="flex-grow">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
