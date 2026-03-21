import sys
import heapq
from functools import lru_cache
from flask import Flask, request, jsonify
from flask_cors import CORS

# Initialize Flask for the Web UI
app = Flask(__name__)
CORS(app)

# ==========================================
# 1. ENVIRONMENT & RULES
# ==========================================
class WumpusEnvironment:
    def __init__(self, n, grid_map):
        self.n = n
        self.wumpuses_start = []
        self.pits = set()
        self.time_zones = set()
        self.goal = None
        self.breeze_cells = set()

        for r in range(n):
            for c in range(n):
                ch = grid_map[r][c]
                if ch == 'W':
                    self.wumpuses_start.append({'id': len(self.wumpuses_start), 'r': r + 1, 'c': c + 1})
                elif ch == 'P':
                    self.pits.add((r + 1, c + 1))
                elif ch == 'T':
                    self.time_zones.add((r + 1, c + 1))
                elif ch == 'G':
                    self.goal = (r + 1, c + 1)

        # Static breeze calculation
        for pr, pc in self.pits:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = pr + dr, pc + dc
                if 1 <= nr <= n and 1 <= nc <= n:
                    self.breeze_cells.add((nr, nc))

        self.max_turns = 4 * n * n

    def get_move_sequence(self, row, turn_idx):
        even = (row % 2 == 0)
        turn_a = (turn_idx % 2 == 0)
        if even:
            return [(1, 3), (-1, 1)] if turn_a else [(1, 1), (-1, 3)]
        else:
            return [(-1, 3), (1, 1)] if turn_a else [(-1, 1), (1, 3)]

    def clamp(self, v):
        return max(1, min(self.n, v))

    def get_wumpus_pos_at_clock(self, wid, clock):
        s = self.wumpuses_start[wid]
        r, c = s['r'], s['c']
        for t in range(clock):
            for d, steps in self.get_move_sequence(r, t):
                for _ in range(steps):
                    c += d
                    c = self.clamp(c)
        return (r, c)

    def wumpus_set(self, clock):
        return frozenset(
            self.get_wumpus_pos_at_clock(i, clock)
            for i in range(len(self.wumpuses_start))
        )

    def is_stench(self, r, c, wp_set):
        return any(abs(wr - r) + abs(wc - c) == 1 for wr, wc in wp_set)

    def cell_delta(self, r, c):
        d = 1
        if (r, c) in self.pits: d += 5
        if (r, c) in self.breeze_cells: d += 2
        if (r, c) in self.time_zones: d -= 3
        return d

# ==========================================
# 2. SOLVER (Dijkstra's Algorithm)
# ==========================================
DIRS = [(-1, 0), (0, -1), (0, 1), (1, 0)]  # Lexicographic Order

def solve_dijkstra(env):
    pq = []
    wp0 = env.wumpus_set(0)
    init_sc = 1 if env.is_stench(1, 1, wp0) else 0
    heapq.heappush(pq, (0, ((1, 1),), 1, 1, init_sc, 0))
    visited = {}

    while pq:
        cost, path_tup, r, c, sc, w_clock = heapq.heappop(pq)
        
        if (r, c) == env.goal:
            return "SAFE", cost, list(path_tup)

        state_key = (r, c, sc)
        if state_key in visited and visited[state_key] <= cost:
            continue
        visited[state_key] = cost

        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if not (1 <= nr <= env.n and 1 <= nc <= env.n): continue
            if (nr, nc) in path_tup: continue

            delta = env.cell_delta(nr, nc)
            new_cost = max(0, cost + delta)
            new_clock = new_cost 

            if new_clock >= env.max_turns: continue

            wp = env.wumpus_set(new_clock)
            is_goal = (nr, nc) == env.goal
            
            if (nr, nc) in wp and not is_goal:
                continue

            if is_goal:
                new_sc = sc
            else:
                new_sc = sc + (1 if env.is_stench(nr, nc, wp) else 0)

            if new_sc >= 3: continue

            new_path_tup = path_tup + ((nr, nc),)
            heapq.heappush(pq, (new_cost, new_path_tup, nr, nc, new_sc, new_clock))

    return "UNSAFE", 0, []

# ==========================================
# 3. WEB API ROUTE (Talks to the Frontend)
# ==========================================
@app.route('/solve', methods=['POST'])
def solve_api():
    try:
        raw = request.get_data(as_text=True).strip().splitlines()
        n = int(raw[0].strip())
        grid = [line.split() for line in raw[1:n+1]]
        
        env = WumpusEnvironment(n, grid)
        env.get_wumpus_pos_at_clock = lru_cache(maxsize=None)(env.get_wumpus_pos_at_clock)
        
        status, final_cost, final_path = solve_dijkstra(env)
        
        if status == "UNSAFE": 
            return jsonify({"status": "UNSAFE"})
        
        # Build animation frames for the Web UI
        frames = []
        t_acc = 0
        for i, (r, c) in enumerate(final_path):
            if i > 0: 
                t_acc = max(0, t_acc + env.cell_delta(r, c))
            
            wp_set = env.wumpus_set(t_acc)
            w_pos = [{"id": f"W{idx+1}", "position": list(env.get_wumpus_pos_at_clock(idx, t_acc))} for idx in range(len(env.wumpuses_start))]
            stenches = [[wr+dr, wc+dc] for wr, wc in wp_set for dr, dc in DIRS]
            
            msg = f"Moved to ({r},{c}). Time: {t_acc}s" if i > 0 else "Agent starts."
            
            # Recalculate stench for the HUD log
            current_sc = 0 if (r, c) == env.goal else (1 if env.is_stench(r, c, wp_set) else 0)

            frames.append({
                "turn": i,
                "agent": {"position": [r, c], "accumulatedTime": t_acc, "stenchCount": current_sc}, 
                "wumpuses": w_pos,
                "activeStenches": stenches,
                "logMessage": msg
            })

        return jsonify({
            "status": "SAFE",
            "gridSize": n,
            "staticElements": {
                "start": [1, 1], "gold": list(env.goal) if env.goal else [],
                "pits": [list(p) for p in env.pits], "timeZones": [list(t) for t in env.time_zones]
            },
            "animationFrames": frames
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)