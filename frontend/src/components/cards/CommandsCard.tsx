
export function CommandsCard() {
  return <div className="card bg-base-200 shadow-xl hover:shadow-2xl transition-all">
    <div className="card-body">
      <div className="badge badge-success mb-2">Entertainment</div>
      <h3 className="card-title">Fun & Games</h3>
      <p>Variety of fun commands, games, memes, and utilities to keep your server members engaged and entertained.</p>
      <div className="card-actions justify-end mt-4">
        <a href="/features/fun" className="btn btn-sm btn-primary">Learn More</a>
      </div>
    </div>
  </div>;
}
