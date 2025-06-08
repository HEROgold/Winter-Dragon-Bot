
export function StatsSection() {
  return <div className="stats shadow mt-16 mx-auto flex flex-col md:flex-row">
    <div className="stat">
      <div className="stat-figure text-primary">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="inline-block w-8 h-8 stroke-current"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
      </div>
      <div className="stat-title">Server Count</div>
      <div className="stat-value">2.1K</div>
      <div className="stat-desc">Growing community</div>
    </div>

    <div className="stat">
      <div className="stat-figure text-secondary">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="inline-block w-8 h-8 stroke-current"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
      </div>
      <div className="stat-title">Commands Used</div>
      <div className="stat-value">24M+</div>
      <div className="stat-desc">↗︎ 4,200 (22%)</div>
    </div>

    <div className="stat">
      <div className="stat-figure text-success">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="inline-block w-8 h-8 stroke-current"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path></svg>
      </div>
      <div className="stat-title">Uptime</div>
      <div className="stat-value">99.9%</div>
      <div className="stat-desc">Reliable & Fast</div>
    </div>
  </div>;
}
