export function Navbar() {
  return (
    <nav className="navbar bg-base-200 shadow-lg">
      <div className="container mx-auto px-4">
        <div className="navbar-start">
          <a href="/" className="btn btn-ghost text-xl font-bold">
            Winter Dragon Bot
          </a>
        </div>
        <div className="navbar-center hidden lg:flex">
          <ul className="menu menu-horizontal p-0">
            <li><a href="#features">Features</a></li>
            <li><a href="/commands">Commands</a></li>
            <li><a href="/dashboard">Dashboard</a></li>
            <li><a href="/premium">Premium</a></li>
          </ul>
        </div>
        <div className="navbar-end">
          <a href="https://discord.gg/winterdragon" className="btn btn-primary">Support Server</a>
        </div>
      </div>
    </nav>
  );
}
