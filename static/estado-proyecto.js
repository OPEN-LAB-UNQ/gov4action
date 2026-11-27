'use strict';
(() => {
  const root = document.getElementById('estado-proyecto');
  if (!root) return;
  const text = (tag, value, parent = root) => {
    const el = document.createElement(tag); el.textContent = value; parent.append(el); return el;
  };
  const stamp = value => {
    if (!value) return 'sin fecha disponible';
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(value)) return value;
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? value : d.toLocaleString('es-AR', {timeZone: 'America/Argentina/Buenos_Aires', hour12: false});
  };
  const source = (label, item) => text('p', `${label}: ${item.estado === 'actualizado' ? 'fuente consultada' : item.estado === 'ultima_copia' ? 'fuente sin respuesta; última copia disponible' : 'sin datos disponibles'}. Consulta: ${stamp(item.consultado_en)}.`);
  let busy = false;
  async function refresh() {
    if (busy) return;
    busy = true;
    try {
      const r = await fetch('/api/publico/estado', {cache: 'no-store', signal: AbortSignal.timeout(12000)});
      if (!r.ok) throw new Error('Estado no disponible');
      const s = await r.json();
      root.replaceChildren();
      text('p', `Aplicación ${s.versiones.aplicacion} · Motor ${s.versiones.motor} · Documento v${s.versiones.documento}`);
      source('Uso registrado', s.uso);
      if (s.uso.datos) {
        const u = s.uso.datos;
        const grid = document.createElement('div'); grid.className = 'grid4'; root.append(grid);
        for (const [key, label] of [['informes','informes cargados'],['informes_con_devolucion','informes con devolución'],['participantes','participantes que cargaron informes'],['proyectos','proyectos registrados'],['proyectos_entregados','proyectos entregados (con o sin revisión docente)']]) {
          const card = document.createElement('article'); card.className = 'card'; grid.append(card);
          text('h3', `${u[key] ?? '—'}`, card); text('p', label, card);
        }
      }
      text('p', 'Los informes cargados son todos los subidos; los «con devolución» ya recibieron su devolución. Son conteos de actividad, no indicadores de impacto. Excluyen cuentas administradoras y las cuentas de prueba configuradas. No se publican nombres ni contenidos privados.');
      const v = s.validacion;
      text('h3', 'Última validación técnica');
      text('p', v.tests ? `${v.tests.passed}/${v.tests.collected} pruebas Python aprobadas · ${v.javascript ? `${v.javascript.passed}/${v.javascript.collected} pruebas JavaScript aprobadas` : 'sin registro actualizado de JavaScript'} · Corte: ${stamp(v.validado_en || v.tests.date)}.` : 'No hay una validación registrada.');
      text('p', v.vigente ? 'La huella del código, la interfaz y los controles coincide con la versión validada.' : 'La evidencia disponible no acredita la versión completa actual. Se necesita una nueva validación.');
      if (document.getElementById('catalogo-prototipos')) {
        source('Catálogo de prototipos', s.prototipos);
        const catalog = document.getElementById('catalogo-prototipos'); catalog.replaceChildren();
        if (!s.prototipos.datos) text('p', 'El catálogo no está disponible en este momento.', catalog);
        for (const item of s.prototipos.datos || []) {
          const card = document.createElement('article'); card.className = 'card'; catalog.append(card);
          text('h3', item.titulo, card); text('p', item.medicion || 'Medición aún no documentada.', card);
          if (/^https:\/\/proyectos(grupo_b)?\.entornodepruebas\.com\.ar\/[a-z0-9-]+\/$/.test(item.url || '')) {
            const link = text('a', 'Abrir el prototipo →', text('p', '', card));
            link.href = item.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
            link.setAttribute('aria-label', `Abrir el prototipo: ${item.titulo} (se abre en otra pestaña)`);
          }
        }
      }
    } catch (_) {
      let note = document.getElementById('estado-error');
      if (!note) { note = text('p', ''); note.id = 'estado-error'; }
      note.textContent = 'No se pudo actualizar la información. Los datos que se vean corresponden a la consulta anterior; volveremos a intentar en cinco minutos.';
    } finally { busy = false; }
  }
  refresh(); setInterval(refresh, 300000);
})();
