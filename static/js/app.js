// Persist the theme in localStorage so the next page load doesn't flash.
document.addEventListener('submit', function (e) {
  var form = e.target;
  if (form && form.classList && form.classList.contains('theme-toggle-form')) {
    try {
      var theme = form.querySelector('input[name="theme"]').value;
      window.localStorage.setItem('pda-theme-preference', theme);
    } catch (err) {}
  }
});
