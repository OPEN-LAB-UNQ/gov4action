// 0.10.73: «#/monitoreo» (enlace del sitio de prototipos) abría Mi proyecto con la tarjeta de Monitoreo a la vista.
// 0.10.77: Monitoreo tiene su propia pantalla: «#/monitoreo» y el botón de Inicio llevan ahí, no a la Incubadora.
const {test}=require('node:test'); const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const app=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const trozo=(desde,hasta)=>{const i=app.indexOf(desde),j=app.indexOf(hasta,i);assert.ok(i>=0&&j>i,desde);return app.slice(i,j);};

function nodo(id){
  const n={id,hidden:false,textContent:'',style:{},open:false,parentElement:null,clases:new Set(),
    classList:{toggle(c,si){if(si)n.clases.add(c);else n.clases.delete(c);}},
    appendChild(el){el.parentElement=n;n.hijo=el;}};
  return n;
}
function entorno({rol='analista',vista='monitoreo',api=async()=>({}),incubadoraVista}={}){
  const llamadas={vistas:[],api:[],toasts:[]};
  const card=nodo('proyecto-monitoreo-card'); const h3={textContent:''}; card.querySelector=()=>h3;
  const cuerpo=nodo('monitoreo-vista-cuerpo'); const admin=nodo('proyecto-admin-panel');
  cuerpo.appendChild(card);  // así llega en index.html: la tarjeta empieza dentro de su pantalla
  card.style.display='none';
  const els={'proyecto-monitoreo-card':card,'monitoreo-vista-cuerpo':cuerpo,'proyecto-admin-panel':admin,
    'monitoreo-vista-aviso':nodo('aviso'),'monitoreo-vista-aviso-texto':nodo('texto'),'monitoreo-vista-ir':nodo('ir'),
    'incubadora-vistas':nodo('vistas'),'incubadora-personal':nodo('personal')};
  const ctx=vm.createContext({
    state:{currentUser:{rol},vista,incubadoraVista},
    window:{location:{hash:'#/monitoreo'}},
    document:{getElementById:id=>els[id]||null,querySelectorAll:()=>[]},
    mostrarVista:(nombre,url)=>llamadas.vistas.push([nombre,url]),
    abrirDetalle:async()=>{},configurarEspacioIncubadora(){},cargarProyectoIADetalle:async()=>{},
    apiFetch:async(url)=>{llamadas.api.push(url);return api(url);},toast:(m)=>llamadas.toasts.push(m),
    contar:(n,s)=>`${n} ${s}`,escapeHtml:s=>String(s),monitoreoProyectoHtml:()=>'',Number,String,
  });
  vm.runInContext(trozo('async function navegarPorUrl(','document.querySelectorAll("[data-nav-target]")'),ctx);
  vm.runInContext(trozo('function renderMonitoreo(','document.getElementById("btn-guardar-proyecto")'),ctx);
  vm.runInContext(trozo('function irDesdeAvisoMonitoreo(','document.getElementById("monitoreo-vista-ir")'),ctx);
  vm.runInContext(trozo('function configurarEspacioIncubadora(',"document.querySelectorAll('[data-incubadora-vista]').forEach(btn => btn.addEventListener"),ctx);
  return {ctx,card,cuerpo,admin,els,llamadas};
}
const DATOS={proyecto_id:7,modo:'prueba',puede_registrar:true,proyecto_titulo:'Boletín',alcance:'Modo prueba',metricas:{},registros:[]};

test('«#/monitoreo» abre la pantalla de Monitoreo, no Mi proyecto',async()=>{
  const {ctx,llamadas}=entorno({vista:'inicio'});
  await ctx.navegarPorUrl();
  assert.equal(JSON.stringify(llamadas.vistas),JSON.stringify([['monitoreo',false]]));
});

test('en su pantalla, la tarjeta va abierta, sin el desplegable, con el proyecto de quien entra',async()=>{
  const {ctx,card,cuerpo,els,llamadas}=entorno({api:async()=>DATOS});
  await ctx.cargarVistaMonitoreo();
  assert.equal(JSON.stringify(llamadas.api),JSON.stringify(['/monitoreo/mio']));  // sólo lee: no crea el proyecto
  assert.equal(card.parentElement,cuerpo); assert.equal(card.style.display,'block');
  assert.equal(card.open,true); assert.ok(card.clases.has('monitoreo-pantalla'));
  assert.equal(card.querySelector().textContent,'Boletín · modo prueba');
  assert.equal(els['monitoreo-vista-aviso'].hidden,true);
  assert.equal(ctx.state.monitoreoProyectoId,7); assert.equal(ctx.proyectoMonitoreoActual(),7);
});

