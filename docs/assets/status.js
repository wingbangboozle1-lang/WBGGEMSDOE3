/* Mark cached observations stale in the viewer, even if deployments stop. */
(() => {
  document.querySelectorAll('[data-freshness]').forEach((node) => {
    const stamp = node.dataset.checked || '';
    const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(stamp);
    const checked = Date.parse(stamp);
    const age = Date.now() - checked;
    // A date-only observation has no known time-of-day. Allow a 36-hour
    // grace window rather than treating midnight as the actual fetch time.
    const maxAge = (dateOnly ? 36 : 12) * 3600000;
    if (!Number.isFinite(checked) || age < -300000 || age > maxAge || node.dataset.error === 'yes') {
      node.textContent = `STALE · ${node.textContent}`;
    }
  });
})();
