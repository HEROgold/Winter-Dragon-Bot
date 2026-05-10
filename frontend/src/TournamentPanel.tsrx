import { useState } from "react";

interface TournamentPanelProps {
  onError: (error: string) => void;
}

export component TournamentPanel({ onError }: TournamentPanelProps) {
  const [guildIdInput, setGuildIdInput] = useState("");
  const [tournament, setTournament] = useState<TournamentSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTournament = async () => {
    const guildId = Number(guildIdInput);

    if (!Number.isFinite(guildId) || guildId <= 0) {
      setError("Enter a valid guild ID to load a tournament.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/tournaments/${guildId}`);

      if (!response.ok) {
        throw new Error("Failed to fetch tournament data");
      }

      const data = (await response.json()) as TournamentSnapshot;
      setTournament(data);
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Failed to load tournament data";
      setError(message);
      onError(message);
    } finally {
      setLoading(false);
    }
  };

  <section class="tournament-panel">
    <div class="section-header">
      <div>
        <h2>"Tournament Control"</h2>
        <p class="description">
          "Load a guild tournament snapshot to review its current phase and team roster."
        </p>
      </div>
      <span class="section-badge">"Discord-linked"</span>
    </div>

    <div class="tournament-form">
      <label class="tournament-label" for="guild-id-input">"Guild ID"</label>
      <div class="tournament-input-row">
        <input
          id="guild-id-input"
          type="number"
          min="1"
          placeholder="123456789012345678"
          value={guildIdInput}
          onInput={(event: any) => setGuildIdInput(event.target.value)}
        />
        <button type="button" onClick={loadTournament} class="load-btn" disabled={loading}>
          {loading ? "Loading..." : "Load Tournament"}
        </button>
      </div>

      <p class="inline-error">{error ?? ""}</p>
    </div>

    <div class="tournament-summary">
      <div class="summary-card">
        <span class="label">"Guild"</span>
        <code>{tournament ? tournament.guildId : "—"}</code>
      </div>
      <div class="summary-card">
        <span class="label">"Phase"</span>
        <span>{tournament ? tournament.status.split("_").join(" ") : "No tournament loaded"}</span>
      </div>
      <div class="summary-card">
        <span class="label">"Teams"</span>
        <span>{tournament ? tournament.teams.length : 0}</span>
      </div>
    </div>

    <div class="tournament-teams">
      <p class="muted">
        {tournament
          ? tournament.teams
              .map((team, index) => `Team ${index + 1}: ${team.players.map((player) => `${player.name} (${player.intendedPick})`).join(", ") || "No players yet"}`)
              .join(" | ")
          : "No tournament loaded"}
      </p>
    </div>

    <style>
      .tournament-panel {
        margin-bottom: 2.5rem;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        background:
          linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
      }

      .section-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 1rem;
      }

      .section-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        background: rgba(88, 101, 242, 0.18);
        color: #cdd3ff;
        font-size: 0.75rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .tournament-form {
        margin-bottom: 1.25rem;
      }

      .tournament-label {
        display: block;
        margin-bottom: 0.6rem;
        color: rgba(247, 244, 238, 0.7);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
      }

      .tournament-input-row {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
      }

      .tournament-input-row input {
        flex: 1 1 16rem;
        min-width: 0;
        padding: 0.9rem 1rem;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.14);
        background: rgba(0, 0, 0, 0.18);
        color: #f7f4ee;
        font: inherit;
      }

      .tournament-input-row input:focus {
        outline: 2px solid rgba(88, 101, 242, 0.5);
        outline-offset: 2px;
      }

      .load-btn {
        padding: 0.9rem 1.3rem;
        background: linear-gradient(180deg, #7a88ff 0%, #5865f2 100%);
        color: white;
        border: 0;
        border-radius: 10px;
        font-weight: 700;
        cursor: pointer;
      }

      .load-btn:disabled {
        opacity: 0.7;
        cursor: progress;
      }

      .inline-error {
        margin: 0.85rem 0 0;
        color: #ff7b7b;
      }

      .tournament-summary {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
        gap: 0.8rem;
        margin-bottom: 1rem;
      }

      .summary-card {
        padding: 0.95rem;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.05);
      }

      .tournament-teams {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
        gap: 1rem;
      }

      .muted {
        color: rgba(247, 244, 238, 0.68);
      }
    </style>
  </section>
}
