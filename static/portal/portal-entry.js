// Los enlaces a informes y pantallas conservan su ruta dentro de Gov4Action.
if (window.location.hash.startsWith('#/')) {
  window.location.replace('/index.html' + window.location.search + window.location.hash);
}

// Cerrar el menú al navegar, sin cambiar el comportamiento del enlace.
const mobileMenu = document.querySelector('.mobile-menu');
if (mobileMenu) {
  mobileMenu.addEventListener('click', (event) => {
    if (event.target.closest('a')) mobileMenu.open = false;
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && mobileMenu.open) {
      mobileMenu.open = false;
      mobileMenu.querySelector('summary').focus();
    }
  });
  document.addEventListener('click', (event) => {
    if (mobileMenu.open && !mobileMenu.contains(event.target)) mobileMenu.open = false;
  });
}
