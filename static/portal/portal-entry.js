// Los enlaces a informes y pantallas conservan su ruta dentro de Gov4Action.
if (window.location.hash.startsWith('#/')) {
  window.location.replace('/index.html' + window.location.search + window.location.hash);
}
