# 🦇 Wumpus Pathfinder // Visualization Engine

A high-performance, full-stack pathfinding visualization engine for the classic **Wumpus World** problem. This project calculates the optimal, safest, and fastest route for an agent to navigate a dangerous grid filled with Pits, Time Zones, and moving Wumpuses, and visualizes the timeline in a modern sci-fi web interface.

## ✨ Key Features
* **Hybrid Algorithm Engine:** Uses Exhaustive DFS for small grids ($N \le 7$) to ensure absolute precision, and a highly-optimized Dijkstra/Priority Queue with aggressive state-pruning for massive grids ($N > 7$) to prevent timeouts.
* **Full-Stack Architecture:** A lightweight Python/Flask backend handles the heavy pathfinding math, while a vanilla JavaScript frontend handles the state-based animation playback.
* **Sci-Fi Web UI:** A responsive, dark-mode dashboard featuring pulsing CSS hazard animations, an analytics HUD, and step-by-step playback controls.
* **Lexicographical Tie-Breaking:** Automatically prioritizes paths using Up, Left, Right, Down standard order when multiple paths share the exact same time cost.

## 🛠️ Tech Stack
* **Backend:** Python 3, Flask, Flask-CORS, `heapq` (Priority Queue)
* **Frontend:** HTML5, CSS3 (Custom Variables/Keyframes), Vanilla JavaScript (Fetch API)

---

## 🚀 How to Run the Project

Because this is a full-stack application, you need to run the Python backend and the HTML frontend simultaneously. 

### Step 1: Start the Backend (The Brain)
1. Open a terminal and navigate to the `backend` folder:
   ```bash
   cd backend
Install the required dependencies (Flask and Flask-CORS):

Bash
pip install -r requirements.txt
Run the Flask server:

Bash
python app.py
(Keep this terminal open. It will run on http://127.0.0.1:5000)

Step 2: Start the Frontend (The UI)
Open a second terminal window and navigate to the frontend folder:

Bash
cd frontend
Start a local HTTP server:

Bash
python -m http.server 8000
Open your web browser and navigate to http://localhost:8000

🎮 How to Use the Dashboard
Paste your raw grid data into the RAW GRID DATA text area.

Make sure the very first line is a single integer representing the grid size (e.g., 7 or 12).

Click ⚡ LOAD & SOLVE.

If a safe path exists, the grid will generate. Use the Playback Controls (or the Left/Right arrow keys) to step through time and watch the Agent dodge the Wumpuses!

Input Grid Format Example:
Plaintext
5
. . . W .
. . . . .
. . . . W
P . . . G
. T T T .
🧠 Game Rules Implemented
Agent Movement: Costs 1 second per step.

Pits (P): Adds a 5-second penalty.

Time Zones (T): Subtracts 3 seconds from the clock.

Wumpus (W): Moves sequentially (A/B clock cycle). If the Agent shares a tile with a Wumpus, the path is invalidated (unless it is the Goal tile).

Stench & Breeze: Calculated dynamically based on wumpus/pit proximity. Encountering 3 stenches invalidates the path.
