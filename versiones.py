"""Versiones independientes; los protocolos institucionales viven en VersionProtocolo."""
import hashlib
from functools import lru_cache
from pathlib import Path

# 0.10.83: motor 0.10.62: menos falsas alarmas, trimestres abreviados, duplicados, regla de valor fuera de orden y lectura con IA más rápida.
# 0.10.65: aplicación 0.10.65 (motor sin cambios): documento v9.4 en la ficha; la presentación no nombra el ministerio de los participantes.
# 0.10.64: aplicación 0.10.64 (motor sin cambios): Python 3.12 y dependencias sin avisos de seguridad conocidos.
# 0.10.63: aplicación 0.10.63 (motor sin cambios): la tutora no deja preguntas cortadas ni repite pendientes respondidos.
# 0.10.62: aplicación 0.10.62 (motor sin cambios): grupos de cursada; cada grupo ve sus proyectos y su votación.
# 0.10.61: aplicación 0.10.61 (controles sin cambios): ajustes de una auditoría externa (contador, alertas, health, errores, tope, textos).
# 0.10.60: motor 0.10.60: lector del cuadro con GPT y Gemini; DeepSeek sólo si se agrega a mano.
# 0.10.59: motor 0.10.59: totales con filas en cero, tramos parejos, promedios y series empalmadas.
# 0.10.58: aplicación 0.10.58 (motor sin cambios): /privacidad para la UE y el video detrás de un botón.
# 0.10.57: motor 0.10.57: libros con bloques apilados y filas de códigos de serie; años sin datos en el cuadro.
# 0.10.56: motor 0.10.56: total de columna en filas que son sumas; libros con el rango inflado recortados.
# 0.10.55: motor 0.10.55: series de 2 o 3 períodos corroboradas por la misma relación en otras hojas o cuadros.
# 0.10.54: Incubadora: ir a cada sección y buscar dentro de un trabajo compartido.
# 0.10.53: Incubadora: trabajos completos desde la galería de casos, sin datos privados.
# 0.10.52: Incubadora: detección por texto separada de los cierres del participante.
# 0.10.51.1: Incubadora: cronología de rectificaciones calculada por el programa; verificador con modelo propio.
# 0.10.51: Incubadora: una cita rectificada después por el participante no sustenta el criterio.
# 0.10.50: Incubadora: segunda lectura de pertinencia de las citas; pedidos de síntesis respetados.
# 0.10.49.1: Incubadora: pedir una revisión no es evidencia; revisión en texto plano.
# 0.10.49: Incubadora: memoria y atribución de fuentes de la tutora.
# 0.10.48: «unidad a confirmar» explicada en pantalla y PDF.
# 0.10.47: motor 0.10.47: porcentajes confirmados que suman cantidades, una pregunta de unidad por cuadro.
# 0.10.46: la exploración con IA no publica una conformidad como discordancia.
# 0.10.45: exploración con IA: celda citada, cabeceras combinadas, atipicidad y lentes no ejecutadas.
# 0.10.44: exploración con IA: año de cada mes en los fragmentos y cronología validada.
# 0.10.43: motor 0.10.39: un mes sin datos no hace vecinos a dos períodos; límites con su cuadro.
# 0.10.42: motor 0.10.38: interpretación confirmada en lentes, conciliador y lectura con IA.
# 0.10.41.8: las páginas públicas no nombran organismos con errores reales.
# 0.10.41.7: video de presentación incrustado en /presentacion.
# 0.10.41.6: la filmina del recorrido de la charla entra en pantallas de notebook.
# 0.10.41.5: lema «La IA propone, las reglas comprueban, la persona decide» y cinco pasos.
# 0.10.41.4: documento metodológico v9.3.
# 0.10.41.3: proyecto de OPEN LAB (UNQ); licencia MIT.
# 0.10.41.2: la suite de pruebas nunca manda correos reales.
# 0.10.41.1: presentación reordenada; «Qué cambia en el recorrido» en la ficha.
# 0.10.41: «¿Qué resultó ser?» a la vista, pregunta de cierre e indicador de valor.
# 0.10.40: Incubadora: aviso por correo al docente por cada consulta y resumen diario de las sin respuesta.
# 0.10.39: seguridad de los datos en las dos revisiones; documento v9.2; la interpretación orienta, no apaga.
# 0.10.38: Incubadora: la pantalla no pisa la entrega pegada y no guardada; tope de 30.000 de punta a punta.
# 0.10.37: motor 0.10.37: formato de series de un ministerio (códigos de serie, trimestres «I-00», saldo neto).
# 0.10.36: motor 0.10.36: paneles con total propio, fila de unidad y cronogramas de deuda.
# 0.10.35: revisión rápida (sin IA, por defecto) y revisión profunda en el motor, el informe y la pantalla.
# 0.10.24: mensaje único (radiografía, cinco frases, qué esperar) en la app y en las páginas públicas.
# 0.10.23: motor 0.10.23: en una hoja de variaciones, el signo distinto no encabeza como alta.
# 0.10.22: motor 0.10.22: valor repetido y columna «Total» no son errores de escala.
# 0.10.21: motor 0.10.21: en una distribución porcentual, una participación chica no está fuera de escala.
# 0.10.20: motor 0.10.20: la columna de años con sus meses no se arma como serie.
# 0.10.19: motor 0.10.19: años con sus meses en la misma columna y año.mes no son «año no entero».
# 0.10.18: motor 0.10.18: llamadas de nota en el encabezado, paneles completos, filas de resultado.
# 0.10.17.1: el PDF no deja una página en blanco después de una página llena.
# 0.10.17: reintento de lectoras y analogía entre cuadros iguales en la lectura previa.
# 0.10.16: modo básico (por defecto) y avanzado en la interfaz.
# 0.10.15: faltantes del lector en una línea; motivo de validez cuando no hay controles.
# 0.10.14: saltos el mismo año en varias hojas, una consulta común que va primero.
# 0.10.13: motor 0.10.13: reclasificación entre categorías y prioridad por peso sobre el total.
# 0.10.12.1: lo no controlado agrupa los lugares con el mismo motivo.
# 0.10.12: confirmación previa y PDF resumen los cuadros por tipo; consultas en la página 1 del PDF.
# 0.10.11: el informe muestra primero sólo los casos principales; el resto queda plegado.
# 0.10.10: durante el análisis se consulta el estado del trabajo, no el informe completo.
# 0.10.9: libros enormes: el libro se abre una vez para los encabezados.
# 0.10.8: «Cancelar lectura» durante la interpretación previa.
# 0.10.7: año arriba y mes abajo; sin falsas alarmas por series intermitentes, saldos cancelados y diferencias.
# 0.10.6: encabezado de dos niveles por combinaciones, total arriba y celda nombrada en el cruce.
# 0.10.5: lecturas confirmadas orientan automáticamente; resultados revisados separados.
# 0.10.4: biblioteca operativa con revisión humana y orientación conservadora de la interpretación.
# 0.10.3: separa cuadros breves apilados. Desde 0.10.2: distingue selección de ejecución.
APP_VERSION = "0.10.89"  # Mantenimiento de configuración, exportaciones y guía de instalación (motor sin cambios: multilente-0.10.62)
API_VERSION = "0.4.3"  # Distingue lecturas observadas de resultados evaluados.
DOCUMENT_VERSION = "9.8"  # Zenodo: versión 10.5281/zenodo.24221830 (v0.9.8, 14/11/2026, cierra la etapa bajo el nombre Gobernanza, sin nombres de organismos; anterior 9.7: 10.5281/zenodo.24067159); serie 10.5281/zenodo.22063241.
ANALYSIS_VERSION = "multilente-0.10.62"  # Motor 0.10.62: Total de columna: un total que suma sólo algunas columnas (otras son cargos u horas) no se compara con todas; trimestres con año de dos dígitos y con llamada a nota («3º Trim 10», «2° Trim 07 1») se leen como períodos; los hallazgos idénticos (misma regla, celda y texto) salen una vez; regla «valor fuera de orden» (lente Cronista): en una serie de 8 o más valores que sube, un valor que cae por debajo de los anteriores y que quedaría en orden en otro lugar señala un tramo cargado corrido de lugar (caída de al menos 10 %, o 25 % si es un solo valor; sin la primera ni la última cifra; una misma caída en tres o más series es causa común). Lectura con IA: un rol dudoso se descarta y se cuenta sin invalidar la lectura; seis cuadros a la vez; lecturas idénticas reutilizadas hasta 14 días y declaradas. Desde 0.10.61: Controles sin cambios: el sondeo previo ya no afirma que una repetición «es la forma del cuadro, no un error»; dice que puede ser eso o un error de plantilla y que no puede distinguirlos sin mirar el cuadro. Desde 0.10.60: Lector del cuadro: lectoras por defecto GPT y Gemini (DeepSeek sólo en LECTOR_LECTORAS); con dos lectoras una relación se comprueba si la proponen las dos; el pedido de la interpretación previa pide todas las relaciones que los rótulos sostienen. Desde 0.10.59: Filas con total y partes en cero no confirman un total; tres o más filas seguidas con una diferencia pareja (hasta 15 %) son una señal alta por tramo; promedios de valores con pocos decimales: su resolución, sólo para el cierre y las cifras de un repetido; serie empalmada: coincidencias esperadas con su unidad. Desde 0.10.57: Fila de códigos de serie dentro del cuadro: metadato que separa bloques; bloques de distinta frecuencia en una columna de períodos: una serie por bloque, validada con su ordinal; «I.16» y fechas como texto son períodos; marcas «n,d,» y «s.d»; unidades físicas; un período sin número en ninguna serie que lo abarca no tiene datos. Desde 0.10.56: Total de columna: un total que supera la suma de sus partes (todas presentes y no negativas) en más del 15 % y hasta el 50 % se señala si en la misma fila cierran al menos tres columnas distintas con valores, la mitad de las comparadas. Un libro que superaría el rango máximo sólo por celdas sin datos, la dimensión o hasta 20 celdas sueltas por hoja se lee recortado al bloque con datos (primero sólo el formato). Desde 0.10.55: Series de 2 o 3 períodos comparables: la relación total = suma de componentes se corrobora si la misma relación (mismos rótulos, origen y unidad) cierra en todos sus períodos en al menos otras 3 hojas o cuadros del archivo, ninguna otra falla el mismo período y el 80 % de las repeticiones está completo; las diferencias dentro del redondeo de los sumandos no se señalan. Desde 0.10.47: Columnas confirmadas como porcentaje que suman un total de cantidades en un cuadro sin eje temporal: una pregunta de unidad por cuadro (porcentajes_como_cantidades). Desde 0.10.39: Diferencias sólo entre períodos consecutivos con dato; lo no leído por el lector, con su cuadro; el eje se describe como períodos, no como años. Desde 0.10.38: Interpretación confirmada en Ajedrecista, Rizoma, conciliador y lectura con IA; asociaciones sin filas de total y diferencias sólo con eje temporal verificado; importes estadísticos con signo libre y sin reversas. Desde 0.10.37: Fila de códigos de serie como metadato; trimestres romanos con año de dos o cuatro dígitos; rótulo de columna = el más bajo con texto del encabezado; «Total» en un nivel intermedio; saldo neto (componentes de egreso se restan). Desde 0.10.36: Paneles con un total por panel; años arriba de la fila de unidad; cronogramas de deuda (paneles [instrumento, CAPITAL, INTERÉS] con TOTAL al pie, componente sin sobrante, cierre exacto en perfiles de vencimientos con prioridad media); fila de categoría sin período, filas «Como % del total» y ruido de punto flotante con signo. Desde 0.10.34: Columnas de tiempo (Período, Año, Mes, Fecha) fuera de las sumas. Desde 0.10.33: Triangulación en paneles; conciliación ≥ 1 % y evidencia exacta con rareza alta son prioridad alta. Desde 0.10.32: Decimal aislado en una columna de enteros (ocho o más enteros distintos de cero; sin ruido de punto flotante ni fórmulas). Desde 0.10.31: «Tipo de …» con cifras no es sensible; total redondeado admite una unidad de su último decimal. Desde 0.10.30: Total por panel con años en filas; marcas de sin dato no vuelven sensible una columna de conteo; «Distribución relativa» no sumable. Desde 0.10.29: Totales por panel, «Total» arriba y columnas con «-»; diferencias explicadas por otra columna, un dato no publicado o una distribución que suma 99,8 no se señalan. Desde 0.10.23: Signo distinto en hojas de variaciones: registrado, prioridad media. Desde 0.10.22: Escala por columna: sin señal para valores repetidos ni columnas «Total». Desde 0.10.21: Distribuciones porcentuales: sin «fuera de escala» por participaciones chicas. Desde 0.10.20: La columna de años con sus meses no entra en las series verticales. Desde 0.10.19: Años con sus meses en la misma columna: sin señales y fuera de los controles temporales; año.mes como número: serie mensual. Desde 0.10.18: «(1)», «(2)» entre los años del encabezado son columnas de notas, no los períodos −1 y −2; paneles variable × año completos con el rótulo combinado de arriba; filas de ahorro y de resta de romanos admiten cualquier signo. Desde 0.10.13: Reclasificación entre categorías registrada en la evidencia (componentes fuera del ritmo del total, en sentido contrario, con el total que cierra); prioridad por peso sobre el total. Desde 0.10.9: Mismos resultados, sin reabrir el libro por hoja ni rearmar la tabla de períodos por punto. Desde 0.10.7: Año arriba y mes abajo (con «Subtotal 2025») como período mensual; picos sólo si sobresalen de toda la serie cuando es intermitente; valor aislado no junto a un cero; «Diferencia» sin escala propia. Desde 0.10.6: Combinaciones verticales que bajan suman la fila de rótulos (no la de unidades); total arriba en la triangulación fila × columna; cruce fila × columna de las cuentas del lector. Desde 0.10.5: Antecedentes automáticos y trazabilidad por cuadro. Desde 0.10.1: Plan confirmado por cuadro; fechas operativas separadas de series agregadas. Desde 0.9.20.1: Lector del cuadro (lector-1): relaciones leídas a ciegas por tres modelos, acordadas por dos y verificadas con los números. Desde 0.9.18: Sondeo previo (sondeo-2) sobre las señales de cada hoja; totales cruzados con bloques anidados y sin rótulo; arreglos de falsas alarmas con planillas reales (fórmula fija, panel, rótulos repetidos, filas repetidas aisladas). Desde 0.9.17: Encabezado de dos niveles año + trimestre leído por el modelo común; series de signo mixto y flujos declarados sin picos ni signo aislado; «s/i», «s/inf» y «///» como marcas de sin dato y la marca repetida en la hoja como convención; escala por columna fuera de las variaciones y tasas; filas de resultado, financiamiento y saldo admiten negativos; un código padre igual a su único hijo no es una fila copiada. Desde 0.9.16: Jerarquía por código: cada código padre es el total de sus hijos inmediatos; total suelto unido a sus componentes a través de filas sin datos; cambio de escala en el año en que la nota declara otra unidad queda como contexto. Desde 0.9.15: «<5» y «s.e.» como dato suprimido (no 5); «Transporte» al pie como total de arrastre; filas «Promedio…» fuera de los cierres; fecha constante fuera del eje de períodos; bimestres y años «X2017»; formato inglés por el idioma del PDF. Desde 0.9.14: Subtotales de columna intercalados contra sus períodos; punto ambiguo declarado al comienzo; años guardados como fechas. Desde 0.9.13: Columnas auxiliares («CV (%)») fuera de los períodos; «2025M01»; columnas fuera de los controles declaradas también en CSV y PDF; prioridad limitada en celdas declaradas mal leídas. Desde 0.9.12: Superíndices fuera de las cifras; renglones de prosa fuera de la grilla del PDF. Desde 0.9.11: ×10 en el primer período; rótulos de PDF por costura y por palabra. Desde 0.9.10: Notación científica como cifra; rótulos de PDF pegados se separan. Desde 0.9.9: Cifras del original contra las analizadas; dos cuadros por página de PDF; meses «enero de 2025». Desde 0.9.8: Llamadas de nota pegadas al número; signo aislado en el primer o último período. Desde 0.9.7: Rubro entero en otra escala con el total sin recalcular. Desde 0.9.6: lectura sin inferencia de tipos y formato por columna en los controles. Desde 0.9.5: patrón de fórmulas con referencias fijas ($). Desde 0.9.4: formato numérico por cuadro, volatilidad por cuadro, totales cruzados, salvaguarda de cobertura.
AUTOMATIC_PROTOCOL_VERSION = "controles-automaticos-1.0"


@lru_cache(maxsize=1)
def version_codigo() -> str:
    """Huella del código ejecutable, también disponible en distribuciones sin Git."""
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    files = sorted([*root.glob("*.py"), *root.glob("core/**/*.py"),
                    *root.glob("services/**/*.py"), *root.glob("routers/**/*.py")])
    for path in files:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def version_control(lente: str) -> str:
    root = Path(__file__).resolve().parent / "services"
    files = sorted([root / "lentes" / f"{lente}.py", root / "lentes" / "__init__.py",
                    *root.glob("calculos/*.py"), *root.glob("controles_excel/*.py"),
                    root / "excel_encabezados.py", root / "excel_cobertura.py", root / "excel_estructura.py", root / "prioridad_controles.py", root / "lectura_temporal.py",
                    root / "perfilado.py", root / "observaciones.py", root / "validez.py", root / "interpretacion_previa.py",
                    root / "formula_integridad.py", root / "pdf_controles.py",
                    root / "guardrails.py", root / "controles_solicitados.py"])
    digest = hashlib.sha256()
    for path in files:
        if path.exists():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()
