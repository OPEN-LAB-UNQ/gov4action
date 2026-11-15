# Formación en Gov4Action

Integración editorial del 13 de noviembre de 2026. Rutas públicas: /formacion, /formacion/autoevaluacion y /formacion/mapa. Fuentes canónicas: static/portal y static/formacion-assets. La portada conserva sus secciones y suma un acceso después de las cuatro herramientas.

Origen: mapa público y 18 preguntas de /home/economia, adaptados a la marca y contexto general de Gov4Action. No se copiaron bases, resultados, credenciales ni backend del curso. No existe dependencia de ese servicio en ejecución. El mapa conserva sus cinco ejes y relaciones. Actualizar contenidos requiere revisión editorial, controles y nueva publicación; no se afirma sincronización automática con el curso de origen.

Autoevaluación: percepción personal, no instrumento validado de competencia ni certificación. Respuestas numéricas 1–5 en sessionStorage con clave propia; sin envío de respuestas al servidor y sin agregación de grupos. Los promedios requieren tres respuestas por habilidad, las recomendaciones requieren 18/18. Borrar respuestas elimina el estado local de esta pestaña. El mapa guarda sólo preferencias de navegación en localStorage con clave propia. Recursos JS y JSON propios, compatibles con CSP sin scripts inline.

Controles: suite completa verificar_calidad.py, seis pruebas Node de puntuación, privacidad y referencias del mapa; pruebas Python de acceso anónimo y conservación de secciones. Verificar además navegador, mapa y recorrido completo tras publicar. Mantener respaldo y rollback del despliegue.
