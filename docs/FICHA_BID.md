# Ficha para «Código para el Desarrollo» (BID)

Actualizada el 26/11/2026, con los mismos campos que la ficha publicada del
[Asistente IA para Consultas Académicas](https://knowledge.iadb.org/es/conocimiento-abierto/codigo-para-el-desarrollo/solucion-de-codigo-abierto/asistente-ia-para-consultas-academicas).

## Título

Gov4Action: Multilente, Incubadora, Conexiones y Monitoreo

(Anteriormente «Gobernanza Multilente e Incubadora». El repositorio anterior, `gobernanza-multilente`, queda como antecedente de la versión 0.10.66.)

## Datos

| Campo | Valor |
|---|---|
| Idioma | Python |
| Tipo de herramienta | Aplicación web |
| Licencia | The MIT License |
| Versión | 0.10.89 |
| Responsable | OPEN LAB · Universidad Nacional de Quilmes |
| Repositorio | https://github.com/OPEN-LAB-UNQ/gov4action |
| Sitio | https://gov4action.com |

## ¿Qué es?

Gov4Action es una aplicación web desarrollada en Python (FastAPI y PostgreSQL) por OPEN LAB, proyecto de
extensión de la Universidad Nacional de Quilmes. Reúne cuatro herramientas abiertas para incorporar
inteligencia artificial en el trabajo público sin delegar el juicio: Multilente (revisar), Incubadora
(formular), Conexiones (articular) y Monitoreo (aprender). Su criterio común es que la IA propone, las
reglas comprueban y la persona decide: ninguna da veredictos, hacen preguntas con su evidencia.

**Multilente** hace una segunda lectura de informes con datos agregados —presupuestos y su ejecución,
estados contables, tableros de indicadores y metas— antes de decidir con ellos. Lee planillas Excel,
CSV y PDF y aplica a cada cuadro los mismos controles reproducibles, organizados en seis lentes
analíticas (ajedrecista, matemático, cronista, orquesta, radiólogo y rizoma) y una capa conciliadora que
revisa si una señal tiene una explicación técnica antes de escalarla. Devuelve preguntas con su evidencia,
en lenguaje llano, y cada informe empieza por lo que no pudo leer o revisar. La revisión rápida, que es la
que se usa por defecto, no usa IA: es una base de reglas que hace las cuentas en segundos, sin costo por
uso, con el mismo resultado cada vez y sin que los datos salgan del servidor. La revisión profunda suma una
IA opcional que propone cómo leer cada cuadro y lee las señales, pero no calcula ni decide.

**Incubadora** es el espacio formativo: cada persona formula un proyecto de aplicación responsable de IA
para un problema de su área, acompañada por una tutora de IA que hace preguntas en lugar de dar respuestas
cerradas. El proyecto se trabaja con diez criterios, con citas literales de lo que aportó la persona que un
segundo modelo comprueba antes de mostrarlas, y recibe una devolución escrita por el equipo docente.

**Conexiones** pone los proyectos de la Incubadora uno al lado del otro, dentro de cada grupo de cursada,
para ver qué temas, datos o riesgos podrían compartir. Busca temas de una lista fija, sin IA, y propone
hipótesis para que los equipos conversen: no fusiona proyectos ni decide por nadie. Está operativa.

**Monitoreo** registra, proyecto por proyecto, avances, riesgos, decisiones humanas, indicadores y
aprendizajes de una prueba. Está en producción siguiendo el uso de Multilente y, con los prototipos de la
formación, funciona en modo prueba con datos ficticios. Es aprendizaje, no evaluación: no mide a las personas.

**Uso hasta ahora.** Se usó en tres cursadas de agentes de la Administración Pública Nacional (Argentina)
entre el 25/08 y el 21/11/2026: 65 participantes cargaron 193 informes en Multilente y se registraron 93
proyectos en la Incubadora, de los cuales 49 llegaron a una entrega final. Al 26/11/2026 hay 49 prototipos
en línea con datos ficticios, armados a partir de trabajos de participantes de dos comisiones. Ninguna
de las herramientas se aplicó todavía en el trabajo de un organismo.

## ¿Qué problemas resuelve?

Quien decide casi nunca tiene tiempo de revisar a fondo los informes que recibe, y controlarlos hacia
atrás, insumo por insumo, es inviable. Un total que no cierra, un valor cargado en otra escala, una fórmula
que cambió de criterio sin aviso o una serie con un quiebre pueden pasar inadvertidos y llegar a una
decisión. Multilente sistematiza esa segunda lectura: aplica los mismos controles a todos los cuadros, sin
depender del cansancio ni del apuro de quien revisa, y convierte cada hallazgo en una pregunta concreta
para el área responsable, sin reemplazar a la auditoría ni al área técnica.

Al mismo tiempo, muchas iniciativas de IA en el sector público empiezan por la tecnología y no por el
problema, y quedan aisladas. Incubadora acompaña a cada persona a formular su proyecto respondiendo, antes
de implementarlo, a quién sirve, qué datos usa, qué riesgos trae y quién lo supervisa. Conexiones ayuda a
que esos proyectos no queden en islas desconectadas, y Monitoreo deja registro de lo que se probó y lo que
se aprendió.

## ¿Qué mide hoy y qué no?

Lo medido se publica con sus límites. Sobre 123 errores sembrados en planillas oficiales, la revisión rápida
señaló 119 en la celda correcta. Sobre 15 errores reales de publicaciones oficiales ya corregidas, las
reglas detectaron los 6 errores de cuentas (totales que no suman, escalas, dígitos) y 1 de los 9 que
dependen del significado de las cifras; una IA general que ve los números detecta más de estos últimos,
pero tarda, cuesta y no siempre da el mismo resultado. Por eso las reglas son la base y la IA, una capa
opcional. Son casos ya conocidos y la clasificación es propia: no es una validación independiente. Tampoco
hay evidencia de impacto sobre decisiones. El detalle de cada medición está en la ficha técnica.

## ¿Cómo funciona la herramienta?

### Multilente

**Carga y lectura.** Se carga el informe (Excel o CSV) y se elige el ámbito (organismo público u
organización) y la revisión: rápida, solo con las cuentas y sin IA, o profunda, en la que modelos de IA
proponen cómo interpretar cada cuadro sin ver las cifras y una persona lo confirma. Los PDF y las imágenes
pasan antes por una revisión de lectura: se ve el original al lado de la tabla leída, se corrige lo necesario
y se confirma. La lectura se hace en el propio servidor, y una salvaguarda compara las cifras del original
con las que efectivamente se analizan, declarando cualquier pérdida.

**Controles por lentes.** Reglas programadas y reproducibles revisan totales y componentes, escalas, signos,
períodos, unidades, fórmulas y relaciones entre magnitudes, cada una desde una lente: lo que no puede pasar
(ajedrecista), lo que cambió en el tiempo (cronista), lo que debería acompañarse (orquesta), cómo se calculó
(matemático), qué dicen los antecedentes (radiólogo) y qué conexiones explorar (rizoma). La capa conciliadora
ajusta la prioridad cuando una señal se explica por cómo se publicó o armó el dato.

**Informe y decisión humana.** El informe empieza por lo que no se pudo leer o controlar y sigue con las
consultas para el área, cada una con qué pasó, qué preguntar, la evidencia y dónde está. La decisión y la
firma quedan siempre en manos de una persona, y queda registrado qué se controló y con qué versión.

### Incubadora

**Conversación con la tutora.** La tutora conversa con la persona a partir de diez criterios (problema,
usuarios, evidencia, datos, flujo actual, rol de la IA, supervisión, riesgos, indicador y próximo paso) y
pregunta por lo que falta. Recuerda solo lo que aportó la persona.

**Revisión y entrega.** Cada criterio se revisa con citas literales de lo aportado, que un segundo modelo
comprueba antes de mostrarlas. La propuesta final recibe la devolución docente. De forma opcional y para una
etapa posterior, el proyecto puede evaluarse con un protocolo de quince controles (R-1).

### Conexiones y Monitoreo

**Conexiones.** Cruza los proyectos de un grupo de cursada por temas de una lista fija y muestra cuáles se
parecen por palabras en común, sin IA, como hipótesis para conversar.

**Monitoreo.** Registra avances, riesgos, decisiones, indicadores y aprendizajes; cada registro conserva su
fecha y etapa, y lo ven quienes integran el proyecto y el equipo docente.

## Estándares abiertos

- HTTP/HTTPS (IETF RFC 9110 / RFC 2818) → comunicación cliente-servidor
- REST → diseño de la API
- JSON (ECMA-404 / RFC 8259) → intercambio de datos
- SQL (ISO/IEC 9075) → base de datos PostgreSQL
- Office Open XML (ECMA-376 / ISO/IEC 29500) → lectura de planillas Excel (.xlsx)
- CSV (RFC 4180) → lectura de datos tabulares
- PDF (ISO 32000) → lectura de documentos con texto
- UTF-8 (RFC 3629) → codificación de caracteres
- TLS (IETF RFC 8446) → cifrado de las comunicaciones

## Sector

Gobierno y gestión pública / Finanzas públicas / Educación / Ciencia y Tecnología

## Características

Análisis y visualización de recopilación de datos / Inteligencia artificial / Transparencia y rendición de cuentas

## Objetivos de desarrollo sostenible

Paz, justicia e instituciones sólidas (ODS 16) / Educación de calidad (ODS 4) / Alianzas para lograr los objetivos (ODS 17)

## Recursos

| Recurso | Descripción | Enlace |
|---|---|---|
| Sitio | Las cuatro herramientas, lo medido y lo que falta. | https://gov4action.com |
| Video | «Gov4Action. Cuatro herramientas» (5:21): qué hace cada una, qué se midió y qué falta demostrar. | https://youtu.be/1x6OoWeTxAg |
| Ejemplos sin clave | Informes de ejemplo (uno sin señal y otro con señal) que cualquiera puede abrir. | https://gov4action.com/probar.html |
| Presentación | Qué es, cómo funciona, criterio de uso y preguntas frecuentes. | https://gov4action.com/presentacion |
| Ficha técnica | Arquitectura, criterios de uso y resultados de cada medición, con sus límites. | https://gov4action.com/detalle |
| Estado y evidencia | Qué está implementado, qué se midió y qué falta demostrar. | https://gov4action.com/estado |
| Prototipos | Catálogo de los 17 prototipos con datos ficticios. | https://gov4action.com/prototipos |

## Capturas

Archivos en [`docs/capturas/`](capturas/):

1. `herramientas.png` — las cuatro herramientas (revisar, formular, articular y aprender), con lo que no agregan y lo que ya lograron.
2. `medicion.png` — lo que encuentra Multilente en errores reales ya conocidos, por tipo de error, con sus límites.
3. `escalera.png` — hasta dónde llegan los proyectos: de la idea formulada al prototipo, y lo que todavía no hay.
4. `portada.png` — «Una segunda lectura antes de decidir» (versión anterior, con el nombre Gobernanza).
5. `ejemplos.png` — informes de ejemplo que se pueden probar sin clave.
6. `informe.png` — «El 7 es el mismo. La fórmula, no.»: lo que devolvió la herramienta sobre una planilla en
   la que una celda pasó de promedio ponderado a simple sin cambiar el resultado.
7. `ficha.png` — criterios de uso y resultados de cada medición.
8. `numeros.png` — lo que ya lograron las cuatro herramientas, con las cifras de uso al 14/11/2026 y las mediciones de Multilente al 15/11/2026 (119 de 123 errores sembrados señalados; 6 de 6 y 1 de 9 en errores reales ya conocidos), con la aclaración de que miden uso y señales, no impacto en las decisiones.
9. `video.png` — el video «Gov4Action. Cuatro herramientas» (5:21) incrustado en la página de inicio de gov4action.com, con el reproductor de YouTube en modo de privacidad mejorada.
