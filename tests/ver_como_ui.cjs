// 0.10.74: «ver como»: aviso fijo con botón para salir, recarga al vencer, escrituras marcadas, y nada se abre solo.
const {test}=require('node:test'); const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const app=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const trozo=(desde,hasta)=>app.slice(app.indexOf(desde),app.indexOf(hasta));

function entorno({rol='admin',estado={activo:false},hash='#/inicio'}={}){
  const llamadas={api:[],vistas:[],recargas:0,temporizadores:[],clases:{},variables:{},barra:[]};
  const insertados=[];
  const body={prepend(el){insertados.push(el);},classList:{toggle(c,v){llamadas.clases[c]=v;}}};
  const pastilla={after(el){llamadas.barra.push(el);}};
  const ctx=vm.createContext({
    state:{currentUser:{rol}},
    window:{location:{hash,href:'',reload(){llamadas.recargas++;}}},
    document:{body,documentElement:{style:{setProperty(k,v){llamadas.variables[k]=v;}}},
      getElementById:id=>id==='ver-como-salir'?{addEventListener(){}}:id==='usuario-actual'?pastilla:id==='btn-ver-como-barra'?(llamadas.barra[0]||null):null,
      createElement:()=>({setAttribute(){},addEventListener(){},innerHTML:'',id:'',className:'',offsetHeight:52})},
    apiFetch:async(ruta,op={})=>{llamadas.api.push([ruta,op.method||'GET',op.body]); return ruta==='/admin/ver-como'&&!op.method?estado:{ok:true};},
    escapeHtml:s=>String(s).replace(/</g,'&lt;'),toast(){},Date,Math,Number,Boolean,Map,
    normalizarBusqueda:t=>t.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase(),
    contar:(n,s,p)=>`${n} ${n===1?s:p}`,
    setTimeout:(fn,ms)=>llamadas.temporizadores.push(ms),
    mostrarVista:(n,u)=>llamadas.vistas.push([n,u]),
    abrirDetalle:async()=>{},configurarEspacioIncubadora(){},cargarProyectoIADetalle:async()=>{},
  });
  vm.runInContext(trozo('function cabecerasVerComo(','async function apiFetch('),ctx);
  vm.runInContext(trozo('async function cargarVerComo(','async function cargarAreas('),ctx);
  vm.runInContext(trozo('async function navegarPorUrl(','document.querySelectorAll("[data-nav-target]")'),ctx);
  return {ctx,llamadas,insertados};
}

test('con una vista activa aparece el aviso, el menú baja y se programa la recarga al vencer',async()=>{
  const vence=Date.now()+10*60*1000;
  const {ctx,insertados,llamadas}=entorno({estado:{activo:true,valida:true,vence_en:vence,usuario:{nombre:'Alumna <b>',grupo:'Grupo A · comisión 2'}}});
  await ctx.cargarVerComo();
  assert.equal(insertados.length,1);
  assert.match(insertados[0].innerHTML,/Estás viendo Gov4Action como Alumna &lt;b>/);
  assert.match(insertados[0].innerHTML,/Grupo A · comisión 2/);
  assert.match(insertados[0].innerHTML,/Sólo lectura: nada de lo que hagas se guarda\./);
  assert.match(insertados[0].innerHTML,/id="ver-como-salir"/);
  assert.equal(llamadas.clases['ver-como'],true);
  assert.equal(llamadas.variables['--alto-ver-como'],'52px');
  assert.equal(llamadas.temporizadores.length,1);
  assert.ok(Math.abs(llamadas.temporizadores[0]-(10*60*1000+1000))<5000);
  assert.equal(JSON.stringify(ctx.cabecerasVerComo()),JSON.stringify({'X-Ver-Como':'1'}));  // las escrituras van marcadas
});

test('si la vista ya no es válida, el aviso lo dice y ofrece salir',async()=>{
  const {ctx,insertados}=entorno({estado:{activo:true,valida:false,usuario:null}});
  await ctx.cargarVerComo();
  assert.match(insertados[0].innerHTML,/ya no es válida/);
  assert.match(insertados[0].innerHTML,/id="ver-como-salir"/);
  assert.doesNotMatch(insertados[0].innerHTML,/Estás viendo Gov4Action como/);
});

test('sin vista activa no aparece nada ni se marcan los pedidos',async()=>{
  const {ctx,insertados,llamadas}=entorno();
  await ctx.cargarVerComo();
  assert.equal(insertados.length,0); assert.equal(ctx.state.verComo,null);
  assert.equal(llamadas.clases['ver-como'],false);
  assert.equal(JSON.stringify(ctx.cabecerasVerComo()),'{}');
});

