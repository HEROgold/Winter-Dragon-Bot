
import "./navbar.css"
import { NavbarLinks } from "@/hooks/routes";
import StyleSelector from "./style_selector";

export default function Navbar() {
  return (
    <>
      <StyleSelector />
      <nav className="navbar">
        <NavbarLinks />
      </nav>
    </>
  );
}
