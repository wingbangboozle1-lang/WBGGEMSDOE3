(() => {
  "use strict";

  const filter = document.getElementById("site-filter");
  const count = document.getElementById("filter-count");
  const rows = [...document.querySelectorAll("#priority-table tbody tr")];
  if (filter && count) {
    const applyFilter = () => {
      const query = filter.value.trim().toLowerCase();
      let shown = 0;
      rows.forEach((row) => {
        const match = row.textContent.toLowerCase().includes(query);
        row.hidden = !match;
        if (match) shown += 1;
      });
      count.textContent = `${shown} ${shown === 1 ? "site" : "sites"}`;
    };
    filter.addEventListener("input", applyFilter);
    applyFilter();
  }

  const feedUrl = document.body.dataset.feed;
  if (!feedUrl) return;
  const update = (selector, text) => {
    document.querySelectorAll(selector).forEach((element) => {
      element.textContent = text;
    });
  };
  fetch(feedUrl, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error("feed unavailable");
      return response.json();
    })
    .then((data) => {
      const board = data.leaderboard || {};
      const value =
        typeof board.top_value === "string" &&
        /^(?:0(?:\.\d+)?|1(?:\.0+)?)$/.test(board.top_value)
          ? board.top_value
          : "Unavailable";
      update("[data-board-value]", value);
      const observed =
        typeof board.observed_utc === "string" ? board.observed_utc : "unknown";
      let state = "Public observation unavailable";
      if (board.status === "current") state = "Public leaderboard checked";
      else if (value !== "Unavailable")
        state = "Stale / last public observation";
      update(
        "[data-board-status]",
        `${state}: ${observed}. Not a submission receipt.`,
      );
      const repos = Array.isArray(data.repositories) ? data.repositories : [];
      if (!repos.length) {
        update("[data-repo-status]", "Repository freshness unavailable");
        return;
      }
      const changed = repos.filter(
        (item) => item.status === "changed_since_audit",
      ).length;
      const unavailable = repos.filter(
        (item) => item.status === "unavailable",
      ).length;
      const checked =
        typeof data.checked_utc === "string"
          ? data.checked_utc
          : "unknown time";
      update(
        "[data-repo-status]",
        `${changed} changed since audit · ${unavailable} unavailable · checked ${checked}`,
      );
    })
    .catch(() => {
      update(
        "[data-board-status]",
        "Feed unavailable. Displayed number is a dated snapshot, not a submission receipt.",
      );
      update("[data-repo-status]", "Repository freshness unavailable");
    });
})();
