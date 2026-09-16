const form = document.getElementById('search-form');
const button = document.getElementById('search-button');
const statusText = document.getElementById('search-status');
form.addEventListener('submit', () => {
  button.disabled = true;
  button.textContent = 'Checking prices…';
  statusText.textContent = 'Reading current listings. This usually takes a few seconds.';
});
window.addEventListener('pageshow', () => {
  button.disabled = false;
  button.textContent = 'Find car prices ↗';
  statusText.textContent = 'Prices are fetched on search and reused for up to 5 minutes.';
});
