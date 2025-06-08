
export function WelcomeSystemCard() {
  return <div className="card bg-base-200 shadow-xl hover:shadow-2xl transition-all">
    <div className="card-body">
      <div className="badge badge-info mb-2">Community</div>
      <h3 className="card-title">Welcome System</h3>
      <p>Customize welcome messages with embed templates, role assignments, and welcome channels to greet new members.</p>
      <div className="card-actions justify-end mt-4">
        <a href="/features/welcome" className="btn btn-sm btn-primary">Learn More</a>
      </div>
    </div>
  </div>;
}
