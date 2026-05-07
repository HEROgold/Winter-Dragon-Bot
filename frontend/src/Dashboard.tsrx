import { useState, useEffect } from "react";

interface OAuthSession {
  accessToken: string;
  discordId: string;
  username: string;
}

interface UserData {
  id: string;
  username: string;
  joinedAt: string;
  recordCount: number;
}

interface DashboardProps {
  session: OAuthSession;
  onLogout: () => void;
  onError: (error: string) => void;
}

export component Dashboard({
  session,
  onLogout,
  onError,
}: DashboardProps) {
  const [userData, setUserData] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/user/${session.discordId}`, {
        headers: {
          Authorization: `Bearer ${session.accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch user data");
      }

      const data = await response.json();
      setUserData(data);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteData = async () => {
    setDeleting(true);
    try {
      const response = await fetch(`/api/user/${session.discordId}/data`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${session.accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ reason: "User requested deletion" }),
      });

      if (!response.ok) {
        throw new Error("Failed to delete data");
      }

      setShowDeleteModal(false);
      onLogout();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to delete data");
    } finally {
      setDeleting(false);
    }
  };

  <div class="dashboard-container">
    <header class="dashboard-header">
      <div class="header-left">
        <p class="eyebrow">"WinterDragon Dashboard"</p>
        <h1>"Welcome, "{session.username}</h1>
      </div>
      <button type="button" onClick={onLogout} class="logout-btn">
        "Logout"
      </button>
    </header>

    if (loading) {
      <div class="loading-state">
        <p>"Loading your data..."</p>
      </div>
    } else if (userData) {
      <section class="user-profile">
        <h2>"Your Profile"</h2>
        <div class="profile-grid">
          <div class="profile-item">
            <span class="label">"Discord ID"</span>
            <code>{userData.id}</code>
          </div>
          <div class="profile-item">
            <span class="label">"Joined"</span>
            <span>{userData.joinedAt}</span>
          </div>
          <div class="profile-item">
            <span class="label">"Total Records"</span>
            <span>{userData.recordCount}</span>
          </div>
        </div>
      </section>

      <section class="data-actions">
        <h2>"Data Management"</h2>
        <p class="description">
          "Permanently delete all your WinterDragon data. This action cannot be undone."
        </p>
        <button
          type="button"
          onClick={() => setShowDeleteModal(true)}
          class="delete-btn"
        >
          "Delete My Data"
        </button>
      </section>

      if (showDeleteModal) {
        <div class="modal-overlay" onClick={() => setShowDeleteModal(false)}>
          <div class="modal" onClick={(e) => e.stopPropagation()}>
            <h2>"Are you sure?"</h2>
            <p>
              "This will permanently delete all your WinterDragon data and cannot be undone. We will keep an audit log of this deletion for compliance."
            </p>
            <div class="modal-actions">
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                class="cancel-btn"
              >
                "Cancel"
              </button>
              <button
                type="button"
                onClick={handleDeleteData}
                disabled={deleting}
                class="confirm-delete-btn"
              >
                {deleting ? "Deleting..." : "Yes, Delete Everything"}
              </button>
            </div>
          </div>
        </div>
      }
    }

    <style>
      .dashboard-container {
        width: 100%;
        max-width: 48rem;
        padding: 2rem;
      }

      .dashboard-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 2rem;
        gap: 1.5rem;
      }

      .header-left h1 {
        margin: 0.5rem 0 0;
        font-size: 2rem;
      }

      .logout-btn {
        padding: 0.6rem 1.2rem;
        background: rgba(255, 255, 255, 0.1);
        color: #f7f4ee;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 160ms ease;
      }

      .logout-btn:hover {
        background: rgba(255, 255, 255, 0.15);
        border-color: rgba(255, 255, 255, 0.3);
      }

      .loading-state {
        padding: 2rem;
        text-align: center;
        color: rgba(247, 244, 238, 0.6);
      }

      .user-profile,
      .data-actions {
        margin-bottom: 2.5rem;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.03);
      }

      .user-profile h2,
      .data-actions h2 {
        margin: 0 0 1.5rem;
        font-size: 1.25rem;
      }

      .profile-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
        gap: 1rem;
      }

      .profile-item {
        padding: 1rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
      }

      .profile-item .label {
        display: block;
        margin-bottom: 0.5rem;
        color: rgba(247, 244, 238, 0.6);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
      }

      .profile-item code {
        font-family: "SFMono-Regular", Consolas, monospace;
        font-size: 0.9rem;
        word-break: break-all;
      }

      .description {
        color: rgba(247, 244, 238, 0.7);
        margin-bottom: 1.5rem;
      }

      .delete-btn {
        padding: 0.8rem 1.5rem;
        background: rgba(220, 53, 69, 0.2);
        color: #ff7b7b;
        border: 1px solid rgba(220, 53, 69, 0.4);
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        transition: all 160ms ease;
      }

      .delete-btn:hover {
        background: rgba(220, 53, 69, 0.3);
        border-color: rgba(220, 53, 69, 0.5);
      }

      .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: grid;
        place-items: center;
        z-index: 1000;
      }

      .modal {
        background: rgba(7, 12, 22, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 16px;
        padding: 2rem;
        max-width: 28rem;
        width: 90%;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
      }

      .modal h2 {
        margin: 0 0 1rem;
        font-size: 1.5rem;
      }

      .modal p {
        margin: 0 0 1.5rem;
        color: rgba(247, 244, 238, 0.8);
        line-height: 1.5;
      }

      .modal-actions {
        display: flex;
        gap: 1rem;
      }

      .cancel-btn,
      .confirm-delete-btn {
        flex: 1;
        padding: 0.75rem;
        border: 0;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        transition: all 160ms ease;
      }

      .cancel-btn {
        background: rgba(255, 255, 255, 0.1);
        color: #f7f4ee;
      }

      .cancel-btn:hover {
        background: rgba(255, 255, 255, 0.15);
      }

      .confirm-delete-btn {
        background: rgba(220, 53, 69, 0.3);
        color: #ff7b7b;
        border: 1px solid rgba(220, 53, 69, 0.4);
      }

      .confirm-delete-btn:hover:not(:disabled) {
        background: rgba(220, 53, 69, 0.4);
      }

      .confirm-delete-btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

      .eyebrow {
        margin: 0;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: #f3c969;
        font-size: 0.78rem;
      }
    </style>
  </div>
}
