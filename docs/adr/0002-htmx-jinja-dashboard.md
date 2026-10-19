# The web dashboard is htmx 4 and Jinja templates served by the FastAPI service

The dashboard is rendered on the server: the FastAPI service that holds the HTTP API also serves the pages, as Jinja templates, and htmx 4 swaps in the HTML fragments its routes return. There is no separate frontend app, no Node or Bun toolchain, no build step and no frontend container. The dashboard's pages (Discord sign-in, a profile, the data the bot stores, a deletion request, per-guild cog settings) are forms and lists over data the Python code already models, so keeping them in Python keeps the domain logic, validation and types in one place.

## Considered Options

- **A React (or TSRX/Ripple) single-page app on Bun, as on `main`.** Rejected: a second language, toolchain, dependency tree and container for a handful of CRUD pages, and the browser has to hold a bearer token (`main` kept it in localStorage). TSRX and Ripple are still alpha.
- **SvelteKit or React + Vite with TypeScript types generated from the OpenAPI schema.** Rejected for now: the right choice if the dashboard grows heavy client-side editors, but until then it costs the same second toolchain for no gain. Revisit if a page needs more client state than htmx plus a little JavaScript can hold.
- **A Python UI framework (NiceGUI, Reflex, FastHTML).** Rejected: NiceGUI keeps each tab's state on the server over a websocket, which suits admin panels, not a public dashboard; Reflex runs its own backend beside FastAPI; FastHTML is built on Starlette and its star-import, loosely typed style conflicts with the repo's code style.
- **Datastar instead of htmx.** Rejected for now: the same server-rendered model with server-sent updates built in, but a much smaller community. Worth revisiting for live views such as bot statistics.

## Consequences

- Sign-in is a Discord OAuth2 redirect whose callback sets an HttpOnly session cookie; the browser never sees a token, and same-origin pages need no CORS. Forms that change state need CSRF protection.
- A dashboard route returns a whole page on a normal request and only the changed fragment on an htmx request (the `HX-Request` header); the JSON API routes stay for other clients.
- Templates are not type-checked: pass them pydantic models or entities, not loose dicts, and keep logic out of them.
- htmx 4 changed defaults from 2.x (fetch-based requests, explicit attribute inheritance, error responses swap in by default); most tutorials still describe 2.x, so follow the htmx 4 docs.
- Behaviour htmx can't express (charts, drag and drop) is a small script on the page that needs it, not a framework.
