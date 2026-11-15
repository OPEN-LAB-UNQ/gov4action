'use strict';
// DATA is inserted from the original eighteen-question learning resource.
const skills = [
    { id: "oportunidades", label: "Oportunidades", short: "Oportunidades", suggestion: "Elegí tres tareas repetitivas del área y pasalas por un filtro simple: frecuencia, fastidio, impacto y riesgo. No busques IA: buscá problemas que duelen." },
    { id: "problema", label: "Formulación del problema", short: "Problema", suggestion: "Antes de pedir una solución, escribí una consigna de una línea: situación, usuario, insumo, resultado esperado y criterio de éxito." },
    { id: "diseno", label: "Diseño de soluciones", short: "Diseño", suggestion: "Dibujá el flujo completo: quién carga datos, qué hace la IA, dónde se valida, quién decide y qué queda registrado." },
    { id: "evaluacion", label: "Evaluación crítica", short: "Evaluación", suggestion: "Tomá una salida de IA y obligate a buscar errores: fuente dudosa, supuesto oculto, dato inventado, omisión o exceso de confianza." },
    { id: "integracion", label: "Integración en procesos", short: "Integración", suggestion: "Convertí una buena respuesta en procedimiento: entrada estándar, responsable, plazo, control, versión y próxima acción." },
    { id: "responsable", label: "Uso responsable", short: "Responsable", suggestion: "Separá datos públicos, internos y sensibles. Definí qué puede entrar a la IA, qué no, y cómo se documenta la decisión humana." }
];
const questions = [
    { skill: "oportunidades", text: "Detecto tareas donde la IA puede aportar valor real, no solo novedad.", detail: "Se refiere a mirar el trabajo cotidiano y encontrar situaciones donde la IA puede mejorar tiempos, calidad o acceso a información, no usarla porque está de moda." },
    { skill: "oportunidades", text: "Puedo priorizar por frecuencia, costo, fastidio, impacto y riesgo.", detail: "No todas las oportunidades valen lo mismo. Una buena priorización empieza por tareas repetidas, costosas o molestas, pero evita comenzar por procesos demasiado sensibles." },
    { skill: "oportunidades", text: "Cuando veo un proceso del área, puedo proponer un primer experimento de IA de bajo riesgo.", detail: "Implica convertir una idea en una prueba chica: por ejemplo, clasificar consultas, resumir documentos públicos o detectar faltantes sin automatizar decisiones críticas." },
    { skill: "problema", text: "Antes de usar IA, puedo explicar qué problema quiero resolver.", detail: "Antes del prompt viene el problema. La pregunta es: qué duele, a quién le duele, con qué información trabajamos y cómo sabríamos que mejoró." },
    { skill: "problema", text: "Distingo un problema real de una solución buscando justificación.", detail: "A veces empezamos diciendo ‘hagamos un chatbot’ o ‘usemos IA’. Este ítem mide si podés volver atrás y preguntar qué necesidad concreta justificaría esa solución." },
    { skill: "problema", text: "Puedo convertir una necesidad difusa en una consigna clara: insumo, tarea, resultado y criterio de éxito.", detail: "Por ejemplo: con estos informes como insumo, detectar alertas de ejecución, producir una síntesis y marcar qué evidencia respalda cada punto." },
    { skill: "diseno", text: "Puedo imaginar un flujo con personas, IA, controles y validaciones.", detail: "Una solución no es solo una respuesta de IA. Es un circuito: quién carga, qué procesa la IA, quién revisa, qué se registra y qué pasa si hay dudas." },
    { skill: "diseno", text: "Sé decidir si conviene ChatGPT, Excel, NotebookLM, automatización, API u otra herramienta.", detail: "La IA no reemplaza todo. A veces Excel alcanza; otras conviene NotebookLM, una automatización, una API o una herramienta interna. El criterio está en elegir bien." },
    { skill: "diseno", text: "Puedo anticipar qué parte del trabajo debe automatizarse y qué parte debe seguir bajo decisión humana.", detail: "Automatizar no significa delegar responsabilidad. Este ítem apunta a separar tareas mecánicas de decisiones que requieren juicio institucional." },
    { skill: "evaluacion", text: "No acepto una respuesta de IA sin revisar errores, supuestos y límites.", detail: "La IA puede sonar segura y estar equivocada. Evaluar críticamente es buscar errores, omisiones, supuestos no declarados y datos inventados." },
    { skill: "evaluacion", text: "Puedo contrastar la salida con datos, documentos o criterio experto.", detail: "No alcanza con que la respuesta parezca razonable. Hay que contrastarla con normativa, expedientes, informes, bases de datos o conocimiento del área." },
    { skill: "evaluacion", text: "Sé formular preguntas de control para detectar omisiones, inconsistencias o exceso de confianza en una respuesta.", detail: "Por ejemplo: qué evidencia respalda esto, qué información falta, qué interpretación alternativa existe, qué podría estar mal o qué no puede afirmarse." },
    { skill: "integracion", text: "Puedo llevar una prueba útil al trabajo real del área.", detail: "Muchas pruebas quedan lindas pero no entran al proceso. Integrar es convertir el experimento en una práctica usable por el equipo." },
    { skill: "integracion", text: "Pienso en responsables, tiempos, trazabilidad y mantenimiento.", detail: "Una solución necesita dueño, frecuencia, forma de control, registro de cambios y alguien que la sostenga cuando cambian documentos, criterios o herramientas." },
    { skill: "integracion", text: "Puedo definir cómo una solución de IA se incorpora a un procedimiento sin depender de una persona aislada.", detail: "Si solo funciona porque una persona sabe cómo pedirlo, todavía es frágil. La idea es dejar criterios, pasos y controles compartidos." },
    { skill: "responsable", text: "Identifico riesgos de privacidad, seguridad y uso indebido de información.", detail: "En gestión pública hay datos sensibles, internos o estratégicos. Este ítem mide si podés detectar qué información no debería exponerse o mezclarse sin control." },
    { skill: "responsable", text: "Tengo claro dónde debe quedar la supervisión humana.", detail: "La IA puede asistir, ordenar o sugerir, pero hay decisiones que requieren responsabilidad humana explícita, especialmente si afectan derechos, recursos o prioridades." },
    { skill: "responsable", text: "Puedo explicar qué datos no deberían cargarse en una herramienta de IA y cómo documentar la decisión tomada.", detail: "No se trata solo de ‘no subir datos sensibles’. También hay que dejar trazabilidad: qué se usó, qué no se usó, por qué y quién validó el resultado." }
];

