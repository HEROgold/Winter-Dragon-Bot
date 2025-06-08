
export function CustomCommandsCard() {
  return <div className="card bg-base-200 shadow-xl hover:shadow-2xl transition-all">
    <div className="card-body">
      <div className="badge badge-accent mb-2">Customizable</div>
      <h3 className="card-title">Custom Commands</h3>
      <p>Create your own server-specific commands with custom responses, embed messages, and automatic triggers.</p>
      <div className="card-actions justify-end mt-4">
        <a href="/features/custom-commands" className="btn btn-sm btn-primary">Learn More</a>
      </div>
    </div>
  </div>;
}
