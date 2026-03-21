const AppState = { data: null, currentFrame: 0, isPlaying: false, timer: null };

// 1. Fetch from Python Backend
document.getElementById('btnSolve').onclick = async () => {
    const text = document.getElementById('gridInput').value;
    const btn = document.getElementById('btnSolve');
    const badge = document.getElementById('statusBadge');
    
    btn.textContent = "SOLVING...";
    btn.disabled = true;

    try {
        const response = await fetch('http://127.0.0.1:5000/solve', {
            method: 'POST', body: text
        });
        const data = await response.json();
        
        if (data.status === 'UNSAFE') {
            badge.textContent = 'UNSAFE'; badge.className = 'status unsafe';
            document.getElementById('gridWrapper').style.display = 'none';
            document.getElementById('emptyState').style.display = 'block';
        } else if (data.status === 'SAFE') {
            badge.textContent = 'SAFE'; badge.className = 'status safe';
            AppState.data = data;
            buildGrid();
            renderFrame(0);
            document.getElementById('logBox').innerHTML = ''; // clear logs
            ['btnPrev', 'btnPlay', 'btnNext'].forEach(id => document.getElementById(id).disabled = false);
        }
    } catch (err) { 
        alert("Error: Make sure the Python backend is running on port 5000!"); 
    }
    
    btn.textContent = "⚡ LOAD & SOLVE";
    btn.disabled = false;
};

// 2. Build Static Grid
function buildGrid() {
    const { gridSize, staticElements } = AppState.data;
    const table = document.getElementById('gridTable');
    table.style.gridTemplateColumns = `repeat(${gridSize}, var(--cell-size))`;
    table.innerHTML = '';

    const pS = new Set(staticElements.pits.map(p => `${p[0]},${p[1]}`));
    const tS = new Set(staticElements.timeZones.map(t => `${t[0]},${t[1]}`));
    const bS = new Set();
    
    staticElements.pits.forEach(p => {
        [[-1,0],[1,0],[0,-1],[0,1]].forEach(d => bS.add(`${p[0]+d[0]},${p[1]+d[1]}`));
    });

    for (let r = 1; r <= gridSize; r++) {
        for (let c = 1; c <= gridSize; c++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.id = `cell-${r}-${c}`;
            
            if (r === staticElements.gold[0] && c === staticElements.gold[1]) { cell.innerHTML = 'G'; cell.classList.add('gold'); }
            if (pS.has(`${r},${c}`)) { cell.innerHTML = 'P'; cell.classList.add('pit'); }
            if (tS.has(`${r},${c}`)) { cell.innerHTML = 'T'; cell.classList.add('time'); }
            if (bS.has(`${r},${c}`) && !pS.has(`${r},${c}`)) cell.classList.add('breeze-active');
            
            table.appendChild(cell);
        }
    }
    
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('gridWrapper').style.display = 'block';
}

// 3. Render Animation Frame
function renderFrame(idx) {
    if (!AppState.data || idx < 0 || idx >= AppState.data.animationFrames.length) {
        if (idx >= AppState.data.animationFrames.length) pausePlayback();
        return;
    }
    
    AppState.currentFrame = idx;
    const frame = AppState.data.animationFrames[idx];
    const cellSize = 50 + 2; // size + gap

    // Update Stenches visually
    document.querySelectorAll('.stench-active').forEach(c => c.classList.remove('stench-active'));
    frame.activeStenches.forEach(s => {
        const c = document.getElementById(`cell-${s[0]}-${s[1]}`);
        if(c) c.classList.add('stench-active');
    });

    // Draw Dynamic Entities (Agent & Wumpus)
    const layer = document.getElementById('entityLayer');
    layer.innerHTML = '';
    
    // Create Agent
    const a = document.createElement('div');
    a.className = 'entity agent'; a.innerHTML = '🔵';
    a.style.transform = `translate(${(frame.agent.position[1]-1)*cellSize}px, ${(frame.agent.position[0]-1)*cellSize}px)`;
    layer.appendChild(a);

    // Create Wumpuses
    frame.wumpuses.forEach(w => {
        const we = document.createElement('div');
        we.className = 'entity wumpus'; we.innerHTML = '👹';
        we.style.transform = `translate(${(w.position[1]-1)*cellSize}px, ${(w.position[0]-1)*cellSize}px)`;
        layer.appendChild(we);
    });

    // Update HUD Stats
    document.getElementById('hudTurn').textContent = frame.turn;
    document.getElementById('hudTime').textContent = frame.agent.accumulatedTime;
    document.getElementById('hudStench').textContent = `${frame.agent.stenchCount} / 3`;

    // Append to Event Log (Only if moving forward to avoid duplicate logs)
    if (idx === 0 || !document.getElementById(`log-${idx}`)) {
        const box = document.getElementById('logBox');
        let cssClass = '';
        if (frame.logMessage.includes("GOLD")) cssClass = 'gold';
        if (frame.logMessage.includes("Pit")) cssClass = 'pit';
        
        box.innerHTML += `<div class="log-entry ${cssClass}" id="log-${idx}"><b>T${String(frame.turn).padStart(2,'0')}:</b> ${frame.logMessage}</div>`;
        box.scrollTop = box.scrollHeight;
    }
}

// 4. Playback Controls
function pausePlayback() {
    clearInterval(AppState.timer);
    AppState.isPlaying = false;
    const btn = document.getElementById('btnPlay');
    btn.innerHTML = '▶ Play';
    btn.classList.remove('active');
}

document.getElementById('btnNext').onclick = () => { pausePlayback(); renderFrame(AppState.currentFrame + 1); };
document.getElementById('btnPrev').onclick = () => { pausePlayback(); renderFrame(AppState.currentFrame - 1); };
document.getElementById('btnPlay').onclick = () => {
    if (AppState.isPlaying) {
        pausePlayback();
    } else {
        if (AppState.currentFrame >= AppState.data.animationFrames.length - 1) {
            renderFrame(0); // Restart if at the end
            document.getElementById('logBox').innerHTML = ''; // clear log on restart
        }
        AppState.isPlaying = true;
        document.getElementById('btnPlay').innerHTML = '⏸ Pause';
        document.getElementById('btnPlay').classList.add('active');
        AppState.timer = setInterval(() => renderFrame(AppState.currentFrame + 1), 600);
    }
};