test('sin proyecto, la pantalla invita a empezarlo en la Incubadora y no muestra la tarjeta',async()=>{
  const {ctx,card,els}=entorno({api:async()=>({proyecto_id:null,modo:'prueba'})});
  await ctx.cargarVistaMonitoreo();
  assert.equal(card.style.display,'none');
  assert.equal(els['monitoreo-vista-aviso'].hidden,false);
  assert.match(els['monitoreo-vista-aviso-texto'].textContent,/Cuando lo empieces en la Incubadora/);
  assert.equal(els['monitoreo-vista-ir'].hidden,false);
  assert.equal(els['monitoreo-vista-ir'].textContent,'Empezar mi proyecto en la Incubadora');
  assert.equal(ctx.proyectoMonitoreoActual(),null);
});

test('la cuenta administradora ve un aviso que la manda a la supervisión docente y no pide nada',async()=>{
  const {ctx,els,llamadas}=entorno({rol:'admin'});
  await ctx.cargarVistaMonitoreo();
  assert.equal(JSON.stringify(llamadas.api),JSON.stringify(['/monitoreo/mio']));  // 0.10.85: sólo mira si tiene seguimiento propio
  assert.match(els['monitoreo-vista-aviso-texto'].textContent,/Supervisión docente[\s\S]*Ver como/);
  assert.equal(els['monitoreo-vista-ir'].textContent,'Ir a la supervisión docente');
});

test('la cuenta administradora con un proyecto de seguimiento propio ve su Monitoreo en la pantalla',async()=>{
  const propio={...DATOS,proyecto_id:4,modo:'piloto',propio:true,habilitado:true,proyecto_titulo:'Gov4Action Multilente',alcance:'Seguimiento propio'};
  const {ctx,card,cuerpo,els}=entorno({rol:'admin',api:async()=>propio});
  await ctx.cargarVistaMonitoreo();
  assert.equal(card.parentElement,cuerpo); assert.equal(card.style.display,'block');
  assert.equal(card.querySelector().textContent,'Gov4Action Multilente');
  assert.equal(els['monitoreo-vista-aviso'].hidden,true);
  assert.equal(ctx.state.monitoreoProyectoId,4);
});

test('si se va de la pantalla antes de que llegue la respuesta, no la dibuja',async()=>{
  let soltar; const pendiente=new Promise(r=>{soltar=r;});
  const {ctx,card}=entorno({api:()=>pendiente});
  const carga=ctx.cargarVistaMonitoreo();
  ctx.state.vista='conexiones';
  soltar(DATOS); await carga;
  assert.equal(card.style.display,'none'); assert.equal(ctx.state.monitoreoProyectoId,undefined);
});

test('si no carga, lo dice en la pantalla',async()=>{
  const {ctx,els}=entorno({api:async()=>{throw Error('sin red');}});
  await ctx.cargarVistaMonitoreo();
  assert.equal(els['monitoreo-vista-aviso'].hidden,false);
  assert.match(els['monitoreo-vista-aviso-texto'].textContent,/No se pudo cargar Monitoreo: sin red/);
});

test('en la vista docente la tarjeta vuelve al panel docente, con su desplegable',()=>{
  const {ctx,card,admin}=entorno({vista:'proyecto-ia',incubadoraVista:'docente'});
  card.clases.add('monitoreo-pantalla');
  ctx.renderMonitoreo({...DATOS,puede_registrar:false});
  assert.equal(card.parentElement,admin); assert.ok(!card.clases.has('monitoreo-pantalla'));
  assert.equal(card.querySelector().textContent,'Gov4Action Monitoreo · Boletín · modo prueba');
});

test('en «Mi proyecto» no hay Monitoreo que cargar ni que dibujar',async()=>{
  const {ctx,card,llamadas}=entorno({vista:'proyecto-ia',incubadoraVista:'personal'});
  ctx.state.proyectoIA={id:7};
  assert.equal(ctx.proyectoMonitoreoActual(),null);
  ctx.configurarEspacioIncubadora();
  assert.equal(llamadas.api.length,0);
  await ctx.cargarMonitoreo(7);  // una respuesta que llega tarde no se dibuja: ya no es el proyecto «actual»
  assert.equal(card.style.display,'none');
});

test('configurar la Incubadora mientras se ve la pantalla de Monitoreo no le pisa la carga',async()=>{
  const {ctx,llamadas}=entorno({rol:'admin',vista:'monitoreo'});
  ctx.configurarEspacioIncubadora('docente');
  assert.equal(llamadas.api.length,0);
  const otro=entorno({rol:'admin',vista:'proyecto-ia'});
  otro.ctx.state.proyectoIASeleccionado=9;
  otro.ctx.configurarEspacioIncubadora('docente');
  await new Promise(r=>setImmediate(r));
  assert.equal(JSON.stringify(otro.llamadas.api),JSON.stringify(['/monitoreo/proyecto/9']));
});

