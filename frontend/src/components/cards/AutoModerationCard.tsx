
export function AutoModerationCard() {
  return <div className="card bg-base-200 shadow-xl hover:shadow-2xl transition-all">
    <div className="card-body">
      <div className="badge badge-secondary mb-2">Smart</div>
      <h3 className="card-title">Auto-Moderation</h3>
      <p>Configurable auto-moderation features to filter spam, inappropriate content, and unwanted links with customizable rule sets.</p>
      <div className="card-actions justify-end mt-4">
        <a href="/features/auto-mod" className="btn btn-sm btn-primary">Learn More</a>
      </div>
    </div>
  </div>;
}
