// 0.10.76: en Monitoreo, lo propio del proyecto: su prototipo en acción y sus indicadores.
const {test}=require('node:test'); const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const app=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const trozo=(desde,hasta)=>app.slice(app.indexOf(desde),app.indexOf(hasta));
const ctx=vm.createContext({SITIO_PROTOTIPOS:'https://proyectos.entornodepruebas.com.ar/',
  escapeHtml:s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'),
  contar:(n,s,p)=>`${n} ${n===1?s:p}`,monitoreoTipoLabel:t=>({avance:'Avance',indicador:'Indicador'}[t]||t),Date,Number,Object,String});
ctx.SITIO_PROTOTIPOS_GRUPO_B='https://proyectos-grupo-b.example.org/';
vm.runInContext(trozo('function esDePrototipos(','function enlacePrototipoHtml('),ctx);
vm.runInContext(trozo('function monitoreoProyectoHtml(','function renderMonitoreo('),ctx);

const BASE={modo:'prueba',puede_registrar:true,por_tipo_etapa:{avance:1,indicador:3},metricas:{por_tipo:{avance:9}},en_accion:{
  url:'https://proyectos.entornodepruebas.com.ar/boletin-oficial/',
  medicion_url:'https://proyectos.entornodepruebas.com.ar/boletin-oficial/control',
  medicion_texto:'Control paralelo <diario>'},indicador_propuesto:'Medir el tiempo "antes"',
  indicadores_registrados:[{titulo:'Minutos <b>',valor:90,anterior:120,mediciones:2,fecha:'2026-11-08T12:00:00'}]};

test('muestra el prototipo en acción, cómo mide y los indicadores de la etapa, con los textos escapados',()=>{
  const html=ctx.monitoreoProyectoHtml(BASE);
  assert.match(html,/Tu proyecto en acción/);
  assert.match(html,/href="https:\/\/proyectos\.entornodepruebas\.com\.ar\/boletin-oficial\/"[^>]*>Abrir el prototipo/);
  assert.match(html,/boletin-oficial\/control"[^>]*>Ver cómo mide/);
  assert.match(html,/Cómo lo mide el prototipo<\/span> Control paralelo &lt;diario&gt;/);
  assert.match(html,/En tu propuesta<\/span> «Medir el tiempo &quot;antes&quot;»/);
  assert.match(html,/<strong>Minutos &lt;b&gt;<\/strong>: 90 <span class="hint">\(antes: 120\)<\/span> · 2 mediciones/);
  assert.match(html,/Registrado en esta etapa: Avance: 1 · Indicador: 3/);  // la etapa vigente, no el total
  assert.doesNotMatch(html,/Avance: 9/);
});

test('para el equipo docente los textos son neutros y no invitan a registrar',()=>{
  const html=ctx.monitoreoProyectoHtml({...BASE,puede_registrar:false,indicadores_registrados:[]});
  assert.match(html,/El proyecto en acción/); assert.doesNotMatch(html,/Tu proyecto en acción/);
  assert.match(html,/En la propuesta<\/span>/); assert.doesNotMatch(html,/En tu propuesta/);
  assert.match(html,/Todavía no hay indicadores registrados en esta etapa\./);
  assert.doesNotMatch(html,/Elegí el tipo/);
});

test('un enlace que no es del sitio de prototipos no se muestra',()=>{
  const html=ctx.monitoreoProyectoHtml({...BASE,en_accion:{...BASE.en_accion,medicion_url:'https://otro.sitio/x'}});
  assert.match(html,/Abrir el prototipo/); assert.doesNotMatch(html,/Ver cómo mide/);
  const sinBloque=ctx.monitoreoProyectoHtml({...BASE,en_accion:{url:'javascript:alert(1)'}});
  assert.doesNotMatch(sinBloque,/proyecto en acción/);
});

test('sin indicadores registrados invita a registrarlos; en cartera no hay bloque',()=>{
  const html=ctx.monitoreoProyectoHtml({modo:'prueba',puede_registrar:true,en_accion:null,indicadores_registrados:[],metricas:{}});
  assert.match(html,/Todavía no hay indicadores registrados\. Elegí el tipo «Indicador»/);
  assert.doesNotMatch(html,/proyecto en acción/);
  assert.equal(ctx.monitoreoProyectoHtml({modo:'cartera'}),'');
});
