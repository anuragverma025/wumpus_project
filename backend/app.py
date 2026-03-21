import sys
import math
from functools import lru_cache
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.setrecursionlimit(10000)

app = Flask(__name__)
CORS(app)

# --- Your Core Environment & Algorithm ---
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
                char = grid_map[r][c]
                if char == 'W': self.wumpuses_start.append({'id': len(self.wumpuses_start), 'r': r+1, 'c': c+1}) 
                elif char == 'P': self.pits.add((r+1, c+1))
                elif char == 'T': self.time_zones.add((r+1, c+1))
                elif char == 'G': self.goal = (r+1, c+1)

        for pr, pc in self.pits:
            for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                nr, nc = pr + dr, pc + dc
                if 1 <= nr <= n and 1 <= nc <= n: self.breeze_cells.add((nr, nc))
        self.max_turns = 4 * n * n

    def get_move_sequence(self, row, turn_idx):
        is_even = (row % 2 == 0)
        is_turn_a = (turn_idx % 2 == 0) 
        if is_even: return [(1, 3), (-1, 1)] if is_turn_a else [(1, 1), (-1, 3)]
        else: return [(-1, 3), (1, 1)] if is_turn_a else [(-1, 1), (1, 3)]

    def clamp(self, val): return max(1, min(self.n, val))

    def get_wumpus_pos_at_clock(self, wumpus_id, clock):
        start = self.wumpuses_start[wumpus_id]
        r, c = start['r'], start['c']
        for t in range(clock):
            moves = self.get_move_sequence(r, t)
            for direction, steps in moves:
                for _ in range(steps):
                    c += direction
                    c = self.clamp(c)
        return (r, c)

    def is_stench(self, r, c, wumpus_positions_set):
        for wr, wc in wumpus_positions_set:
            if abs(wr - r) + abs(wc - c) == 1: return True
        return False

def solve_wumpus_rbfs_reset(env):
    goal = env.goal
    n = env.n
    neighbor_offsets = [(-1, 0), (0, -1), (0, 1), (1, 0)]

    def get_successors(r, c, wumpus_clock, stench, cost, path_set):
        succ = []
        for dr, dc in neighbor_offsets:
            nr, nc = r + dr, c + dc
            if not (1 <= nr <= n and 1 <= nc <= n): continue
            if (nr, nc) in path_set: continue
            
            delta = 1
            if (nr, nc) in env.pits: delta += 5
            if (nr, nc) in env.breeze_cells: delta += 2
            if (nr, nc) in env.time_zones: delta -= 3
            new_cost = max(0, cost + delta)
            
            next_wumpus_clock = 0 if new_cost == 0 else wumpus_clock + 1
            if next_wumpus_clock >= env.max_turns: continue

            wumpus_positions = set()
            for i in range(len(env.wumpuses_start)):
                wumpus_positions.add(env.get_wumpus_pos_at_clock(i, next_wumpus_clock))

            if (nr, nc) in wumpus_positions and (nr, nc) != goal: continue
            new_stench = stench + (1 if env.is_stench(nr, nc, wumpus_positions) else 0)
            if new_stench >= 3: continue

            succ.append({'r': nr, 'c': nc, 'w_clock': next_wumpus_clock, 'stench': new_stench, 'cost': new_cost, 'f': new_cost })
        return succ

    def rbfs(r, c, w_clock, stench, cost, path, path_set, f_limit):
        if (r, c) == goal: return (path, cost, "SUCCESS")
        successors = get_successors(r, c, w_clock, stench, cost, path_set)
        if not successors: return (None, float('inf'), "FAILURE")
        successors.sort(key=lambda x: (x['f'], x['r'], x['c']))

        while True:
            best = successors[0]
            if best['f'] > f_limit: return (None, best['f'], "FAILURE")
            alt_f = successors[1]['f'] if len(successors) > 1 else float('inf')
            new_path_set = path_set.copy()
            new_path_set.add((best['r'], best['c']))
            
            result_path, result_cost, result_status = rbfs(best['r'], best['c'], best['w_clock'], best['stench'], best['cost'], path + [(best['r'], best['c'])], new_path_set, min(f_limit, alt_f))
            if result_status == "SUCCESS": return (result_path, result_cost, "SUCCESS")
            best['f'] = result_cost
            successors.sort(key=lambda x: (x['f'], x['r'], x['c']))

    env.get_wumpus_pos_at_clock = lru_cache(maxsize=None)(env.get_wumpus_pos_at_clock)
    final_path, final_cost, status = rbfs(1, 1, 0, 0, 0, [(1, 1)], {(1, 1)}, float('inf'))
    if status == "SUCCESS": return "SAFE", final_cost, final_path
    else: return "UNSAFE", 0, []

# --- JSON Payload Translation Layer ---
def build_payload(env, status, final_cost, final_path):
    if status == "UNSAFE":
        return { "status": "UNSAFE" }

    frames = []
    curr_time = 0
    w_clock = 0
    stench_count = 0

    for turn, (r, c) in enumerate(final_path):
        if turn > 0:
            delta = 1
            if (r, c) in env.pits: delta += 5
            if (r, c) in env.breeze_cells: delta += 2
            if (r, c) in env.time_zones: delta -= 3
            curr_time = max(0, curr_time + delta)
            w_clock = 0 if curr_time == 0 else w_clock + 1

        wumpuses = []
        wumpus_positions = set()
        for w in env.wumpuses_start:
            pos = env.get_wumpus_pos_at_clock(w['id'], w_clock)
            wumpuses.append({"id": f"W{w['id']+1}", "position": list(pos)})
            wumpus_positions.add(pos)

        stenches = []
        for wr, wc in wumpus_positions:
            for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                nr, nc = wr + dr, wc + dc
                if 1 <= nr <= env.n and 1 <= nc <= env.n:
                    stenches.append([nr, nc])

        if turn > 0 and env.is_stench(r, c, wumpus_positions):
            stench_count = min(3, stench_count + 1)

        msg = "Agent starts at (1,1)." if turn == 0 else f"Move to ({r},{c}). Cost: +{curr_time}s total."
        if (r, c) in env.pits: msg = f"⚠️ Pit at ({r},{c})! +5s penalty."
        elif (r, c) in env.time_zones: msg = f"⏳ Time Zone at ({r},{c})! -3s."
        if (r, c) == env.goal: msg = f"🏆 GOLD REACHED! Final Time: {curr_time}s"

        frames.append({
            "turn": turn,
            "agent": { "position": [r, c], "accumulatedTime": curr_time, "stenchCount": stench_count },
            "wumpuses": wumpuses,
            "activeStenches": stenches,
            "logMessage": msg
        })

    return {
        "status": "SAFE",
        "gridSize": env.n,
        "staticElements": {
            "start": [1, 1], "gold": list(env.goal),
            "pits": [list(p) for p in env.pits], "timeZones": [list(t) for t in env.time_zones]
        },
        "summary": { "totalTime": final_cost, "stenchEncountered": stench_count, "optimalPath": [list(p) for p in final_path] },
        "animationFrames": frames
    }

# --- API Route ---
@app.route('/solve', methods=['POST'])
def solve_api():
    try:
        data = request.get_data(as_text=True)
        lines = [line.strip() for line in data.strip().splitlines() if line.strip()]
        n = int(lines[0])
        grid_map = [line.split() for line in lines[1:n+1]]
        
        env = WumpusEnvironment(n, grid_map)
        status, final_cost, final_path = solve_wumpus_rbfs_reset(env)
        payload = build_payload(env, status, final_cost, final_path)
        
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)