const routes = {
  oportunidades: ['/incubadora.html', 'Incubadora'], problema: ['/incubadora.html', 'Incubadora'],
  diseno: ['/incubadora.html', 'Incubadora'], evaluacion: ['/multilente.html', 'Multilente'],
  integracion: ['/conexiones.html', 'Conexiones'], responsable: ['/formacion/mapa#clase3-seguridad', 'Mapa: seguridad']
};
function cleanAnswers(value) {
  const result = {};
  if (!value || typeof value !== 'object' || Array.isArray(value)) return result;
  questions.forEach((_, i) => { if (Number.isInteger(value[i]) && value[i] >= 1 && value[i] <= 5) result[i] = value[i]; });
  return result;
}
function evaluate(value) {
  const answers = cleanAnswers(value);
  const axes = skills.map(skill => {
    const values = questions.flatMap((q, i) => q.skill === skill.id && answers[i] !== undefined ? [answers[i]] : []);
    return { ...skill, count: values.length, score: values.length === 3 ? values.reduce((a, b) => a + b, 0) / 3 : null };
  });
  const complete = Object.keys(answers).length === questions.length;
  return { answered: Object.keys(answers).length, complete, axes,
    priorities: complete ? [...axes].sort((a, b) => a.score - b.score).slice(0, 2) : [] };
}
if (typeof module !== 'undefined') module.exports = { cleanAnswers, evaluate, questions, skills };
if (typeof document !== 'undefined') {
  const storageKey = 'gov4action_autoevaluacion_v1';
  let answers = {};
  const storageNote = document.getElementById('storageNote');
  try { answers = cleanAnswers(JSON.parse(sessionStorage.getItem(storageKey) || '{}')); }
  catch (_) { storageNote.textContent = 'Podés responder aquí. El navegador no permitió recuperar respuestas; no se enviarán al servidor.'; }
  const container = document.getElementById('questions');
  skills.forEach(skill => {
    const group = document.createElement('section'); group.className = 'question-group';
    const heading = document.createElement('h2'); heading.textContent = skill.label; group.append(heading);
    questions.forEach((q, i) => {
      if (q.skill !== skill.id) return;
      const field = document.createElement('fieldset'); field.className = 'card question';
      const legend = document.createElement('legend'); legend.textContent = `${i + 1}. ${q.text}`;
      const detail = document.createElement('p'); detail.textContent = q.detail;
      const options = document.createElement('div'); options.className = 'scale';
      for (let n = 1; n <= 5; n++) {
        const label = document.createElement('label'); const input = document.createElement('input');
        input.type = 'radio'; input.name = `q${i}`; input.value = String(n); input.checked = answers[i] === n;
        input.addEventListener('change', () => {
          answers[i] = n;
          try { sessionStorage.setItem(storageKey, JSON.stringify(answers)); }
          catch (_) { storageNote.textContent = 'Respuestas disponibles mientras esta página permanezca abierta. El navegador no permite guardarlas.'; }
          render();
        });
        const text = document.createElement('span'); text.textContent = String(n);
        label.append(input, text); options.append(label);
      }
      field.append(legend, detail, options); group.append(field);
    });
    container.append(group);
  });
  function render() {
    const result = evaluate(answers);
    document.getElementById('progressText').textContent = `${result.answered} de 18 respuestas`;
    document.getElementById('progress').value = result.answered;
    document.getElementById('resultLabel').textContent = result.complete ? 'Tu percepción actual, por habilidad' : 'Completá las 18 respuestas para elegir por dónde seguir.';
    const breakdown = document.getElementById('breakdown'); breakdown.replaceChildren();
    result.axes.forEach(axis => {
      const row = document.createElement('li');
      row.textContent = `${axis.label}: ${axis.score === null ? `${axis.count}/3 respuestas` : `${axis.score.toFixed(1)} de 5`}`;
      breakdown.append(row);
    });
    const recommendations = document.getElementById('recommendations'); recommendations.replaceChildren();
    result.priorities.forEach(axis => {
      const article = document.createElement('article'); article.className = 'card';
      const h = document.createElement('h3'); h.textContent = axis.label;
      const p = document.createElement('p'); p.textContent = axis.suggestion;
      const a = document.createElement('a'); a.href = routes[axis.id][0]; a.textContent = `Trabajar con ${routes[axis.id][1]} →`;
      article.append(h, p, a); recommendations.append(article);
    });
    document.getElementById('copyResult').disabled = !result.complete;
    const radar = document.getElementById('radar');
    const point = (i, radius) => [200 + Math.sin(i * Math.PI / 3) * radius, 180 - Math.cos(i * Math.PI / 3) * radius];
    const polygon = radius => skills.map((_, i) => point(i, radius).join(',')).join(' ');
    let markup = '<title>Perfil de autoevaluación en seis habilidades</title>';
    for (let level = 1; level <= 5; level++) markup += `<polygon points="${polygon(level * 23)}" fill="none" stroke="#c5d9e8"/>`;
    skills.forEach((skill, i) => { const [x, y] = point(i, 145); markup += `<text x="${x}" y="${y}" text-anchor="middle" fill="#10234f" font-size="12">${skill.short}</text>`; });
    if (result.complete) markup += `<polygon points="${result.axes.map((axis, i) => point(i, axis.score * 23).join(',')).join(' ')}" fill="#22aaad" fill-opacity=".25" stroke="#285bb4" stroke-width="3"/>`;
    radar.innerHTML = markup;
  }
  document.getElementById('resetAnswers').addEventListener('click', () => {
    answers = {}; try { sessionStorage.removeItem(storageKey); } catch (_) { /* optional storage */ }
    container.querySelectorAll('input').forEach(input => { input.checked = false; });
    document.getElementById('copyStatus').textContent = 'Respuestas borradas.'; render();
  });
  document.getElementById('copyResult').addEventListener('click', async () => {
    const result = evaluate(answers); if (!result.complete) return;
    const text = 'Gov4Action · Autoevaluación de percepción, no certificación\n' + result.axes.map(a => `${a.label}: ${a.score.toFixed(1)}/5`).join('\n');
    try { await navigator.clipboard.writeText(text); document.getElementById('copyStatus').textContent = 'Resumen copiado.'; }
    catch (_) { document.getElementById('copyStatus').textContent = 'No se pudo copiar. Podés seleccionar los resultados y copiarlos manualmente.'; }
  });
  render();
}
