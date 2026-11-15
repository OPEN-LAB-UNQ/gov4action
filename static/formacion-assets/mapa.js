const mapStorage = {getItem(key){try{const value=localStorage.getItem(key);if(key.endsWith('_centered'))return value;if(value)JSON.parse(value);return value;}catch(_){return null;}},setItem(key,value){try{localStorage.setItem(key,value);}catch(_){}}};

        const svg = document.getElementById("graph");
        const viewport = document.getElementById("viewport");
        const linksLayer = document.getElementById("links");
        const nodesLayer = document.getElementById("nodes");
        const stateKey = "gov4action_mapa_v1";

        let graph = null;
        let nodes = [];
        let nodesById = new Map();
        let selectedId = null;
        let expanded = new Set();
        let history = [];
        let historyIndex = -1;
        let transform = { x: 0, y: 0, k: 1 };
        let isDragging = false;
        let dragStart = null;
        let nodeDrag = null;
        let suppressClick = false;
        let originalPositions = {};
        let renderQueued = false;
        let simulationFrame = null;
        let simulationAlpha = 0;
        let liveLayout = false;
        let rearmCount = 0;

        const categoryColors = {
            central: "#22d3ee",
            metodo: "#34d399",
            problema: "#f59e0b",
            arquitectura: "#60a5fa",
            criterio: "#a78bfa",
            memoria: "#2dd4bf",
            datos: "#38bdf8",
            uso: "#fb7185",
            tecnologia: "#c084fc",
            gobernanza: "#f97316",
            agentes: "#4ade80",
            sistema: "#facc15",
            mejora: "#22c55e",
            cierre: "#e5e7eb"
        };

        function escapeHtml(value) {
            return String(value || "").replace(/[&<>"']/g, (char) => ({
                "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
            }[char]));
        }

        function nodeRef(node) {
            if (!node) return "";
            return `[${node.displayNumber || "?"}] ${node.title}`;
        }

        function mainNodes() {
            return nodes
                .filter((node) => node.parentId === graph.centralNodeId)
                .sort((a, b) => String(a.displayNumber).localeCompare(String(b.displayNumber), undefined, { numeric: true }));
        }

        function childNodes(parentId) {
            return getChildren(parentId)
                .sort((a, b) => String(a.displayNumber).localeCompare(String(b.displayNumber), undefined, { numeric: true }));
        }

        function routeNodes() {
            const central = nodesById.get(graph.centralNodeId);
            return [central, ...mainNodes()].filter(Boolean);
        }

        function routeAnchorId(id) {
            let node = nodesById.get(id);
            while (node && node.parentId && node.parentId !== graph.centralNodeId) {
                node = nodesById.get(node.parentId);
            }
            return node?.id || graph.centralNodeId;
        }

        function routeIndexForSelected() {
            const route = routeNodes();
            const exactIndex = route.findIndex((node) => node.id === selectedId);
            if (exactIndex >= 0) return exactIndex;
            const anchorId = routeAnchorId(selectedId);
            return Math.max(0, route.findIndex((node) => node.id === anchorId));
        }

        function navigateRoute(direction) {
            const current = nodesById.get(selectedId);
            if (current && current.parentId && current.parentId !== graph.centralNodeId) {
                const siblings = childNodes(current.parentId);
                const idx = siblings.findIndex((n) => n.id === selectedId);
                if (idx >= 0) {
                    const nextIdx = Math.max(0, Math.min(siblings.length - 1, idx + direction));
                    if (nextIdx !== idx) navigateToNode(siblings[nextIdx].id, { scale: 1.05 });
                    return;
                }
            }
            const route = routeNodes();
            if (!route.length) return;
            const currentIndex = routeIndexForSelected();
            const nextIndex = Math.max(0, Math.min(route.length - 1, currentIndex + direction));
            if (nextIndex === currentIndex && route[nextIndex]?.id === routeAnchorId(selectedId)) return;
            navigateToNode(route[nextIndex].id, { scale: nextIndex === 0 ? 0.78 : 0.88 });
        }

        function navigateToNode(id, options = {}) {
            const node = nodesById.get(id);
            if (!node) return;
            if (activeSurpriseIds.size && !activeSurpriseIds.has(id)) {
                closeSurprise();
            }
            expandAncestors(id);
            selectNode(id, options.pushHistory !== false);
            centerNode(id, options.scale);
            if (window.matchMedia("(max-width: 980px)").matches) {
                setPanelCollapsed(false);
            }
            document.getElementById("indexModal")?.classList.remove("open");
            document.getElementById("results")?.classList.remove("open");
        }

        function loadState() {
            try {
                const saved = JSON.parse(mapStorage.getItem(stateKey) || "{}");
                if (saved.expanded) expanded = new Set(saved.expanded);
                if (saved.history) history = saved.history;
                if (Number.isInteger(saved.historyIndex)) historyIndex = saved.historyIndex;
                if (saved.selectedId) selectedId = saved.selectedId;
                if (saved.transform) transform = saved.transform;
                if (saved.nodePositions) {
                    Object.entries(saved.nodePositions).forEach(([id, position]) => {
                        const node = nodesById.get(id);
                        if (node && Number.isFinite(position.x) && Number.isFinite(position.y)) {
                            node.initialPosition = { x: position.x, y: position.y };
                        }
                    });
                }
            } catch (error) {}
        }

        function currentNodePositions() {
            return Object.fromEntries(nodes.map((node) => [
                node.id,
                { x: Math.round(node.initialPosition.x), y: Math.round(node.initialPosition.y) }
            ]));
        }

        function saveState() {
            mapStorage.setItem(stateKey, JSON.stringify({
                expanded: [...expanded],
                history,
                historyIndex,
                selectedId,
                transform,
                nodePositions: currentNodePositions(),
                panelCollapsed: document.body.classList.contains("panel-collapsed"),
                panelFull: document.body.classList.contains("panel-full")
            }));
        }

        function isVisible(node) {
            if (!node.parentId) return true;
            if (node.parentId === graph.centralNodeId) return true;
            return expanded.has(node.parentId) && isVisible(nodesById.get(node.parentId));
        }

        function visibleNodes() {
            return nodes.filter(isVisible);
        }

        function getChildren(id) {
            return nodes.filter((node) => node.parentId === id);
        }

        function hasChildren(id) {
            return getChildren(id).length > 0;
        }

        function branchFocusIds() {
            if (activeSurpriseIds.size) return new Set(activeSurpriseIds);
            if (!selectedId) return new Set(nodes.map((node) => node.id));
            const selected = nodesById.get(selectedId);
            if (!selected) return new Set();

            const ids = new Set([selected.id]);
            if (selected.parentId) ids.add(selected.parentId);
            getChildren(selected.id).forEach((child) => ids.add(child.id));

            let ancestor = selected.parentId ? nodesById.get(selected.parentId) : null;
            while (ancestor && ancestor.parentId) {
                ids.add(ancestor.parentId);
                ancestor = nodesById.get(ancestor.parentId);
            }
            return ids;
        }

        function isRelatedToSelected(node) {
            return branchFocusIds().has(node.id);
        }

        function isDirectNeighbor(node) {
            return branchFocusIds().has(node.id);
        }

        function applyTransform() {
            viewport.setAttribute("transform", `translate(${transform.x} ${transform.y}) scale(${transform.k})`);
            saveState();
        }

        function graphPointFromClient(clientX, clientY) {
            const rect = svg.getBoundingClientRect();
            return {
                x: (clientX - rect.left - transform.x) / transform.k,
                y: (clientY - rect.top - transform.y) / transform.k
            };
        }

        function centerNode(id, targetScale) {
            const node = nodesById.get(id);
            if (!node) return;
            const rect = svg.getBoundingClientRect();
            const nextScale = targetScale || Math.max(0.72, Math.min(1.25, transform.k));
            transform.k = nextScale;
            transform.x = rect.width / 2 - node.initialPosition.x * nextScale;
            transform.y = rect.height / 2 - node.initialPosition.y * nextScale;
            applyTransform();
        }

        function selectNode(id, pushHistory = true) {
            const node = nodesById.get(id);
            if (!node) return;
            selectedId = id;
            if (pushHistory) {
                history = history.slice(0, historyIndex + 1);
                history.push(id);
                historyIndex = history.length - 1;
            }
            renderPanel(node);
            renderGraph();
            renderHistory();
            renderMobileBrowser();
            saveState();
            syncHash(id);
        }

        function syncHash(id) {
            const target = "#" + id;
            if (window.location.hash !== target) {
                window.history.replaceState(null, "", target);
            }
        }

        function urlForNode(node) {
            if (!node) return window.location.href;
            return window.location.origin + window.location.pathname + "#" + node.id;
        }

        function openBranch(id) {
            if (!hasChildren(id)) return false;
            if (!expanded.has(id)) {
                expanded.add(id);
                spreadChildrenAround(id);
                renderGraph();
                renderPanel(nodesById.get(selectedId));
                renderMobileBrowser();
                runLayoutSimulation({ alpha: 0.72, continuous: liveLayout });
                saveState();
            }
            return true;
        }

        function setLevel(depth) {
            expanded = new Set([graph.centralNodeId]);
            if (depth >= 2) {
                mainNodes().forEach((node) => {
                    if (hasChildren(node.id)) {
                        expanded.add(node.id);
                        spreadChildrenAround(node.id);
                    }
                });
            }
            if (depth >= 3) {
                nodes.forEach((node) => {
                    if (node.parentId && node.parentId !== graph.centralNodeId && hasChildren(node.id)) {
                        expanded.add(node.id);
                        spreadChildrenAround(node.id);
                    }
                });
            }
            renderGraph();
            renderPanel(nodesById.get(selectedId));
            renderMobileBrowser();
            runLayoutSimulation({ alpha: 0.72, continuous: liveLayout });
            saveState();
        }

        const relationInsights={
"c1-cuatro-formas::c4-cuatro-formas":{label:"La forma de usar IA define su riesgo",explanation:"Automatizar, asistir, recomendar y decidir exigen controles y responsabilidades diferentes.",question:"¿Qué decisiones nunca deberían automatizarse por completo?"},
"c1-rol-agente::c5-supervision":{label:"El criterio humano necesita poder real",explanation:"Supervisar es poder cuestionar, corregir y detener el proceso, no solo mirar el resultado.",question:"¿Quién responde y quién puede intervenir cuando la IA se equivoca?"},
"c2-dato-evidencia::c3-riesgos-verificacion":{label:"Una respuesta plausible todavía no es evidencia",explanation:"Solo el contraste con fuentes, método y contexto permite usar una respuesta de IA para decidir.",question:"¿Qué verificación la convertiría en una respuesta confiable?"},
"c2-asistentes-agentes::c5-agentes":{label:"Más autonomía requiere más gobernanza",explanation:"Cuando la IA ejecuta pasos, también deben crecer el registro, los límites y las autorizaciones.",question:"¿Qué acción exigiría siempre aprobación humana?"},
"c2-autoaprendizaje::c4-incubadora":{label:"Aprender no es recibir la respuesta",explanation:"Una IA formativa puede guiar con preguntas y retroalimentación sin reemplazar el esfuerzo intelectual.",question:"¿Cómo comprobamos que hubo aprendizaje?"},
"c2-calidad-fuentes::c4-multilente":{label:"El análisis empieza en la calidad de la fuente",explanation:"Cruzar perspectivas no corrige datos deficientes: importan el origen, alcance y límites de cada insumo.",question:"¿Qué fuente faltante podría cambiar la interpretación?"},
"c3-registro::c5-transparencia":{label:"Registrar vuelve auditable el uso",explanation:"Guardar propósito, fuentes, versión, validación y responsable permite reconstruir una conclusión.",question:"¿Qué necesitaría otra persona para revisar esta decisión?"},
"c4-monitoreo::c5-condicion-detencion":{label:"Monitorear también es saber cuándo parar",explanation:"Un sistema responsable define alertas y condiciones para suspender, corregir o escalar.",question:"¿Qué evidencia obligaría a detener el sistema?"},
"c4-actividad::c5-actividad":{label:"De una buena idea a una propuesta firme",explanation:"La aplicación explica el valor; la gobernanza agrega responsables, controles, trazabilidad e indicadores.",question:"¿Qué falta para implementarla responsablemente?"}};
function relationKey(a,b){return[a,b].sort().join("::")}
const surpriseThreads=Object.entries(relationInsights).map(([key,i])=>({...i,ids:key.split("::")}));
let surpriseIndex=-1,surpriseStepIndex=0,activeSurpriseIds=new Set();
function showSurprise(){surpriseIndex=(surpriseIndex+1)%surpriseThreads.length;const t=surpriseThreads[surpriseIndex];activeSurpriseIds=new Set(t.ids);surpriseStepIndex=0;t.ids.forEach(id=>{const n=nodesById.get(id);if(!n||!n.parentId)return;expandAncestors(id);expanded.add(n.parentId);spreadChildrenAround(n.parentId)});runLayoutSimulation({alpha:.72,continuous:liveLayout});document.getElementById("surpriseBtn").classList.add("active");navigateToNode(t.ids[0],{scale:.72});renderMobileBrowser();updateSurpriseCaption(t,"CONEXIÓN SORPRESA",true)}
function surpriseStep(d){if(!activeSurpriseIds.size)return;const t=surpriseThreads[surpriseIndex];surpriseStepIndex=(surpriseStepIndex+d+t.ids.length)%t.ids.length;navigateToNode(t.ids[surpriseStepIndex],{scale:.72});updateSurpriseCaption(t,"CONEXIÓN SORPRESA",true)}
function closeSurprise(){activeSurpriseIds=new Set();document.getElementById("surpriseBtn").classList.remove("active");document.getElementById("surpriseCaption").classList.remove("show");renderGraph();saveState()}
function updateSurpriseCaption(t,k="RELACIÓN SUGERIDA",nav=false){const c=document.getElementById("surpriseCaption"),n=nav?nodesById.get(t.ids[surpriseStepIndex]):null;c.innerHTML='<div class="connection-kicker">'+escapeHtml(k)+'</div><div class="connection-title">'+escapeHtml(t.label)+'</div><div class="connection-copy">'+escapeHtml(t.explanation)+'</div><div class="connection-question">'+escapeHtml(t.question)+'</div><div class="connection-actions">'+(nav?'<button id="surprisePrevBtn">Anterior</button><button id="surpriseNextBtn">Siguiente concepto</button><span>'+escapeHtml(n?.title||"")+' · '+(surpriseStepIndex+1)+'/'+t.ids.length+'</span>':'')+'<button class="surprise-close" id="surpriseCloseBtn">Cerrar</button></div>';c.classList.add("show");document.getElementById("surprisePrevBtn")?.addEventListener("click",e=>{e.stopPropagation();surpriseStep(-1)});document.getElementById("surpriseNextBtn")?.addEventListener("click",e=>{e.stopPropagation();surpriseStep(1)});document.getElementById("surpriseCloseBtn").addEventListener("click",e=>{e.stopPropagation();closeSurprise()})}
function showRelationInsight(r){const i=relationInsights[relationKey(r.source.id,r.target.id)];if(!i)return;activeSurpriseIds=new Set([r.source.id,r.target.id]);renderGraph();updateSurpriseCaption(i,"RELACIÓN SUGERIDA",false)}

        let relationsOn = false;

        function toggleRelations() {
            relationsOn = !relationsOn;
            document.body.classList.toggle("relations-on", relationsOn);
            document.getElementById("relationsBtn").classList.toggle("active", relationsOn);
            if (relationsOn) {
                const linkedIds = new Set();
                nodes.forEach((node) => {
                    (node.suggestedNodeIds || []).forEach((id) => {
                        if (!relationInsights[relationKey(node.id, id)]) return;
                        linkedIds.add(node.id);
                        linkedIds.add(id);
                    });
                });
                linkedIds.forEach((id) => {
                    const node = nodesById.get(id);
                    if (!node || !node.parentId) return;
                    expandAncestors(id);
                    expanded.add(node.parentId);
                    spreadChildrenAround(node.parentId);
                });
                runLayoutSimulation({ alpha: 0.72, continuous: liveLayout });
            }
            renderGraph();
            renderMobileBrowser();
            saveState();
        }

        function activateNode(id) {
            const node = nodesById.get(id);
            if (!node) return;
            const canExpand = hasChildren(id);
            selectNode(id);
            if (id === graph.centralNodeId) {
                expanded.add(id);
            } else if (canExpand) {
                openBranch(id);
            }
            centerNode(id, window.matchMedia("(max-width: 980px)").matches ? 0.56 : 0.76);
        }

        function expandAncestors(id) {
            let node = nodesById.get(id);
            while (node && node.parentId) {
                expanded.add(node.parentId);
                node = nodesById.get(node.parentId);
            }
        }

        function toggleExpand(id) {
            if (!hasChildren(id)) return;
            if (expanded.has(id)) {
                const descendants = collectDescendants(id);
                descendants.forEach((descendantId) => expanded.delete(descendantId));
                expanded.delete(id);
            } else {
                expanded.add(id);
                spreadChildrenAround(id);
            }
            renderGraph();
            renderPanel(nodesById.get(selectedId));
            renderMobileBrowser();
            runLayoutSimulation({ alpha: 0.72, continuous: liveLayout });
            saveState();
        }

        function collectDescendants(id) {
            const ids = [];
            getChildren(id).forEach((child) => {
                ids.push(child.id);
                ids.push(...collectDescendants(child.id));
            });
            return ids;
        }

        function closeBranch(id) {
            collectDescendants(id).forEach((descendantId) => expanded.delete(descendantId));
            expanded.delete(id);
            renderGraph();
            renderMobileBrowser();
            runLayoutSimulation({ alpha: 0.45, continuous: liveLayout });
            saveState();
        }

        function spreadChildrenAround(id) {
            const parent = nodesById.get(id);
            const children = getChildren(id).filter((child) => isVisible(child));
            if (!parent || !children.length) return;
            const mobile = window.matchMedia("(max-width: 980px)").matches;
            const count = children.length;
            const fullRing = count > 6;
            const baseRadius = parent.id === graph.centralNodeId ? (mobile ? 430 : 560) : (mobile ? 300 : 430);
            const radius = baseRadius + Math.max(0, count - 4) * (mobile ? 30 : 44);
            const parentAngle = Math.atan2(parent.initialPosition.y, parent.initialPosition.x);
            const startAngle = fullRing ? -Math.PI / 2 : parentAngle - Math.PI / 2;
            const spread = fullRing ? Math.PI * 2 : Math.min(Math.PI * 1.35, Math.PI * 0.62 + count * 0.24);
            children.forEach((child, index) => {
                const angle = fullRing
                    ? startAngle + (index / count) * Math.PI * 2
                    : startAngle + ((index + 1) / (count + 1)) * spread;
                const lane = fullRing && index % 2 ? (mobile ? 28 : 52) : 0;
                child.initialPosition = {
                    x: parent.initialPosition.x + Math.cos(angle) * (radius + lane),
                    y: parent.initialPosition.y + Math.sin(angle) * (radius + lane)
                };
            });
        }

        function linkPath(source, target) {
            const sx = source.initialPosition.x;
            const sy = source.initialPosition.y;
            const tx = target.initialPosition.x;
            const ty = target.initialPosition.y;
            const mx = (sx + tx) / 2;
            const my = (sy + ty) / 2;
            const dx = tx - sx;
            const dy = ty - sy;
            const curve = 0.12;
            return `M ${sx} ${sy} Q ${mx - dy * curve} ${my + dx * curve} ${tx} ${ty}`;
        }

        function createSvg(tag, attrs = {}) {
            const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
            Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
            return el;
        }

        function visibleRelations() {
            const visible = visibleNodes();
            const visibleIds = new Set(visible.map((node) => node.id));
            const relations = [];
            const relationKeys = new Set();

            function pushRelation(type, source, target) {
                if (!source || !target) return;
                const pair = [source.id, target.id].sort().join("::");
                const key = `${type}:${pair}`;
                if (relationKeys.has(key)) return;
                relationKeys.add(key);
                relations.push({ type, source, target });
            }

            visible.forEach((node) => {
                if (node.parentId && visibleIds.has(node.parentId)) {
                    pushRelation("hierarchy", nodesById.get(node.parentId), node);
                }
                node.relatedNodeIds.forEach((relatedId) => {
                    const related = nodesById.get(relatedId);
                    if (!related || !visibleIds.has(relatedId)) return;
                    pushRelation("related", node, related);
                });
                (node.suggestedNodeIds || []).forEach((suggestedId) => {
                    const suggested = nodesById.get(suggestedId);
                    if (!suggested || !visibleIds.has(suggestedId) || !relationInsights[relationKey(node.id, suggestedId)]) return;
                    pushRelation("suggested", node, suggested);
                });
            });
            if (activeSurpriseIds.size) {
                const ids = [...activeSurpriseIds].filter((id) => visibleIds.has(id));
                for (let i = 0; i < ids.length; i++) {
                    for (let j = i + 1; j < ids.length; j++) {
                        pushRelation("surprise", nodesById.get(ids[i]), nodesById.get(ids[j]));
                    }
                }
            }
            return relations;
        }

        function nodeRadius(node) {
            if (node.id === graph.centralNodeId) return 82;
            if (node.id === selectedId) return 70;
            if (node.featured) return 54;
            return 42;
        }

        function scheduleRenderGraph() {
            if (renderQueued) return;
            renderQueued = true;
            requestAnimationFrame(() => {
                renderQueued = false;
                renderGraph();
            });
        }

        function renderGraph() {
            if (!graph) return;
            const visible = visibleNodes();
            const visibleIds = new Set(visible.map((node) => node.id));
            linksLayer.innerHTML = "";
            nodesLayer.innerHTML = "";

            visibleRelations().forEach((relation) => {
                const focusIds = branchFocusIds();
                const touchesSelected = focusIds.has(relation.source.id) && focusIds.has(relation.target.id);
                const path=createSvg("path",{class:"link "+relation.type+" "+(touchesSelected?"neighbor":""),d:linkPath(relation.source,relation.target),fill:"none"});
                if(relation.type==="suggested"&&relationInsights[relationKey(relation.source.id,relation.target.id)]){path.setAttribute("tabindex","0");path.setAttribute("role","button");path.addEventListener("click",e=>{e.stopPropagation();showRelationInsight(relation)});path.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();showRelationInsight(relation)}})}
                linksLayer.appendChild(path);
            });

            visible.forEach((node) => {
                const isSelected = node.id === selectedId;
                const isCentral = node.id === graph.centralNodeId;
                const radius = nodeRadius(node);
                const wrap = createSvg("g", {
                    class: `node-wrap ${isRelatedToSelected(node) ? "" : "dim"} ${isDirectNeighbor(node) ? "active-neighbor" : ""} ${activeSurpriseIds.has(node.id) ? "surprise-active" : ""}`,
                    transform: `translate(${node.initialPosition.x} ${node.initialPosition.y})`,
                    tabindex: "0",
                    role: "button",
                    "aria-label": node.title
                });
                const color = categoryColors[node.category] || "#94a3b8";
                wrap.appendChild(createSvg("circle", {
                    class: "node-halo",
                    r: radius + 6
                }));
                wrap.appendChild(createSvg("circle", {
                    class: "node-circle",
                    r: radius,
                    fill: isCentral ? "url(#nodeCentral)" : "url(#nodeDefault)",
                    stroke: isSelected ? "#ffffff" : color,
                    "stroke-width": isSelected ? 4 : 2.2
                }));
                wrap.appendChild(createSvg("circle", {
                    r: Math.max(8, radius - 8),
                    fill: "none",
                    stroke: color,
                    "stroke-opacity": isSelected ? 0.35 : 0.18,
                    "stroke-width": 10
                }));
                wrap.appendChild(createSvg("text", {
                    class: "node-number",
                    y: node.alias ? -10 : 4
                })).textContent = node.displayNumber || "";
                if (node.alias) {
                    const aliasWords = String(node.alias).split(/\s+/);
                    const aliasLines = wrapLines(aliasWords, isCentral ? 11 : 9).slice(0, 2);
                    aliasLines.forEach((line, index) => {
                        wrap.appendChild(createSvg("text", {
                            class: "node-alias",
                            y: 11 + index * 15
                        })).textContent = line;
                    });
                }

                const selected = nodesById.get(selectedId);
                const isMainNode = node.parentId === graph.centralNodeId;
                const isChildOfSelected = node.parentId === selectedId;
                const isParentOfSelected = selected?.parentId === node.id;
                const showTitle = isSelected || isCentral || isMainNode || isChildOfSelected || isParentOfSelected;
                if (showTitle) {
                    const words = node.title.split(" ");
                    const lines = wrapLines(words, isCentral ? 23 : isSelected ? 22 : 18).slice(0, isSelected ? 3 : 2);
                    lines.forEach((line, index) => {
                        wrap.appendChild(createSvg("text", {
                            class: "node-title-outside",
                            y: radius + 22 + index * 15,
                            "font-size": isCentral ? 17 : isSelected ? 15 : 12
                        })).textContent = line;
                    });
                }

                if (hasChildren(node.id)) {
                    const bx = radius * 0.58;
                    const by = -radius * 0.58;
                    wrap.appendChild(createSvg("circle", {
                        class: "expand-dot",
                        cx: bx,
                        cy: by,
                        r: isSelected ? 13 : 11
                    }));
                    wrap.appendChild(createSvg("text", {
                        class: "expand-dot-text",
                        x: bx,
                        y: by + 1
                    })).textContent = expanded.has(node.id) ? "-" : "+";
                }

                wrap.addEventListener("click", (event) => {
                    event.stopPropagation();
                    if (suppressClick) {
                        suppressClick = false;
                        return;
                    }
                    activateNode(node.id);
                });
                wrap.addEventListener("pointerdown", (event) => {
                    event.stopPropagation();
                    nodeDrag = {
                        id: node.id,
                        startClientX: event.clientX,
                        startClientY: event.clientY,
                        startX: node.initialPosition.x,
                        startY: node.initialPosition.y,
                        moved: false
                    };
                    svg.classList.add("dragging");
                    wrap.setPointerCapture?.(event.pointerId);
                });
                wrap.addEventListener("dblclick", (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    suppressClick = false;
                    navigateToNode(node.id, { scale: hasChildren(node.id) ? 0.82 : 1 });
                    centerNode(node.id);
                });
                nodesLayer.appendChild(wrap);
            });
        }

        function wrapLines(words, maxChars) {
            const lines = [];
            let current = "";
            words.forEach((word) => {
                const test = current ? `${current} ${word}` : word;
                if (test.length > maxChars && current) {
                    lines.push(current);
                    current = word;
                } else {
                    current = test;
                }
            });
            if (current) lines.push(current);
            return lines.slice(0, 4);
        }

        function renderPanel(node) {
            if (!node) return;
            const isCentralPanel = node.id === graph.centralNodeId;
            document.getElementById("nodeNumber").textContent = node.displayNumber || "?";
            const aliasEl = document.getElementById("nodeAlias");
            aliasEl.textContent = node.alias || "";
            aliasEl.style.display = node.alias ? "inline-flex" : "none";
            document.getElementById("nodeCategory").textContent = node.category;
            document.getElementById("nodeTitle").textContent = node.title;
            document.getElementById("nodeDesc").textContent = node.shortDescription;
            document.getElementById("panelCloseBranchBtn").disabled = !hasChildren(node.id);
            document.getElementById("panelPrevBtn").style.display = isCentralPanel ? "none" : "inline-flex";
            document.getElementById("panelCenterBtn").style.display = isCentralPanel ? "none" : "inline-flex";
            document.getElementById("panelCloseBranchBtn").style.display = isCentralPanel ? "none" : "inline-flex";
            document.getElementById("copyRefBtn").style.display = isCentralPanel ? "none" : "inline-flex";
            document.getElementById("panelNextBtn").textContent = isCentralPanel ? "Entrar al mapa →" : "Siguiente →";
            document.getElementById("panelSizeBtn").textContent = isCentralPanel ? "Ver ficha grande" : "Ampliar ficha";
            document.getElementById("exampleBtn").style.display = node.viajoBienExample ? "inline-flex" : "none";
            const exampleBox = document.getElementById("exampleBox");
            exampleBox.classList.remove("open");
            exampleBox.textContent = node.viajoBienExample || "";

            const html = (node.content || []).map((block) => {
                if (block.type === "quote") return `<div class="content-block"><blockquote class="quote">${escapeHtml(block.text)}</blockquote></div>`;
                if (block.type === "paragraph") return `<div class="content-block"><p>${escapeHtml(block.text)}</p></div>`;
                if (block.type === "list") {
                    return `<div class="content-block"><h3>${escapeHtml(block.title || "")}</h3><ul>${(block.items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>`;
                }
                if (block.type === "flow") {
                    const chips = (block.steps || []).map((step) => `<span class="flow-chip">${escapeHtml(step)}</span>`);
                    const chain = chips.join('<span class="flow-arrow">→</span>');
                    return `<div class="content-block"><div class="flow-chain">${chain}</div></div>`;
                }
                if (block.type === "converge") {
                    const inputs = (block.inputs || []).map((item) => `<span class="flow-chip">${escapeHtml(item)}</span>`).join("");
                    return `<div class="content-block"><div class="flow-converge"><div class="flow-inputs">${inputs}</div><span class="flow-arrow">→</span><span class="flow-output">${escapeHtml(block.output || "")}</span></div></div>`;
                }
                return "";
            }).join("");
            document.getElementById("nodeContent").innerHTML = html || `<div class="content-block"><p>${escapeHtml(node.shortDescription)}</p></div>`;
            const prompt = document.getElementById("promptQuestion");
            prompt.style.display = node.promptQuestion ? "block" : "none";
            prompt.textContent = node.promptQuestion ? `Pregunta disparadora: ${node.promptQuestion}` : "";
        }

        function updatePanelSizeButton() {
            const button = document.getElementById("panelSizeBtn");
            if (!button) return;
            const full = document.body.classList.contains("panel-full");
            button.textContent = full ? "Panel lateral" : "Ampliar ficha";
            button.classList.toggle("active", full);
        }

        function setPanelFull(full) {
            document.body.classList.toggle("panel-full", full);
            if (full) {
                document.body.classList.remove("panel-collapsed");
            }
            updatePanelSizeButton();
            setTimeout(() => centerNode(selectedId, full ? 0.34 : 0.78), 120);
            saveState();
        }

        function togglePanelSize() {
            setPanelFull(!document.body.classList.contains("panel-full"));
        }

        function setPanelCollapsed(collapsed) {
            document.body.classList.toggle("panel-collapsed", collapsed);
            if (collapsed) {
                document.body.classList.remove("panel-full");
            }
            updatePanelSizeButton();
            document.getElementById("togglePanelBtn").textContent = "Ver panel";
            document.getElementById("togglePanelBtn").setAttribute("aria-label", "Mostrar panel derecho");
            setTimeout(() => centerNode(selectedId), 120);
            saveState();
        }

        function togglePanel() {
            setPanelCollapsed(!document.body.classList.contains("panel-collapsed"));
        }

        function resetNodePositions() {
            stopLayoutSimulation();
            Object.entries(originalPositions).forEach(([id, position]) => {
                const node = nodesById.get(id);
                if (node) node.initialPosition = { x: position.x, y: position.y };
            });
            renderGraph();
            renderMobileBrowser();
            centerNode(selectedId);
            saveState();
        }

        function rearmGraph() {
            if (!graph) return;
            stopLayoutSimulation();
            const central = nodesById.get(graph.centralNodeId);
            const mains = mainNodes();
            if (!central) return;
            rearmCount += 1;

            expanded = new Set([graph.centralNodeId]);
            mains.forEach((node) => {
                if (hasChildren(node.id)) expanded.add(node.id);
            });

            central.initialPosition = { x: 0, y: 0 };
            const mobile = window.matchMedia("(max-width: 980px)").matches;
            const mode = rearmCount % 3;
            const ringRadius = mobile ? 460 : 760;
            const childRadius = mobile ? 215 : 330;
            const startAngle = -Math.PI / 2 + (Math.random() - 0.5) * 0.85 + rearmCount * 0.17;
            const turn = Math.PI * 2;
            const stretchX = mode === 1 ? 1.32 : mode === 2 ? 0.9 : 1.08;
            const stretchY = mode === 1 ? 0.9 : mode === 2 ? 1.3 : 1.06;

            mains.forEach((node, index) => {
                const progress = mains.length <= 1 ? 0 : index / mains.length;
                const angle = startAngle + progress * turn + (mode === 2 ? Math.sin(index * 0.9 + rearmCount) * 0.13 : 0);
                const spiral = mode === 1 ? (index - mains.length / 2) * (mobile ? 16 : 28) : 0;
                const wave = Math.sin(index * 1.7 + rearmCount * 0.8) * (mode === 0 ? 86 : 132);
                const branchOffset = mode === 2 ? Math.cos(index * 1.2 + rearmCount) * (mobile ? 128 : 210) : 0;
                const jitterX = (Math.random() - 0.5) * (mode === 0 ? 110 : 190);
                const jitterY = (Math.random() - 0.5) * (mode === 0 ? 110 : 190);
                const radius = ringRadius + wave + spiral;
                node.initialPosition = {
                    x: Math.cos(angle) * radius * stretchX + Math.cos(angle + Math.PI / 2) * branchOffset + jitterX,
                    y: Math.sin(angle) * radius * stretchY + Math.sin(angle + Math.PI / 2) * branchOffset + jitterY
                };

                const children = childNodes(node.id);
                const spread = Math.min(Math.PI * (mode === 2 ? 1.55 : 1.28), 0.72 + children.length * (mode === 2 ? 0.32 : 0.26));
                const base = angle - spread / 2 + (Math.random() - 0.5) * 0.3;
                children.forEach((child, childIndex) => {
                    const ratio = children.length <= 1 ? 0.5 : childIndex / (children.length - 1);
                    const childAngle = base + ratio * spread;
                    const childDepth = childRadius + (mode === 1 ? childIndex * (mobile ? 18 : 30) : 0) + Math.sin(childIndex + rearmCount) * 42;
                    const childJitterX = (Math.random() - 0.5) * (mode === 0 ? 78 : 135);
                    const childJitterY = (Math.random() - 0.5) * (mode === 0 ? 78 : 135);
                    child.initialPosition = {
                        x: node.initialPosition.x + Math.cos(childAngle) * childDepth + childJitterX,
                        y: node.initialPosition.y + Math.sin(childAngle) * childDepth + childJitterY
                    };
                });
            });

            selectedId = selectedId && nodesById.has(selectedId) ? selectedId : graph.centralNodeId;
            renderGraph();
            renderPanel(nodesById.get(selectedId));
            renderMobileBrowser();
            centerNode(graph.centralNodeId, window.matchMedia("(max-width: 980px)").matches ? 0.3 : 0.42);
            runLayoutSimulation({ alpha: 1.05, continuous: false });
            saveState();
        }

        function runLayoutSimulation(options = {}) {
            if (!graph) return;
            simulationAlpha = Math.max(simulationAlpha, options.alpha || 0.62);
            if (options.continuous !== undefined) liveLayout = options.continuous;
            document.getElementById("liveLayoutBtn")?.classList.toggle("active", liveLayout);
            if (simulationFrame) return;
            stepLayoutSimulation();
        }

        function stopLayoutSimulation() {
            liveLayout = false;
            simulationAlpha = 0;
            if (simulationFrame) cancelAnimationFrame(simulationFrame);
            simulationFrame = null;
            document.getElementById("liveLayoutBtn")?.classList.remove("active");
        }

        function toggleLiveLayout() {
            liveLayout = !liveLayout;
            if (liveLayout) {
                runLayoutSimulation({ alpha: 0.9, continuous: true });
            } else {
                stopLayoutSimulation();
                saveState();
            }
        }

        function stepLayoutSimulation() {
            simulationFrame = requestAnimationFrame(() => {
                simulationFrame = null;
                const visible = visibleNodes();
                const relations = visibleRelations();
                const mobile = window.matchMedia("(max-width: 980px)").matches;
                const centerStrength = mobile ? 0.002 : 0.0035;
                visible.forEach((node) => {
                    node.vx = node.vx || 0;
                    node.vy = node.vy || 0;
                    node.vx += (-node.initialPosition.x) * centerStrength * simulationAlpha;
                    node.vy += (-node.initialPosition.y) * centerStrength * simulationAlpha;
                });

                relations.forEach((relation) => {
                    const source = relation.source;
                    const target = relation.target;
                    const dx = target.initialPosition.x - source.initialPosition.x;
                    const dy = target.initialPosition.y - source.initialPosition.y;
                    const dist = Math.max(1, Math.hypot(dx, dy));
                    const desired = relation.type === "hierarchy" ? (mobile ? 235 : 340) : relation.type === "suggested" ? (mobile ? 360 : 520) : (mobile ? 315 : 455);
                    const strength = relation.type === "hierarchy" ? 0.014 : relation.type === "suggested" ? 0.0025 : 0.004;
                    const force = (dist - desired) * strength * simulationAlpha;
                    const fx = (dx / dist) * force;
                    const fy = (dy / dist) * force;
                    source.vx += fx;
                    source.vy += fy;
                    target.vx -= fx;
                    target.vy -= fy;
                });

                for (let i = 0; i < visible.length; i++) {
                    for (let j = i + 1; j < visible.length; j++) {
                        const a = visible[i];
                        const b = visible[j];
                        const dx = b.initialPosition.x - a.initialPosition.x;
                        const dy = b.initialPosition.y - a.initialPosition.y;
                        const dist = Math.max(1, Math.hypot(dx, dy));
                        const minDist = nodeRadius(a) + nodeRadius(b) + (mobile ? 72 : 118);
                        const charge = (mobile ? 5200 : 8800) / (dist * dist);
                        let force = charge;
                        if (dist < minDist) force += (minDist - dist) * 0.07;
                        force *= simulationAlpha;
                        const fx = (dx / dist) * force;
                        const fy = (dy / dist) * force;
                        a.vx -= fx;
                        a.vy -= fy;
                        b.vx += fx;
                        b.vy += fy;
                    }
                }

                visible.forEach((node) => {
                    if (nodeDrag?.id === node.id) return;
                    node.vx *= 0.78;
                    node.vy *= 0.78;
                    node.initialPosition.x += Math.max(-18, Math.min(18, node.vx));
                    node.initialPosition.y += Math.max(-18, Math.min(18, node.vy));
                });

                scheduleRenderGraph();
                simulationAlpha *= liveLayout ? 0.992 : 0.955;
                if (liveLayout || simulationAlpha > 0.018) {
                    stepLayoutSimulation();
                } else {
                    saveState();
                }
            });
        }

        function renderHistory() {
            const list = document.getElementById("historyList");
            if (!list) return;
            const last = history.slice(-7);
            list.innerHTML = "";
            last.forEach((id) => {
                const node = nodesById.get(id);
                if (!node) return;
                const chip = document.createElement("span");
                chip.className = "history-chip";
                chip.textContent = nodeRef(node);
                chip.addEventListener("click", () => {
                    navigateToNode(id);
                });
                list.appendChild(chip);
            });
        }

        function renderIndex() {
            const list = document.getElementById("indexList");
            if (!list || !graph) return;
            list.innerHTML = "";
            const central = nodesById.get(graph.centralNodeId);
            if (central) list.appendChild(indexButton(central, "top"));
            mainNodes().forEach((node) => {
                list.appendChild(indexButton(node, "top"));
                childNodes(node.id).forEach((child) => {
                    list.appendChild(indexButton(child, "child"));
                    childNodes(child.id).forEach((grandchild) => list.appendChild(indexButton(grandchild, "grandchild")));
                });
            });
        }

        function indexButton(node, depth) {
            const button = document.createElement("button");
            button.className = `index-item ${depth !== "top" ? depth : ""}`;
            button.innerHTML = `<span class="number-pill">${escapeHtml(node.displayNumber || "?")}</span>${node.alias ? `<span class="alias-pill">${escapeHtml(node.alias)}</span>` : ""}<span>${escapeHtml(node.title)}</span>`;
            button.addEventListener("click", () => navigateToNode(node.id, { scale: depth === "top" ? 0.88 : 1.05 }));
            return button;
        }

        function renderMobileBrowser() {
            const container = document.getElementById("mobileBrowser");
            if (!container || !graph) return;
            container.innerHTML = "";
            mainNodes().forEach((node) => {
                const section = document.createElement("div");
                section.className = `mobile-section ${expanded.has(node.id) ? "open" : ""}`;
                const main = document.createElement("button");
                main.className = "mobile-main";
                main.innerHTML = `<span class="number-pill">${escapeHtml(node.displayNumber)}</span>${node.alias ? `<span class="alias-pill">${escapeHtml(node.alias)}</span>` : ""}<span>${escapeHtml(node.title)}</span><b>${childNodes(node.id).length ? "＋" : ""}</b>`;
                main.addEventListener("click", () => {
                    if (childNodes(node.id).length) {
                        expanded.has(node.id) ? expanded.delete(node.id) : expanded.add(node.id);
                        renderMobileBrowser();
                    }
                    navigateToNode(node.id, { scale: 0.76 });
                });
                section.appendChild(main);
                const children = document.createElement("div");
                children.className = "mobile-children";
                childNodes(node.id).forEach((child) => {
                    const childButton = document.createElement("button");
                    childButton.className = "mobile-child";
                    childButton.innerHTML = `<span class="number-pill">${escapeHtml(child.displayNumber)}</span><span class="mobile-node-title">${escapeHtml(child.title)}</span>`;
                    childButton.addEventListener("click", () => navigateToNode(child.id, { scale: 0.95 }));
                    children.appendChild(childButton);
                    childNodes(child.id).forEach((grandchild) => {
                        const grandchildButton = document.createElement("button");
                        grandchildButton.className = "mobile-child grandchild";
                        grandchildButton.innerHTML = `<span class="number-pill">${escapeHtml(grandchild.displayNumber)}</span><span class="mobile-node-title">${escapeHtml(grandchild.title)}</span>`;
                        grandchildButton.addEventListener("click", () => navigateToNode(grandchild.id, { scale: 1.05 }));
                        children.appendChild(grandchildButton);
                    });
                });
                section.appendChild(children);
                container.appendChild(section);
            });
        }

        function search(query) {
            const results = document.getElementById("results");
            const value = query.trim().toLowerCase();
            if (!value) {
                results.classList.remove("open");
                results.innerHTML = "";
                return;
            }
            const matches = nodes.filter((node) => {
                const haystack = `${node.displayNumber || ""} ${node.alias || ""} ${node.title} ${node.shortDescription} ${(node.tags || []).join(" ")} ${node.promptQuestion || ""} ${node.viajoBienExample || ""} ${JSON.stringify(node.content)}`.toLowerCase();
                return haystack.includes(value);
            }).sort((a, b) => {
                const rank = (node) => {
                    if (String(node.displayNumber || "").toLowerCase() === value) return 0;
                    if (String(node.alias || "").toLowerCase() === value) return 1;
                    if (String(node.title || "").toLowerCase() === value) return 2;
                    if (String(node.title || "").toLowerCase().startsWith(value)) return 3;
                    return 9;
                };
                return rank(a) - rank(b) || String(a.displayNumber).localeCompare(String(b.displayNumber), undefined, { numeric: true });
            }).slice(0, 10);
            results.innerHTML = matches.map((node) => `
                <button class="result" data-id="${escapeHtml(node.id)}">
                    <span class="result-title"><span class="number-pill">${escapeHtml(node.displayNumber || "?")}</span>${node.alias ? `<span class="alias-pill">${escapeHtml(node.alias)}</span>` : ""}<b>${escapeHtml(node.title)}</b></span>
                    <small>${escapeHtml(node.shortDescription)}</small>
                </button>
            `).join("");
            results.classList.add("open");
            results.querySelectorAll(".result").forEach((button) => {
                button.addEventListener("click", () => {
                    const id = button.getAttribute("data-id");
                    navigateToNode(id, { scale: 1 });
                });
            });
        }

        function zoomAt(clientX, clientY, factor) {
            const rect = svg.getBoundingClientRect();
            const px = clientX - rect.left;
            const py = clientY - rect.top;
            const before = graphPointFromClient(clientX, clientY);
            transform.k = Math.max(0.28, Math.min(2.4, transform.k * factor));
            transform.x = px - before.x * transform.k;
            transform.y = py - before.y * transform.k;
            applyTransform();
        }

        svg.addEventListener("pointerdown", (event) => {
            if (event.target.closest(".node-wrap")) return;
            isDragging = true;
            dragStart = { x: event.clientX - transform.x, y: event.clientY - transform.y };
            svg.classList.add("dragging");
            svg.setPointerCapture(event.pointerId);
        });
        svg.addEventListener("pointermove", (event) => {
            if (nodeDrag) {
                const node = nodesById.get(nodeDrag.id);
                if (!node) return;
                const dx = (event.clientX - nodeDrag.startClientX) / transform.k;
                const dy = (event.clientY - nodeDrag.startClientY) / transform.k;
                if (Math.abs(event.clientX - nodeDrag.startClientX) > 3 || Math.abs(event.clientY - nodeDrag.startClientY) > 3) {
                    nodeDrag.moved = true;
                    suppressClick = true;
                }
                node.initialPosition = {
                    x: nodeDrag.startX + dx,
                    y: nodeDrag.startY + dy
                };
                scheduleRenderGraph();
                return;
            }
            if (!isDragging) return;
            transform.x = event.clientX - dragStart.x;
            transform.y = event.clientY - dragStart.y;
            applyTransform();
        });
        svg.addEventListener("pointerup", () => {
            if (nodeDrag) {
                if (nodeDrag.moved) {
                    saveState();
                }
                nodeDrag = null;
                svg.classList.remove("dragging");
                setTimeout(() => { suppressClick = false; }, 80);
                return;
            }
            isDragging = false;
            svg.classList.remove("dragging");
        });
        svg.addEventListener("wheel", (event) => {
            event.preventDefault();
            zoomAt(event.clientX, event.clientY, event.deltaY < 0 ? 1.12 : 0.89);
        }, { passive: false });

        document.getElementById("backBtn").addEventListener("click", () => navigateRoute(-1));
        document.getElementById("forwardBtn").addEventListener("click", () => navigateRoute(1));
        document.getElementById("panelPrevBtn").addEventListener("click", () => navigateRoute(-1));
        document.getElementById("panelNextBtn").addEventListener("click", () => navigateRoute(1));
        document.getElementById("homeBtn").addEventListener("click", () => {
            navigateToNode(graph.centralNodeId, { scale: 0.78 });
        });
        document.getElementById("indexBtn")?.addEventListener("click", () => {
            renderIndex();
            document.getElementById("indexModal")?.classList.add("open");
        });
        document.getElementById("closeIndexBtn")?.addEventListener("click", () => {
            document.getElementById("indexModal")?.classList.remove("open");
        });
        document.getElementById("expandBtn").addEventListener("click", () => toggleExpand(selectedId));
        document.getElementById("panelCloseBranchBtn").addEventListener("click", () => closeBranch(selectedId));
        document.getElementById("panelCenterBtn").addEventListener("click", () => centerNode(selectedId));
        document.getElementById("copyRefBtn")?.addEventListener("click", async () => {
            const node = nodesById.get(selectedId);
            const ref = urlForNode(node);
            try {
                await navigator.clipboard.writeText(ref);
                document.getElementById("copyRefBtn").textContent = "Copiado";
                setTimeout(() => document.getElementById("copyRefBtn").textContent = "Copiar enlace", 1200);
            } catch (error) {
                window.prompt("Copiar enlace", ref);
            }
        });
        document.getElementById("exampleBtn")?.addEventListener("click", () => {
            document.getElementById("exampleBox")?.classList.toggle("open");
        });
        document.getElementById("zoomInBtn").addEventListener("click", () => zoomAt(window.innerWidth / 2, window.innerHeight / 2, 1.16));
        document.getElementById("zoomOutBtn").addEventListener("click", () => zoomAt(window.innerWidth / 2, window.innerHeight / 2, 0.86));
        document.getElementById("liveLayoutBtn").addEventListener("click", () => toggleLiveLayout());
        document.getElementById("resetLayoutBtn").addEventListener("click", () => rearmGraph());
        document.getElementById("level1Btn").addEventListener("click", () => setLevel(1));
        document.getElementById("level2Btn").addEventListener("click", () => setLevel(2));
        document.getElementById("level3Btn").addEventListener("click", () => setLevel(3));
        document.getElementById("relationsBtn").addEventListener("click", () => toggleRelations());
        document.getElementById("surpriseBtn").addEventListener("click", () => showSurprise());
        document.getElementById("skillTestBtn")?.addEventListener("click", () => { window.location.href = "/formacion/autoevaluacion"; });
        document.getElementById("panelSizeBtn")?.addEventListener("click", () => togglePanelSize());
        document.getElementById("presentBtn").addEventListener("click", () => togglePresentation());
        document.getElementById("togglePanelBtn").addEventListener("click", () => togglePanel());
        document.getElementById("panelCloseInlineBtn")?.addEventListener("click", () => setPanelCollapsed(true));
        document.getElementById("searchInput").addEventListener("input", (event) => search(event.target.value));
        document.getElementById("resetHistory")?.addEventListener("click", () => {
            history = [];
            historyIndex = -1;
            selectNode(graph.centralNodeId);
            renderHistory();
        });

        function navigateHistory(direction) {
            const next = historyIndex + direction;
            if (next < 0 || next >= history.length) return;
            historyIndex = next;
            const id = history[historyIndex];
            navigateToNode(id, { pushHistory: false });
        }

        function togglePresentation() {
            document.body.classList.toggle("presentation");
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen?.();
            } else {
                document.exitFullscreen?.();
            }
            setTimeout(() => centerNode(selectedId), 180);
        }

        window.addEventListener("keydown", (event) => {
            if (event.target.tagName === "INPUT" && event.key !== "Escape") return;
            if (event.key === "ArrowLeft") navigateRoute(-1);
            if (event.key === "ArrowRight") navigateRoute(1);
            if (event.key === " ") { event.preventDefault(); centerNode(selectedId); }
            if (event.key.toLowerCase() === "h") navigateToNode(graph.centralNodeId, { scale: 0.78 });
            if (event.key.toLowerCase() === "i") { renderIndex(); document.getElementById("indexModal")?.classList.add("open"); }
            if (event.key.toLowerCase() === "f") togglePresentation();
            if (event.key.toLowerCase() === "s") { event.preventDefault(); document.getElementById("searchInput").focus(); }
            if (event.key.toLowerCase() === "e") toggleExpand(selectedId);
            if (event.key.toLowerCase() === "p") togglePanel();
            if (event.key.toLowerCase() === "a") togglePanelSize();
            if (event.key.toLowerCase() === "v") toggleLiveLayout();
            if (event.key.toLowerCase() === "r") rearmGraph();
            if (event.key === "+") zoomAt(window.innerWidth / 2, window.innerHeight / 2, 1.16);
            if (event.key === "-") zoomAt(window.innerWidth / 2, window.innerHeight / 2, 0.86);
            if (event.key === "Escape") {
                document.getElementById("results").classList.remove("open");
                document.getElementById("indexModal")?.classList.remove("open");
                if (document.fullscreenElement) document.exitFullscreen?.();
                document.body.classList.remove("presentation");
            }
        });

        async function init() {
            graph = await fetch("/formacion-assets/knowledge-map.json").then((response) => response.json());
            nodes = graph.nodes;
            nodesById = new Map(nodes.map((node) => [node.id, node]));
            originalPositions = Object.fromEntries(nodes.map((node) => [
                node.id,
                { x: node.initialPosition.x, y: node.initialPosition.y }
            ]));
            loadState();
            const hashId = window.location.hash ? window.location.hash.slice(1) : "";
            if (hashId && nodesById.has(hashId)) {
                selectedId = hashId;
            }
            const savedPanelState = JSON.parse(mapStorage.getItem(stateKey) || "{}");
            setPanelCollapsed(!!savedPanelState.panelCollapsed);
            if (savedPanelState.panelFull && !savedPanelState.panelCollapsed) {
                setPanelFull(true);
            }
            if (window.matchMedia("(max-width: 980px)").matches && !mapStorage.getItem(stateKey)) {
                setPanelCollapsed(true);
                transform.k = 0.52;
            }
            if (!selectedId || !nodesById.has(selectedId)) selectedId = graph.centralNodeId;
            expanded.add(graph.centralNodeId);
            expandAncestors(selectedId);
            applyTransform();
            selectNode(selectedId, history.length === 0);
            renderIndex();
            runLayoutSimulation({ alpha: window.matchMedia("(max-width: 980px)").matches ? 0.22 : 0.42, continuous: false });
            setTimeout(() => {
                if (window.matchMedia("(max-width: 980px)").matches) {
                    setPanelCollapsed(true);
                    centerNode(selectedId, 0.56);
                } else if (!mapStorage.getItem(stateKey + "_centered")) {
                    centerNode(selectedId, 0.78);
                    mapStorage.setItem(stateKey + "_centered", "1");
                }
            }, 60);
        }

        init().catch((error) => {
            document.getElementById("nodeTitle").textContent = "No se pudo cargar el grafo";
            document.getElementById("nodeDesc").textContent = error.message;
        });
    