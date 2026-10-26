/* Mark a cached public observation stale in the viewer, even if deployments stop. */
(() => {
  const node = document.getElementById('feed-freshness');
  if (!node) return;
  const checked = Date.parse(node.dataset.checked || '');
  const age = Date.now() - checked;
  if (!Number.isFinite(checked) || age < -300000 || age > 12 * 3600000 || node.dataset.error === 'yes') {
    node.textContent = `STALE · ${node.textContent}`;
  }
})();
