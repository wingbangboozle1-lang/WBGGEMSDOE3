/* Mark cached observations stale in the viewer, even if deployments stop. */
(() => {
  document.querySelectorAll('[data-freshness]').forEach((node) => {
    const checked = Date.parse(node.dataset.checked || '');
    const age = Date.now() - checked;
    if (!Number.isFinite(checked) || age < -300000 || age > 12 * 3600000 || node.dataset.error === 'yes') {
      node.textContent = `STALE · ${node.textContent}`;
    }
  });
})();
