import sys
import heapq
from functools import lru_cache
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ==========================================
# 1. ENVIRONMENT & RULES
# ==========================================
class WumpusEnvironment:
    # FIXED: Replaced _init_ with __init__
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

    @lru_cache(maxsize=None)
    def get_wumpus_pos_at_clock(self, wid, clock):
        s = self.wumpuses_start[wid]
        r, c = s['r'], s['c']
        for t in range(max(0, clock)):
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
# 2. SOLVER (Exhaustive DFS for N <= 7)
# ==========================================
class DFSSolver:
    # FIXED: Replaced _init_ with __init__
    def __init__(self, env):
        self.env = env
        self.best_cost = float('inf')
        self.best_path = []

    def solve(self):
        wp0 = self.env.wumpus_set(0)
        init_sc = 1 if self.env.is_stench(1, 1, wp0) else 0
        self._dfs(1, 1, 0, init_sc, ((1, 1),))

        if self.best_cost == float('inf'):
            return "UNSAFE", 0, []
        return "SAFE", self.best_cost, self.best_path

    def _dfs(self, r, c, cost, sc, path):
        # Goal reached
        if (r, c) == self.env.goal:
            if cost < self.best_cost:
                self.best_cost = cost
                self.best_path = list(path)
            return

        # Directions: Lexicographical order
        for dr, dc in [(-1, 0), (0, -1), (0, 1), (1, 0)]:
            nr, nc = r + dr, c + dc

            if not (1 <= nr <= self.env.n and 1 <= nc <= self.env.n): continue
            if (nr, nc) in path: continue

            delta = self.env.cell_delta(nr, nc)
            new_cost = cost + delta

            w_clock = max(0, new_cost)
            if w_clock >= self.env.max_turns: continue

            wp = self.env.wumpus_set(w_clock)
            is_goal = (nr, nc) == self.env.goal

            if (nr, nc) in wp and not is_goal: continue

            new_sc = sc
            if not is_goal and self.env.is_stench(nr, nc, wp):
                new_sc += 1

            if new_sc >= 3: continue

            # Recurse
            self._dfs(nr, nc, new_cost, new_sc, path + ((nr, nc),))

# ==========================================
# 3. SOLVER (Dijkstra for N > 7)
# ==========================================
def solve_dijkstra(env):
    wp0 = env.wumpus_set(0)
    init_sc = 1 if env.is_stench(1, 1, wp0) else 0
    pq = [(0, ((1, 1),), 1, 1, init_sc)]
    visited = {}

    while pq:
        cost, path_tup, r, c, sc = heapq.heappop(pq)

        if (r, c) == env.goal:
            return "SAFE", cost, list(path_tup)

        state_key = (r, c, sc)
        if state_key in visited and visited[state_key] <= cost:
            continue
        visited[state_key] = cost

        for dr, dc in [(-1, 0), (0, -1), (0, 1), (1, 0)]:
            nr, nc = r + dr, c + dc
            if not (1 <= nr <= env.n and 1 <= nc <= env.n): continue
            if (nr, nc) in path_tup: continue

            delta = env.cell_delta(nr, nc)
            new_cost = cost + delta
            w_clock = max(0, new_cost)

            if w_clock >= env.max_turns: continue

            wp = env.wumpus_set(w_clock)
            is_goal = (nr, nc) == env.goal

            if (nr, nc) in wp and not is_goal: continue

            new_sc = sc
            if not is_goal and env.is_stench(nr, nc, wp):
                new_sc += 1

            if new_sc >= 3: continue

            heapq.heappush(pq, (new_cost, path_tup + ((nr, nc),), nr, nc, new_sc))

    return "UNSAFE", 0, []

# ==========================================
# 4. FLASK API (Connects to Website)
# ==========================================
@app.route('/solve', methods=['POST'])
def solve_api():
    try:
        raw = request.get_data(as_text=True).strip().splitlines()
        n = int(raw[0].strip())
        grid = [line.split() for line in raw[1:n+1]]

        env = WumpusEnvironment(n, grid)

        # Hybrid Plan: DFS for small grids, Dijkstra for large ones
        if n <= 7:
            solver = DFSSolver(env)
            status, final_cost, final_path = solver.solve()
        else:
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

            # Using standard Up, Left, Right, Down logic to draw stench fields
            stenches = [[wr+dr, wc+dc] for wr, wc in wp_set for dr, dc in [(-1, 0), (0, -1), (0, 1), (1, 0)]]

            msg = f"Moved to ({r},{c}). Time: {t_acc}s" if i > 0 else "Agent starts."
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

# FIXED: Replaced _main_ with __main__
if __name__ == '__main__':
    app.run(debug=True, port=5000)