
const AppState = { data: null, currentFrame: 0, isPlaying: false, timer: null };

document.getElementById('btnSolve').onclick = async () => {
    const text = document.getElementById('gridInput').value;
    const btn = document.getElementById('btnSolve');
    const badge = document.getElementById('statusBadge');
    btn.textContent = "SOLVING...";
    btn.disabled = true;

    try {
        const response = await fetch('http://127.0.0.1:5000/solve', { method: 'POST', body: text });
        const data = await response.json();

        if (data.status === 'UNSAFE') {
            badge.textContent = 'UNSAFE'; badge.className = 'status unsafe';
            document.getElementById('gridWrapper').style.display = 'none';
        } else {
            badge.textContent = 'SAFE'; badge.className = 'status safe';
            AppState.data = data;
            buildGrid();
            document.getElementById('logBox').innerHTML = ''; // Clear logs
            renderFrame(0);
            ['btnPrev', 'btnPlay', 'btnNext'].forEach(id => document.getElementById(id).disabled = false);
        }
    } catch (err) { alert("Backend Error! Is Python running?"); }
    btn.textContent = "⚡ LOAD & SOLVE"; btn.disabled = false;
};

function buildGrid() {
    const { gridSize, staticElements } = AppState.data;
    const table = document.getElementById('gridTable');

    // Auto-scale grid sizes
    const avail = Math.min(document.querySelector('.grid-panel').clientWidth - 40, document.querySelector('.grid-panel').clientHeight - 40);
    const cs = Math.max(Math.min(Math.floor(avail / gridSize) - 2, 72), 24);
    document.documentElement.style.setProperty('--cell-size', `${cs}px`);

    table.style.gridTemplateColumns = `repeat(${gridSize}, var(--cell-size))`;
    table.innerHTML = '';

    for (let r = 1; r <= gridSize; r++) {
        for (let c = 1; c <= gridSize; c++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.id = `cell-${r}-${c}`;

            // Add tiny coordinate numbers
            cell.innerHTML = `<span style="position:absolute; top:2px; left:4px; font-size:10px; color:#555; pointer-events:none; font-family: monospace;">${r},${c}</span>`;

            if (r === staticElements.gold[0] && c === staticElements.gold[1]) { cell.innerHTML += 'G'; cell.classList.add('gold'); }
            staticElements.pits.forEach(p => { if(p[0]===r && p[1]===c) { cell.innerHTML += 'P'; cell.classList.add('pit'); } });
            staticElements.timeZones.forEach(t => { if(t[0]===r && t[1]===c) { cell.innerHTML += 'T'; cell.classList.add('time'); } });
            table.appendChild(cell);
        }
    }
    document.getElementById('gridWrapper').style.display = 'block';
    document.getElementById('emptyState').style.display = 'none';
}

function renderFrame(idx) {
    if (!AppState.data || idx < 0 || idx >= AppState.data.animationFrames.length) {
        if (AppState.data && idx >= AppState.data.animationFrames.length) pausePlayback();
        return;
    }
    AppState.currentFrame = idx;
    const frame = AppState.data.animationFrames[idx];
    const cellSize = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--cell-size')) + 2;

    // Hazards
    document.querySelectorAll('.stench-active').forEach(c => c.classList.remove('stench-active'));
    frame.activeStenches.forEach(s => {
        const c = document.getElementById(`cell-${s[0]}-${s[1]}`);
        if(c) c.classList.add('stench-active');
    });

    // Entities
    const layer = document.getElementById('entityLayer');
    layer.innerHTML = '';

    const draw = (char, pos, cls) => {
        const div = document.createElement('div');
        div.className = `entity ${cls}`; div.innerHTML = char;
        div.style.transform = `translate(${(pos[1]-1)*cellSize}px, ${(pos[0]-1)*cellSize}px)`;
        layer.appendChild(div);
    };

    draw('🔵', frame.agent.position, 'agent');
    frame.wumpuses.forEach(w => draw('👹', w.position, 'wumpus'));

    // HUD Stats
    document.getElementById('hudTurn').textContent = frame.turn;
    document.getElementById('hudTime').textContent = frame.agent.accumulatedTime;
    document.getElementById('hudStench').textContent = `${frame.agent.stenchCount} / 3`;

    // Event Log
    if (idx === 0 || !document.getElementById(`log-${idx}`)) {
        const box = document.getElementById('logBox');
        let cssClass = '';
        if (frame.logMessage.includes("GOLD")) cssClass = 'gold';
        if (frame.logMessage.includes("Pit")) cssClass = 'pit';
        box.innerHTML += `<div class="log-entry ${cssClass}" id="log-${idx}"><b>T${String(frame.turn).padStart(2,'0')}:</b> ${frame.logMessage}</div>`;
        box.scrollTop = box.scrollHeight;
    }
}

// --- Playback Logic ---
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
            renderFrame(0); 
            document.getElementById('logBox').innerHTML = ''; 
        }
        AppState.isPlaying = true;
        document.getElementById('btnPlay').innerHTML = '⏸ Pause';
        document.getElementById('btnPlay').classList.add('active');
        // Changes frame every 600ms
        AppState.timer = setInterval(() => renderFrame(AppState.currentFrame + 1), 600);
    }
};

// --- Keyboard Shortcuts ---
document.addEventListener('keydown', (e) => {
    if (!AppState.data) return; 
    if (document.activeElement.id === 'gridInput') return; 

    if (e.key === 'ArrowRight') {
        pausePlayback(); 
        renderFrame(AppState.currentFrame + 1);
    } else if (e.key === 'ArrowLeft') {
        pausePlayback(); 
        renderFrame(AppState.currentFrame - 1);
    } else if (e.key === ' ') { 
        e.preventDefault(); 
        document.getElementById('btnPlay').click();
    }
});