test('un enlace #/ver-como/<cuenta> no abre la vista solo',async()=>{
  const {ctx,llamadas}=entorno({hash:'#/ver-como/57'});
  await ctx.navegarPorUrl();
  assert.equal(llamadas.api.length,0);
  assert.deepEqual(llamadas.vistas,[['inicio',false]]);
});

test('abrir la vista pide la cuenta y recarga; salir borra la cookie y recarga',async()=>{
  const {ctx,llamadas}=entorno();
  await ctx.iniciarVerComo('57');
  await ctx.salirVerComo();
  assert.deepEqual(llamadas.api,[['/admin/ver-como','POST',JSON.stringify({usuario_id:57})],['/admin/ver-como/salir','POST',undefined]]);
  assert.equal(llamadas.recargas,2);
});

// 0.10.75: el botón «Ver como» de la barra y la lista de participantes
test('la cuenta administradora tiene el botón «Ver como» en la barra; un participante y la vista activa, no',async()=>{
  const admin=entorno();
  await admin.ctx.cargarVerComo();
  assert.equal(admin.llamadas.barra.length,1);
  assert.equal(admin.llamadas.barra[0].textContent,'Ver como');
  admin.ctx.montarBotonVerComo();  // otra carga no lo duplica
  assert.equal(admin.llamadas.barra.length,1);
  const alumna=entorno({rol:'analista'});
  await alumna.ctx.cargarVerComo();
  assert.equal(alumna.llamadas.barra.length,0);
  const enVista=entorno({estado:{activo:true,valida:true,usuario:{nombre:'Alumna'}}});
  await enVista.ctx.cargarVerComo();
  assert.equal(enVista.llamadas.barra.length,0);
});

test('la lista agrupa por comisión, muestra a quien no tiene proyecto, escapa los nombres y filtra',()=>{
  const {ctx}=entorno();
  const cuentas=[
    {id:3,nombre:'Zoe Sin Proyecto',email:'sp@t',grupo:'Grupo A · comisión 2',activo:true,proyecto:null},
    {id:2,nombre:'Alumna <b>',email:'alumna@t',grupo:'Grupo A · comisión 2',activo:true,proyecto:{id:60,titulo:'Búsqueda de dictámenes'}},
    {id:6,nombre:'Integrante',email:'eq@t',grupo:'Grupo A · comisión 2',activo:true,proyecto:{id:60,titulo:'Búsqueda de dictámenes',en_equipo:true}},
    {id:4,nombre:'Original',email:'or@t',grupo:null,activo:false,proyecto:null},
    {id:5,nombre:'Grupo B Uno',email:'h@t',grupo:'Grupo B',activo:true,proyecto:null},
  ];
  const todo=ctx.listaVerComoHtml(cuentas,'');
  assert.match(todo,/Grupo A · comisión 2 · 3 personas/);
  assert.match(todo,/Grupo A · comisión 1 \(grupo original\) · 1 persona/);
  assert.ok(todo.indexOf('comisión 1')<todo.indexOf('comisión 2') && todo.indexOf('comisión 2')<todo.indexOf('Grupo B'));
  assert.ok(todo.indexOf('data-ver-como-id="2"')<todo.indexOf('data-ver-como-id="3"'));  // por nombre, no por id
  assert.match(todo,/Sin proyecto todavía/);
  assert.match(todo,/ · en equipo/);
  assert.match(todo,/cuenta inactiva/);
  assert.match(todo,/Alumna &lt;b>/);
  const filtrada=ctx.listaVerComoHtml(cuentas,'dictamenes');  // sin tilde también encuentra
  assert.match(filtrada,/data-ver-como-id="2"/);
  assert.doesNotMatch(filtrada,/data-ver-como-id="5"/);
  const sinProyecto=ctx.listaVerComoHtml(cuentas,'sin proyecto');  // también por los rótulos que se ven
  assert.match(sinProyecto,/data-ver-como-id="5"/);
  assert.doesNotMatch(sinProyecto,/data-ver-como-id="2"/);
  assert.match(ctx.listaVerComoHtml(cuentas,'inactiva'),/data-ver-como-id="4"/);
  assert.match(ctx.listaVerComoHtml(cuentas,'nadie así'),/No hay participantes que coincidan/);
});

test('la vista arranca por Inicio',async()=>{
  const {ctx}=entorno();
  await ctx.iniciarVerComo('3');
  assert.equal(ctx.window.location.href,'/#/inicio');
});
