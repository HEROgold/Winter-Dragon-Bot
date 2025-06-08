export function BreadCrumbs() {
  return <div className="breadcrumbs text-sm px-4 py-2 bg-base-200">
    <ul>
      <li className="font-semibold">
        <a>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            className="h-4 w-4 stroke-current">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
          </svg>
          Home
        </a>
      </li>
    </ul>
  </div>;
}
