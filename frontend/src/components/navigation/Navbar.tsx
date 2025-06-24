import { Link } from "react-router-dom";
import { BreadCrumbs } from "./BreadCrumbs";
import { useRef } from "react";
import { router } from "@/routes";
import { useAuth, type User } from "@/contexts/AuthContext";

export function Navigation() {
  const { isAuthenticated, login, logout, user } = useAuth();
  
  // https://reactrouter.com/start/framework/pending-ui
  // Automatically generate this navigation based on the routes defined in the router.
  return (
    <nav className="navbar bg-base-100 shadow-lg">
      <div className="container mx-auto px-4">
        <div className="navbar-center hidden lg:flex">
          <ul className="menu menu-horizontal p-0">
            <NavMenu parent="Features" links={[
              <Link to="/features/moderation">Moderation</Link>,
              <Link to="/features/welcome">Welcome</Link>,
              <Link to="/features/logging">Logging</Link>,
            ]} />
            {isAuthenticated && <li><Link to="/dashboard">Dashboard</Link></li>}
            <li><Link to="/premium">Premium</Link></li>
          </ul>
        </div>
        {navbarEnd(isAuthenticated, user, logout, login)}
      </div>
    </nav>
  );
}

interface NavMenuChildProps {
  links: React.ReactNode[];
  onClick?: () => void;
}

function navbarEnd(isAuthenticated: boolean, user: User, logout: () => void, login: () => void) {
  return <div className="navbar-end">
    {isAuthenticated ? (
      <div className="dropdown dropdown-end">
        <div tabIndex={0} role="button" className="btn btn-ghost btn-circle avatar">
          <div className="w-10 rounded-full">
            {user?.avatar ? (
              <img
                src={`https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`}
                alt={`${user.username}'s avatar`} />
            ) : (
              <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center text-primary-content">
                {user?.username?.charAt(0).toUpperCase()}
              </div>
            )}
          </div>
        </div>
        <ul tabIndex={0} className="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
          <li className="menu-title">
            <span>{user?.username}</span>
          </li>
          <li><Link to="/dashboard">Dashboard</Link></li>
          <li><a onClick={logout}>Logout</a></li>
        </ul>
      </div>
    ) : (
      DiscordLoginButton(login)
    )}
  </div>;
}

function DiscordLoginButton(login: () => void) {
  return <button className="btn btn-primary" onClick={login}>
    Login with Discord
  </button>;
}

function NavMenu({parent, links}: {parent: string, links: React.ReactNode[]}) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  
  const closeMenu = () => {
    if (detailsRef.current) {
      detailsRef.current.open = false;
    }
  };
  
  // Add route to show the parent route.
  const parentPath = `/${parent.toLowerCase()}`;
  const allLink = <Link to={parentPath}>All {parent}</Link>;
  const allLinks = [allLink, ...links];

  return (
    <li>
      <details ref={detailsRef}>
        <summary>{parent}</summary>
        <ul onClick={closeMenu}>
          <NavMenuChild links={allLinks} />
        </ul>
      </details>
    </li>
  );
}

function NavMenuChild({links, onClick: onLinkClick}: NavMenuChildProps) {
  return links.map((link, index) => (
      <li key={index}>
        {link}
      </li>
    ));
}

function NavHome() {
  return <div className="navbar-start">
    <Link to="/" className="btn btn-ghost text-xl font-bold">
      Winter Dragon Bot
    </Link>
  </div>;
}

export function Navbar() {
  return (
    <>
      <NavHome />
      <Navigation />
      <BreadCrumbs />
    </>
  )
}