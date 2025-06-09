import { Link, type LinkProps } from "react-router-dom";
import { BreadCrumbs } from "./BreadCrumbs";
import { useRef } from "react";

export function Navigation() {
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
            <li><Link to="/dashboard">Dashboard</Link></li>
            <li><Link to="/premium">Premium</Link></li>
          </ul>
        </div>
      </div>
    </nav>
  );
}

interface NavMenuChildProps {
  links: React.ReactNode[];
  onClick?: () => void;
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