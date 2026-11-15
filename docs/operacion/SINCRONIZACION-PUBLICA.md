# Estado público de Gov4Action

/api/publico/estado publica sólo conteos agregados, versiones, fichas públicas y resultados de pruebas. Caché: 300 segundos; errores: reintento en 60 segundos. Las copias en memoria conservan la fecha original. Tras reiniciar, sin fuente disponible, se muestra sin datos (uso puede recuperar la foto histórica de public-evidence.json).

La ejecución completa de venv/bin/python scripts/verificar_calidad.py genera static/public-evidence.json sólo después de aprobar Python, campañas y JavaScript. --excel no publica evidencia. El candidato no debe cambiar durante los controles. La huella incluye código, interfaz, portal, controles y documentación. No incluye bases, secretos ni la evidencia generada. Desplegar el candidato exacto y su JSON; reiniciar el servicio para cargar código nuevo. Si difiere la huella, /estado no acredita vigencia.

static/portal es la fuente de la portada y páginas públicas. Al publicar, copiar sus páginas estáticas existentes a /home/gov4action; /estado, /prototipos e /investigacion se sirven desde la aplicación. Incluir esas fuentes en los controles y el respaldo. No editar sólo el espejo de nginx.

Las novedades editoriales, documentos publicados y resultados históricos requieren revisión humana y fecha propia. No convertir actividad en impacto ni publicar relatos privados. El documento v9.7 conserva su corte; la nueva investigación no es un capítulo aceptado ni publicado.
