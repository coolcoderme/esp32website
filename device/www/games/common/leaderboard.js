// leaderboard.js -- shared arcade leaderboard helper.
// Every game submits scores with 3-letter initials, arcade style.

const LB = {
  async get(game) {
    try {
      const r = await fetch("/api/leaderboard/" + game);
      return r.ok ? await r.json() : [];
    } catch (e) { return []; }
  },

  async submit(game, name, score) {
    name = (name || "AAA").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 3) || "AAA";
    try {
      const r = await fetch("/api/leaderboard/" + game, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name, score: Math.round(score) })
      });
      return r.ok ? await r.json() : null;
    } catch (e) { return null; }
  },

  askInitials() {
    let n = prompt("New score! Enter your 3-letter initials:", "AAA");
    if (n === null) return null;
    n = n.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 3);
    return n || "AAA";
  },

  render(el, list) {
    if (!el) return;
    if (!list || !list.length) {
      el.innerHTML = '<p class="muted">No scores yet &mdash; be the first!</p>';
      return;
    }
    el.innerHTML =
      "<table><thead><tr><th>#</th><th>Player</th><th class='score'>Score</th></tr></thead><tbody>" +
      list.map((e, i) =>
        `<tr><td class="rank">${i + 1}</td><td class="mono">${e.name}</td><td class="score">${e.score}</td></tr>`
      ).join("") +
      "</tbody></table>";
  },

  // Convenience: submit a score (prompting for initials) then re-render.
  // Guarded so a single game-over can only submit once (some games used to
  // call this multiple times in the same run).
  _submitted: {},

  async recordAndRefresh(game, score, el) {
    const key = game + ":" + score;
    if (this._submitted[key]) return;
    this._submitted[key] = true;

    const name = this.askInitials();
    if (name === null) {
      delete this._submitted[key];
      this.render(el, await this.get(game));
      return;
    }
    const res = await this.submit(game, name, score);
    this.render(el, (res && res.board) ? res.board : await this.get(game));
    return res;
  },

  resetSession(game) {
    Object.keys(this._submitted).forEach(k => {
      if (k.startsWith(game + ":")) delete this._submitted[k];
    });
  }
};

// Shared page header for games.
function gameHeader(title) {
  return `<header class="site">
     <div class="brand"><div class="logo">E32</div>
       <div><h1>${title}</h1><p><a class="back" href="/#games">&larr; Back to arcade</a></p></div></div>
   </header>`;
}
