(() => {
  const toggle = document.getElementById('auto-refresh');
  if (!toggle) return;
  try { toggle.checked = sessionStorage.getItem('performance-auto-refresh') !== 'off'; } catch {}
  toggle.addEventListener('change', () => {
    try { sessionStorage.setItem('performance-auto-refresh', toggle.checked ? 'on' : 'off'); } catch {}
  });
  setInterval(() => {
    if (toggle.checked && !document.hidden && !document.activeElement?.closest('.performance-toolbar')) {
      window.location.reload();
    }
  }, 30000);
})();
