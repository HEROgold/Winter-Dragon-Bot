// Ticks the Incremental page's amounts and countdowns forward from the server's snapshot.
// Time is measured with performance.now() from the moment a snapshot appears, so the browser's clock never matters,
// and each re-sync replaces the snapshot, so drift cannot build up.
(() => {
  const format = (value) => value.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const duration = (seconds) => {
    const total = Math.ceil(seconds);
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const rest = total % 60;
    if (hours) return `${hours}h ${minutes}m ${rest}s`;
    return minutes ? `${minutes}m ${rest}s` : `${rest}s`;
  };
  const stamp = () => {
    const now = performance.now();
    document.querySelectorAll("[data-tick], [data-countdown]").forEach((element) => {
      if (element.dataset.since === undefined) element.dataset.since = String(now);
    });
  };
  const tick = () => {
    const now = performance.now();
    let ready = false;
    document.querySelectorAll("[data-tick]").forEach((element) => {
      const elapsed = (now - Number(element.dataset.since)) / 1000;
      element.textContent = format(Number(element.dataset.amount) + Number(element.dataset.rate) * elapsed);
    });
    document.querySelectorAll("[data-countdown]").forEach((element) => {
      const left = Number(element.dataset.countdown) - (now - Number(element.dataset.since)) / 1000;
      element.textContent = left > 0 ? duration(left) : "now";
      if (left <= 0) ready = true;
    });
    const game = document.getElementById("incremental");
    if (ready && game && !game.dataset.resyncing) {
      game.dataset.resyncing = "1";
      window.htmx?.trigger(game, "resync");
    }
  };
  document.addEventListener("htmx:afterSettle", stamp);
  stamp();
  setInterval(tick, 250);
})();
