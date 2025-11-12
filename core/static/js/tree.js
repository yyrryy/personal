
/* --- state --- */
const board = document.getElementById('board');
const svg = document.getElementById('svg');
const addBtn = document.getElementById('addBtn');
const connectBtn = document.getElementById('connectBtn');
const saveBtn = document.getElementById('saveBtn');
const loadBtn = document.getElementById('loadBtn');
const titleInput = document.getElementById('title');
const descInput = document.getElementById('desc');
const imageInput = document.getElementById('image');
const typeInput = document.getElementById('type');

let nodes = [];   // {id,x,y,title,description,img,type,el}
let links = [];   // {id,source,target,elVisible,elHit,labelEl,label}
let connectMode = false;
let awaiting = null;
let nodeCounter = 0;

/* --- helpers --- */
function uid(prefix='n'){ return prefix + Math.random().toString(36).slice(2,9); }
function escapeHtml(s){ if(!s) return ''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

/* --- adjacency graph builder --- */
function buildGraph() {
  const graph = {};
  links.forEach(l => {
    if (!graph[l.source]) graph[l.source] = [];
    if (!graph[l.target]) graph[l.target] = [];
    graph[l.source].push(l.target);
    graph[l.target].push(l.source);
  });
  return graph;
}

/* --- get ALL connected nodes (multi-level BFS) --- */
function getConnectedComponent(startId) {
  const graph = buildGraph();
  const visited = new Set();
  const queue = [String(startId)];

  while (queue.length) {
    const id = queue.shift();
    if (!visited.has(id)) {
      visited.add(id);
      (graph[id] || []).forEach(n => {
        if (!visited.has(String(n))) queue.push(String(n));
      });
    }
  }
  return visited;
}

/* --- clear highlights --- */
function clearHighlights(){
  nodes.forEach(n => {
    n.el.classList.remove('node-highlight');
    n.el.classList.remove('selected');
  });
  links.forEach(l => {
    if (l.elVisible) l.elVisible.classList.remove('highlight');
    if (l.elHit) l.elHit.classList.remove('highlight');
    if (l.labelEl) l.labelEl.classList.remove('connection-label-highlight');
  });
}

/* --- highlight component --- */
function highlightComponent(nodeId){
  const connected = getConnectedComponent(nodeId);

  // highlight nodes
  connected.forEach(id => {
    const n = nodes.find(nn => String(nn.id) === String(id));
    if (n) n.el.classList.add('node-highlight');
  });

  // highlight links
  links.forEach(l => {
    if (connected.has(String(l.source)) && connected.has(String(l.target))) {
      if (l.elVisible) l.elVisible.classList.add('highlight');
      if (l.elHit) l.elHit.classList.add('highlight');
      if (l.labelEl) l.labelEl.classList.add('connection-label-highlight');
    }
  });
}

/* --- node creation / drag --- */
function createNode(data){
  const n = Object.assign({x: 120 + Math.random()*300, y: 80 + Math.random()*150, title: 'Untitled', description:'', img:null, type:'note' }, data);
  const el = document.createElement('div');
  el.className = 'node';
  el.style.left = n.x + 'px';
  el.style.top = n.y + 'px';
  el.dataset.id = n.id;
  el.innerHTML = `
    ${n.img ? `<img src="${n.img}" alt="">` : ''}
    <div class="title">${escapeHtml(n.title)}</div>
    <div class="desc">${escapeHtml(n.description)}</div>
  `;
  n.el = el;
  board.appendChild(el);
  attachDrag(el);
  el.addEventListener('click', ev => { ev.stopPropagation(); onSelectNode(n); });
  nodes.push(n);
  updateConnections();
  return n;
}

function attachDrag(el) {
  let sx, sy, sl, st;
  let dragging = false;

  el.addEventListener('pointerdown', e => {
    el.setPointerCapture(e.pointerId);
    sx = e.clientX;
    sy = e.clientY;
    sl = parseFloat(el.style.left) || 0;
    st = parseFloat(el.style.top) || 0;
    dragging = true;
    el.classList.add('dragging');
  });

  window.addEventListener('pointermove', e => {
    if (!dragging) return;
    const nx = sl + (e.clientX - sx);
    const ny = st + (e.clientY - sy);
    el.style.left = nx + 'px';
    el.style.top = ny + 'px';
    const node = nodes.find(x => x.el === el);
    if (node) {
      node.x = nx;
      node.y = ny;
    }
    updateConnections();
  });

  window.addEventListener('pointerup', e => {
    if (!dragging) return;
    dragging = false;
    el.classList.remove('dragging');
    try { el.releasePointerCapture(e.pointerId); } catch (e) {}

    const node = nodes.find(x => x.el === el);
    if (node) {
      fetch(`/update_node/${node.id}/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ x: node.x, y: node.y })
      });
    }
  });
}

/* --- selection / connect flow --- */
function onSelectNode(n){
  if(connectMode){
    if(!awaiting){
      awaiting = n;
      n.el.classList.add('selected');
      return;
    }
    if(awaiting && awaiting !== n){
      createLink(awaiting, n, '', '1');
      awaiting.el.classList.remove('selected');
      awaiting = null;
      connectMode = false;
      connectBtn.textContent = 'Connect';
      return;
    }
  } else {
    clearHighlights();
    highlightComponent(n.id);
    nodes.forEach(x => x.el.classList.remove('selected'));
    n.el.classList.add('selected');
  }
}

/* --- create link --- */
function createLink(a, b, labelText = '', saveToDb) {
  const id = uid('link');
  const gVisible = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  gVisible.classList.add('connection-line');

  const gHit = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  gHit.classList.add('connection-hit');

  const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  label.classList.add('connection-label');
  label.textContent = labelText || '';

  gVisible.dataset.linkId = id;
  gHit.dataset.linkId = id;
  label.dataset.linkId = id;

  svg.appendChild(gVisible);
  svg.appendChild(gHit);
  svg.appendChild(label);

  const linkObj = {
    id,
    source: a.id,
    target: b.id,
    elVisible: gVisible,
    elHit: gHit,
    labelEl: label,
    label: labelText
  };
  links.push(linkObj);
  updateConnections();

  if (saveToDb === '1') {
    fetch("/create_connection/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: a.id, target: b.id, label: labelText })
    })
    .then(res => res.json())
    .then(data => { if (data.status === "ok") linkObj.id = data.id; });
  }

  return id;
}

/* --- update all link geometry --- */
function updateConnections(){
  const rect = board.getBoundingClientRect();
  svg.setAttribute('width', rect.width);
  svg.setAttribute('height', rect.height);

  links.forEach(l => {
    const a = nodes.find(n => String(n.id) === String(l.source));
    const b = nodes.find(n => String(n.id) === String(l.target));
    if(!a || !b){
      try{ l.elVisible.remove(); l.elHit.remove(); l.labelEl.remove(); }catch(e){}
      return;
    }
    const x1 = a.x + a.el.offsetWidth/2;
    const y1 = a.y + a.el.offsetHeight/2;
    const x2 = b.x + b.el.offsetWidth/2;
    const y2 = b.y + b.el.offsetHeight/2;

    const dx = Math.abs(x2 - x1);
    const cx1 = x1 + (x2 > x1 ? Math.min(160, dx/2) : -Math.min(160, dx/2));
    const cx2 = x2 + (x2 > x1 ? -Math.min(160, dx/2) : Math.min(160, dx/2));
    const d = `M ${x1} ${y1} C ${cx1} ${y1} ${cx2} ${y2} ${x2} ${y2}`;

    l.elVisible.setAttribute('d', d);
    l.elHit.setAttribute('d', d);
    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;
    l.labelEl.setAttribute('x', midX);
    l.labelEl.setAttribute('y', midY - 6);
  });
}

/* --- collect / save / load --- */
function collectBoardData(){
  return {
    nodes: nodes.map((n, idx) => ({
      id: n.id,
      title: n.title,
      description: n.description,
      x: n.x,
      y: n.y,
      img: n.img,
      type: n.type
    })),
    connections: links.map(l => ({
      source: l.source,
      target: l.target,
      label: l.label || ''
    }))
  }
}

async function saveBoard() {
  const boardData = collectBoardData();
  const formData = new FormData();
  formData.append("nodes", JSON.stringify(boardData.nodes));
  formData.append("connections", JSON.stringify(boardData.connections));

  await fetch("/save_board/", { method: "POST", body: formData });
  alert("Board saved!");
}

async function loadBoard(){
  const res = await fetch('/get_board_data');
  const data = await res.json();

  nodes.forEach(n => n.el.remove());
  nodes = [];
  links.forEach(l => { try{ l.elVisible.remove(); l.elHit.remove(); l.labelEl.remove(); }catch(e){} });
  links = [];

  (data.nodes || []).forEach(n => createNode({
    id: n.id,
    title: n.title,
    description: n.description,
    x: n.x,
    y: n.y,
    type: n.type,
    img: n.image ? n.image : null
  }));

  (data.connections || []).forEach(c => {
    const a = nodes.find(n => String(n.id) === String(c.source));
    const b = nodes.find(n => String(n.id) === String(c.target));
    if(a && b){
      createLink(a, b, c.label || '', '0');
    }
  });

  setTimeout(updateConnections, 10);
}

/* --- UI wiring --- */
addBtn.addEventListener('click', () => {
  const t = titleInput.value.trim() || 'Untitled';
  const d = descInput.value.trim();
  const typ = typeInput.value;

  const formData = new FormData();
  formData.append("title", t);
  formData.append("description", d);
  formData.append("x", 120 + Math.random() * 300);
  formData.append("y", 80 + Math.random() * 150);
  formData.append("type", typ);

  if (imageInput.files && imageInput.files[0]) {
    formData.append("image", imageInput.files[0]);
  }

  fetch("/create_node/", { method: "POST", body: formData })
  .then(res => res.json())
  .then(nodeData => {
    createNode({
      id: nodeData.id,
      title: nodeData.title,
      description: nodeData.description,
      type: nodeData.type,
      x: parseFloat(nodeData.x),
      y: parseFloat(nodeData.y),
      img: nodeData.image || null
    });
    titleInput.value = '';
    descInput.value = '';
    imageInput.value = '';
  });
});

connectBtn.addEventListener('click', ()=>{
  connectMode = !connectMode;
  awaiting = null;
  connectBtn.textContent = connectMode ? 'Connecting... (click two nodes)' : 'Connect';
});

saveBtn.addEventListener('click', saveBoard);
loadBtn.addEventListener('click', loadBoard);

board.addEventListener('click', ()=>{
  if(awaiting){ awaiting.el.classList.remove('selected'); awaiting = null; }
  if(connectMode){ connectMode = false; connectBtn.textContent = 'Connect'; }
  clearHighlights();
});

/* initialize */
loadBoard();
window.addEventListener('resize', updateConnections);