import { useState, useEffect } from "react";
import { Dashboard } from "./Dashboard.tsrx";

type View = "home" | "dashboard";

interface OAuthSession {
  accessToken: string;
  discordId: string;
  username: string;
}

export component App() {
  const [count, setCount] = useState(0);
  const [view, setView] = useState<View>("home");
  const [session, setSession] = useState<OAuthSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");

    if (code && state) {
      handleOAuthCallback(code, state);
    }

    const stored = localStorage.getItem("wd_session");
    if (stored) {
      setSession(JSON.parse(stored));
    }
  }, []);

  const handleOAuthCallback = async (code: string, state: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/auth/discord/callback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, state }),
      });

      if (!response.ok) {
        throw new Error("OAuth callback failed");
      }

      const data = await response.json();
      const sess: OAuthSession = {
        accessToken: data.accessToken,
        discordId: data.discordId,
        username: data.username,
      };

      setSession(sess);
      localStorage.setItem("wd_session", JSON.stringify(sess));
      setView("dashboard");
      window.history.replaceState({}, document.title, "/");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Authentication failed",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setSession(null);
    localStorage.removeItem("wd_session");
    setView("home");
  };

  const increment = () => {
    setCount((value) => value + 1);
  };

  const decrement = () => {
    setCount((value) => value - 1);
  };

  <main class="app-shell">
    if (view === "home") {
      <section class="hero-card">
        <p class="eyebrow">"WinterDragon"</p>
        <h1>"TSRX React Bun boilerplate"</h1>
        <p class="lede">
          "A small starting point with local counter state and scoped component styles."
        </p>

        <div class="counter-wrap" aria-live="polite">
          <span class="counter-label">"Current count"</span>
          <output class="counter-value">{count}</output>
        </div>

        <div class="controls">
          <button type="button" onClick={decrement}>"--"</button>
          <button type="button" onClick={increment}>"++"</button>
        </div>

        if (!session) {
          <div class="oauth-section">
            <p class="oauth-prompt">"Want to see your WinterDragon data?"</p>
            <a href="/api/auth/discord/login" class="oauth-button">
              "Sign in with Discord"
            </a>
          </div>
        }

        if (error) {
          <div class="error-banner">{error}</div>
        }
      </section>
    } else if (view === "dashboard" && session) {
      <Dashboard
        session={session}
        onLogout={handleLogout}
        onError={setError}
      />
    }

    <style>
      :global(html) {
        color-scheme: dark;
      }

      :global(body) {
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at top, rgba(255, 255, 255, 0.16), transparent 45%),
          linear-gradient(135deg, #09111f 0%, #13213b 45%, #1d2f52 100%);
        color: #f7f4ee;
        font-family: "Georgia", "Times New Roman", serif;
      }

      :global(#root) {
        min-height: 100vh;
      }

      .app-shell {
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 2rem;
      }

      .hero-card {
        width: min(100%, 44rem);
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 28px;
        padding: clamp(1.5rem, 4vw, 3rem);
        background: rgba(7, 12, 22, 0.72);
        box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
        backdrop-filter: blur(18px);
      }

      .eyebrow {
        margin: 0 0 0.5rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: #f3c969;
        font-size: 0.78rem;
      }

      h1 {
        margin: 0;
        font-size: clamp(2.4rem, 6vw, 4.8rem);
        line-height: 0.95;
      }

      .lede {
        margin: 1rem 0 0;
        max-width: 34rem;
        color: rgba(247, 244, 238, 0.78);
        font-size: 1.05rem;
        line-height: 1.6;
      }

      .counter-wrap {
        margin-top: 1.75rem;
        display: grid;
        gap: 0.35rem;
        padding: 1rem 1.15rem;
        border-radius: 22px;
        background: rgba(255, 255, 255, 0.06);
      }

      .counter-label {
        color: rgba(247, 244, 238, 0.72);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
      }

      .counter-value {
        font-family: "SFMono-Regular", Consolas, monospace;
        font-size: clamp(3rem, 10vw, 5rem);
        font-weight: 700;
        line-height: 1;
      }

      .controls {
        display: flex;
        flex-wrap: wrap;
        gap: 0.85rem;
        margin-top: 1.5rem;
      }

      button {
        min-width: 5.25rem;
        border: 0;
        border-radius: 999px;
        padding: 0.95rem 1.2rem;
        background: linear-gradient(180deg, #f6c95e 0%, #d99c34 100%);
        color: #1b1b1b;
        font-family: inherit;
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        box-shadow: 0 10px 28px rgba(217, 156, 52, 0.28);
        cursor: pointer;
        transition:
          transform 160ms ease,
          box-shadow 160ms ease,
          filter 160ms ease;
      }

      button:hover {
        transform: translateY(-1px);
        filter: brightness(1.04);
        box-shadow: 0 14px 34px rgba(217, 156, 52, 0.35);
      }

      button:active {
        transform: translateY(1px);
      }

      button:focus-visible {
        outline: 3px solid rgba(255, 255, 255, 0.88);
        outline-offset: 3px;
      }

      .oauth-section {
        margin-top: 2rem;
        padding-top: 2rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
      }

      .oauth-prompt {
        margin: 0 0 1rem;
        color: rgba(247, 244, 238, 0.8);
        font-size: 0.95rem;
      }

      .oauth-button {
        display: inline-block;
        padding: 0.95rem 1.5rem;
        background: #5865f2;
        color: white;
        text-decoration: none;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.95rem;
        transition:
          background 160ms ease,
          transform 160ms ease;
      }

      .oauth-button:hover {
        background: #4752c4;
        transform: translateY(-1px);
      }

      .oauth-button:active {
        transform: translateY(1px);
      }

      .error-banner {
        margin-top: 1.5rem;
        padding: 1rem;
        background: rgba(220, 53, 69, 0.15);
        border: 1px solid rgba(220, 53, 69, 0.4);
        border-radius: 8px;
        color: #ff7b7b;
        font-size: 0.9rem;
      }
    </style>
  </main>
}