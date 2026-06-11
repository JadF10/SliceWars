# 🍉 SliceWars

A real-time multiplayer gesture-controlled fruit slicing game — built from scratch using Python, Pygame, OpenCV, and MediaPipe. No game engine. No tutorials. Just code.

> **Server live at:** `acela.proxy.rlwy.net:46733` — clone and run to play from anywhere in the world.

---

## Demo

| Gesture Control | Multiplayer Lobby | Versus Mode |
|---|---|---|
| Wave your hand — your index finger IS the blade | Chat, invite, and match with players globally | Race to slice fruits before your opponent |

---

## What makes this project stand out

### Computer Vision Pipeline (Qualcomm signal)
- Webcam input processed at **30fps** using **MediaPipe's 21 skeletal hand landmarks**
- **Custom geometric gesture classifier** — no ML model, pure trigonometry on landmark angles
- **4 gestures classified in real time:** SLICE, SHIELD, POWER_UP, DOUBLE_SLICE
- **Measured input-to-action latency: 30–70ms**
- Mouse cursor fallback with identical interface — game engine never knows which input is active

### Event-Driven Server Architecture (Murex signal)
- **Single source of truth** — server owns all game state, clients only render
- **Every game event timestamped in milliseconds** — FRUIT_SPAWNED, SLICE_HIT, BOMB_HIT, SCORE_UPDATE
- **Live latency monitor** — ping/pong RTT measured per client, displayed in HUD
- **Tick-based game loop** — fixed update rate, independent of client connections
- **Deployed to cloud infrastructure** — server runs 24/7, playable globally

---

## Features

### Game Modes
| Mode | Description |
|---|---|
| **Solo** | Classic fruit ninja — 3 lives, combo multiplier, survive as long as possible |
| **Co-op** | Two players, shared lives pool, combined score — coordination wins |
| **Versus** | Race to slice the same fruits first — independent lives, magnet fruit steals opponent's points |

### Items
| Item | Effect |
|---|---|
| 🍉 Watermelon | +5 points |
| 🍍 Pineapple | +4 points |
| 🍊 Orange | +3 points |
| 🍎 Apple | +2 points |
| 🍌 Banana | +2 points |
| 💣 Bomb | −1 life |
| ☢️ Mega Bomb | −2 lives (screen shake, unmistakable) |
| ⭐ Star Fruit | +1 life (server-randomized, unpredictable spawn) |
| 🧲 Magnet Fruit | Steal 5 points from opponent (Versus only) |

### Social Layer
- Username validation — unique, case-insensitive, enforced server-side
- Global lobby chat
- Private player invites with accept/decline
- Game room chat before match starts
- Live online players list — updates in real time
- Leaderboard tracking wins per player
- Spectator mode

### Input
- **Webcam** — MediaPipe hand tracking, custom gesture classifier
- **Mouse cursor** — fallback for privacy or no webcam
- **Switch anytime** — toggle between webcam and mouse in the game room

---

## Architecture

```
CLIENT                          SERVER (Railway Cloud)
──────────────────────          ──────────────────────────────
Input Layer                     Tick-based game loop (30/sec)
  Webcam (MediaPipe)      ──→   Fruit spawner + physics
  OR Mouse cursor               Slice validator (who hit first)
  outputs (x, y, gesture)       Event logger (ms timestamps)
                                Latency tracker per client
Pygame Renderer           ←──   Broadcasts full game state
  Fruits + halves               
  Blade trail                   
  Juice particles               
  HUD (score, lives, ping)      
  Gesture label                 

Network Layer (TCP Sockets)
  Newline-delimited JSON
  Ping/pong every 2 seconds
```

**Key design principle:** The client never trusts its own slice detection. It only sends finger coordinates to the server. The server validates all slices and broadcasts the authoritative game state — the same architecture used in trading platforms and real-time financial systems.

---

## Tech Stack

| Technology | Used for |
|---|---|
| Python 3.11 | Core language |
| Pygame | Game rendering, UI |
| OpenCV | Webcam capture |
| MediaPipe | Hand landmark detection (21 points) |
| NumPy | Math, coordinate calculations |
| Socket (stdlib) | TCP networking |
| Threading (stdlib) | Concurrent client handling |
| Railway | Cloud server deployment |

---

## Getting Started

### Prerequisites
- Python 3.9+
- Webcam (optional — mouse mode available)

### Install
```bash
git clone https://github.com/JadF10/SliceWars.git
cd SliceWars
pip install pygame opencv-python mediapipe numpy
```

### Run
```bash
python main.py
```

The client connects to the live server at `acela.proxy.rlwy.net:46733` automatically. No local server needed.

### Run your own server (optional)
```bash
python server/server.py 5555
```

Then change `SERVER_HOST` and `SERVER_PORT` in `main.py` to `127.0.0.1` and `5555`.

---

## Project Structure

```
SliceWars/
├── client/
│   ├── input/
│   │   └── webcam.py          # Gesture classifier — Qualcomm signal
│   ├── screens/
│   │   ├── pre_lobby.py       # Username + connect
│   │   ├── lobby.py           # Online players, chat, invite
│   │   ├── game_room.py       # Mode select, ready up
│   │   ├── game.py            # Main game loop
│   │   └── results.py         # Winner, scores, rematch
│   ├── game/
│   │   ├── fruits.py          # Procedural fruit drawing (no image files)
│   │   ├── blade.py           # Slice trail rendering
│   │   ├── particles.py       # Juice splatter effects
│   │   ├── items.py           # Bombs, star fruit, magnet
│   │   └── hud.py             # Score, lives, ping, gesture HUD
│   └── network/
│       └── client.py          # TCP socket layer
├── server/
│   ├── server.py              # Main server — event-driven architecture
│   ├── game_logic.py          # Fruit physics, slice validation, scoring
│   └── leaderboard.py         # Win tracking, JSON persistence
├── shared/
│   └── protocol.py            # Message types, constants, builders
└── main.py                    # Entry point
```

---

## CV Talking Points

**For Murex (real-time systems):**
> "Built a real-time multiplayer system where the server is the single source of truth and clients only render state — the same architecture used in trading platforms. Every game event is timestamped in milliseconds and logged server-side, mirroring how financial systems track order book events."

**For Qualcomm (computer vision):**
> "Built a real-time gesture recognition pipeline processing webcam input at 30fps using geometric analysis of MediaPipe's 21 skeletal landmarks, with custom hand pose classification and measured input-to-action latency of 30–70ms."

**For both:**
> "Server deployed to cloud infrastructure — playable globally. Anyone clones the repo and runs python main.py to connect from anywhere in the world."

---

## Related Projects

- **[Python Arena](https://github.com/Rudri22/Python-Arena)** — Multiplayer snake battle game (EECE 350 Networks project) — the predecessor that taught the networking architecture applied here.

---

## Author

Jad Faddoul — Computer and Communications Engineering, American University of Beirut

*Built to demonstrate real-time systems and computer vision skills for internship applications at Murex and Qualcomm.*
