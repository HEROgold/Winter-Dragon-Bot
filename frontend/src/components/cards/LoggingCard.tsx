
export function LoggingCard() {
  return <div className="card bg-base-200 shadow-xl hover:shadow-2xl transition-all">
    <div className="card-body">
      <div className="badge badge-warning mb-2">Admin</div>
      <h3 className="card-title">Advanced Logging</h3>
      <p>Comprehensive logging system for all server events including message edits, deletions, member joins/leaves, and moderation actions.</p>
      <div className="card-actions justify-end mt-4">
        <a href="/features/logging" className="btn btn-sm btn-primary">Learn More</a>
      </div>
    </div>
  </div>;
}