// Tras la revisión de la 0.10.77.
test('registrar desde la pantalla usa el proyecto de quien entra y deja la tarjeta en su lugar',async()=>{
  const {ctx,card,cuerpo,llamadas}=entorno({api:async(url)=>url==='/monitoreo/mio'?DATOS:{...DATOS,registros:[{id:1}]}});
  await ctx.cargarVistaMonitoreo();
  const campos={'monitoreo-tipo':{value:'avance'},'monitoreo-titulo':{value:'Probé'},'monitoreo-contenido':{value:'Anduvo'},
    'monitoreo-valor-indicador':{value:''}};
  const original=ctx.document.getElementById; ctx.document.getElementById=id=>campos[id]||original(id);
  await ctx.crearRegistroMonitoreo({preventDefault(){}});
  assert.equal(JSON.stringify(llamadas.api),JSON.stringify(['/monitoreo/mio','/monitoreo/proyecto/7']));
  assert.equal(card.parentElement,cuerpo); assert.equal(card.style.display,'block');
});

test('cambiar el estado desde la pantalla recarga la pantalla; si falla, el error queda a la vista',async()=>{
  let falla=false;
  const {ctx,els,llamadas}=entorno({api:async(url)=>{if(falla&&url==='/monitoreo/mio')throw Error('sin red');return DATOS;}});
  await ctx.cargarVistaMonitoreo();
  falla=true;
  await ctx.cambiarEstadoRegistroMonitoreo(1,'resuelto');
  await new Promise(r=>setImmediate(r));
  assert.equal(JSON.stringify(llamadas.api),JSON.stringify(['/monitoreo/mio','/monitoreo/registros/1','/monitoreo/mio']));
  assert.equal(els['monitoreo-vista-aviso'].hidden,false);
  assert.match(els['monitoreo-vista-aviso-texto'].textContent,/No se pudo cargar Monitoreo: sin red/);
});

test('si otra carga dibuja la tarjeta, el «Cargando…» de la pantalla no queda pegado',async()=>{
  let soltar; const pendiente=new Promise(r=>{soltar=r;});
  const {ctx,els}=entorno({api:(url)=>url==='/monitoreo/mio'?pendiente:DATOS});
  ctx.state.monitoreoProyectoId=7;
  const carga=ctx.cargarVistaMonitoreo();          // «Cargando…» a la vista
  await ctx.cargarMonitoreo(7);                     // otra carga (después de un cambio de estado) gana la carrera
  assert.equal(els['monitoreo-vista-aviso'].hidden,true);
  soltar(DATOS); await carga;
  assert.equal(els['monitoreo-vista-aviso'].hidden,true);
});

test('sin proyecto en cartera, el aviso es neutro: no supone un ganador en el grupo',async()=>{
  const {ctx,els}=entorno({api:async()=>({proyecto_id:null,modo:'cartera'})});
  await ctx.cargarVistaMonitoreo();
  assert.match(els['monitoreo-vista-aviso-texto'].textContent,/un proyecto elegido[\s\S]*Todavía no empezaste/);
  assert.doesNotMatch(els['monitoreo-vista-aviso-texto'].textContent,/ganador/);
});

test('un proyecto sin título se nombra como tal en la pantalla',async()=>{
  const {ctx,card}=entorno({api:async()=>({...DATOS,proyecto_titulo:'Proyecto'})});
  await ctx.cargarVistaMonitoreo();
  assert.equal(card.querySelector().textContent,'Tu proyecto, todavía sin título · modo prueba');
});

test('el botón del aviso lleva a la cuenta administradora a «Supervisión docente»',()=>{
  const {ctx}=entorno({rol:'admin',vista:'proyecto-ia',incubadoraVista:'personal'});
  ctx.irDesdeAvisoMonitoreo();
  assert.equal(ctx.state.incubadoraVista,'docente');
  const alumno=entorno({vista:'proyecto-ia',incubadoraVista:'personal'});
  alumno.ctx.irDesdeAvisoMonitoreo();
  assert.equal(alumno.ctx.state.incubadoraVista,'personal');
});

test('«Mi proyecto» ya no carga Monitoreo',()=>{
  const cuerpo=trozo('async function cargarProyectoIA(','async function guardarProyectoIA(');
  assert.doesNotMatch(cuerpo,/cargarMonitoreo\(/);
});

test('en Inicio, el botón del Eje 4 es el de Monitoreo y en cartera sin proyecto ganador se oculta',()=>{
  const ctx=vm.createContext({escapeHtml:s=>String(s)});
  vm.runInContext(trozo('const RECORRIDOS = {','let estadoRecorridos'),ctx);
  const pedido=[]; const boton={hidden:false};
  const el={innerHTML:'',closest:()=>({querySelector:(sel)=>{pedido.push(sel);return boton;}})};
  ctx.renderRuta(el,'monitoreo',{monitoreo:{modo:'cartera',hechos:[]}});
  assert.equal(pedido[0],'[data-nav-target="monitoreo"]'); assert.equal(boton.hidden,true);
  ctx.renderRuta(el,'monitoreo',{monitoreo:{modo:'prueba',hechos:[]}});
  assert.equal(boton.hidden,false);
  ctx.renderRuta(el,'monitoreo',{monitoreo:{modo:'cartera',ganador:true,hechos:['cartera']}});
  assert.equal(boton.hidden,false);
});
