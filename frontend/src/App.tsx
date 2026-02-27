import { APITester } from "./APITester";
import Base from "./partials/Base";
import "./index.css";

import logo from "./logo.svg";
import reactLogo from "./react.svg";

function HTMXExample() {
  return (
    <div className="htmx-section">
      <h2>HTMX Examples</h2>
      <p>
        HTMX allows you to access modern browser features directly from HTML.
      </p>

      {/* Simple GET request example */}
      <button
        hx-get="/api/hello"
        hx-target="#response"
        hx-swap="innerHTML"
        className="btn btn-primary"
      >
        Click to fetch Hello
      </button>
      <div id="response" className="response-container"></div>

      {/* POST request with dynamic name */}
      <div className="mt-4">
        <input
          type="text"
          id="nameInput"
          placeholder="Enter a name"
          className="input"
        />
        <button
          hx-post="/api/hello"
          hx-target="#nameResponse"
          hx-include="[name='name']"
          hx-swap="innerHTML"
          className="btn btn-secondary mt-2"
        >
          Get Personalized Hello
        </button>
        <div id="nameResponse" className="response-container mt-2"></div>
      </div>

      {/* Polling example */}
      <div className="mt-4">
        <div
          hx-get="/api/hello"
          hx-trigger="every 5s"
          hx-target="this"
          hx-swap="innerHTML"
          className="polling-box"
        >
          <p>This will poll every 5 seconds...</p>
        </div>
      </div>
    </div>
  );
}

export function App() {
  return (
    <Base>
      <div className="app-content">
        <h1>Welcome to the Winter Dragon Bot Frontend!</h1>
        <p>This is a sample frontend application built with React and HTMX.</p>

        <HTMXExample />

        <APITester />
      </div>
    </Base>
  );
}

export default App;
