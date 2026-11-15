const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {evaluate,cleanAnswers,questions,skills}=require('../static/formacion-assets/autoevaluacion.js');
test('una respuesta no se confunde con una habilidad completa',()=>{
 const r=evaluate({0:5});assert.equal(r.answered,1);assert.equal(r.complete,false);assert.equal(r.axes[0].score,null);assert.deepEqual(r.priorities,[]);
});
test('rechaza valores inválidos, índices extra y datos corruptos',()=>{
 assert.deepEqual(cleanAnswers({0:'5',1:0,2:6,3:2.5,18:4}),{});
 for(const value of [null,[],false,'corrupto'])assert.deepEqual(cleanAnswers(value),{});
});
test('promedia los tres ítems y orienta hacia las dos habilidades de menor percepción',()=>{
 const answers=Object.fromEntries(questions.map((q,i)=>[i,q.skill==='evaluacion'?2:q.skill==='responsable'?1:5]));
 const r=evaluate(answers);assert.equal(r.complete,true);assert.equal(r.answered,18);
 assert.deepEqual(r.priorities.map(a=>a.id),['responsable','evaluacion']);assert.equal(r.axes[3].score,2);
 assert.equal(evaluate({}).answered,0);assert.deepEqual(evaluate({}).priorities,[]);
});
test('la evaluación cubre seis habilidades con tres ítems cada una',()=>{
 assert.equal(skills.length,6);assert.equal(questions.length,18);
 for(const skill of skills)assert.equal(questions.filter(q=>q.skill===skill.id).length,3);
});
test('los resultados no salen del navegador ni acceden al grupo de origen',()=>{
 const code=fs.readFileSync('static/formacion-assets/autoevaluacion.js','utf8');
 assert.doesNotMatch(code,/fetch\s*\(|XMLHttpRequest|sendBeacon|\/test\/submit|\/test\/global|localStorage/);
 assert.match(code,/sessionStorage/);
});
test('el mapa conserva referencias válidas y cinco ejes',()=>{
 const graph=JSON.parse(fs.readFileSync('static/formacion-assets/knowledge-map.json','utf8'));
 const ids=new Set(graph.nodes.map(n=>n.id));assert.equal(ids.size,graph.nodes.length);assert.ok(ids.has(graph.centralNodeId));
 assert.equal(graph.nodes.filter(n=>n.parentId===graph.centralNodeId).length,5);
 for(const n of graph.nodes){if(n.parentId)assert.ok(ids.has(n.parentId),n.id);for(const id of n.relatedNodeIds||[])assert.ok(ids.has(id),id);}
 new vm.Script(fs.readFileSync('static/formacion-assets/mapa.js','utf8'));
});
