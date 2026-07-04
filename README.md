# Dungeon of the Stars

Dungeon of the Stars is a text-based terminal roleplaying game engine governed by a hybrid system of deterministic mechanics and Large Language Models (LLMs). The game is set in the Star Wars universe and uses a simplified simulation of the Fantasy Flight Games (FFG) Star Wars RPG rules system.

The application features a command dashboard that reads and writes game states directly to a Markdown-based file system, acts as an in-universe judge for natural language commands, resolves skill checks using programmatic dice roll cancellation, and narrates outcomes dynamically.

---

## 1. System Architecture

The game loop is structured to achieve natural language command freedom while maintaining strict structural state validity through a Parser-Judge design:

1. **Command Input:** The player enters natural language instructions (e.g., "scan planetary surface" or "travel to hangar").
2. **Deterministic Guardrails:** Hard regex checks intercept strategic or game-skipping shortcuts (e.g., "win the game") and return immediate in-character operational refutations.
3. **LLM Parser-Judge:** Validates commands against location data and historical logs. It translates natural language intents into a structured JSON schema, specifying action types, movement vectors, background tasks, and required skill checks.
4. **Mechanical Skill Rolls:** If a skill check is flagged, the engine retrieves the player's characteristics and skill ranks from their Markdown sheet, constructs the FFG RPG dice pool, resolves rolls mathematically in Python code, and updates player strain or wounds.
5. **State Mutator:** Updates specific fields, checklists, and inventories across dynamic Markdown files in the file system and logs turn outputs to a persistent JSON history file.
6. **LLM Narrator:** Produces descriptive, atmospheric prose using the engine's deterministic results and dice outcomes.
7. **Terminal UI Display:** Renders a dashboard splitting the screen into player stats, task force escort ship metrics, and the scrolling tactical log.

---

## 2. Directory Structure

```
DungeonOfTheStars/
├── GameData/                         # Dynamic Game State Database
│   ├── Player Data/
│   │   ├── Command Staff/
│   │   │   └── Commander_Vandar_Kross.md  # XO character sheet
│   │   └── Commodore_Nimrod_Heros.md      # Player character sheet
│   ├── ShipData/
│   │   ├── The_Broken_Sunrise/
│   │   │   └── The_Broken_Sunrise.md      # Flagship manifest
│   │   └── [Other Escort Vessels...]      # Escort manifests
│   ├── Saves/
│   │   └── manual_save/              # Full database backups
│   └── game_history.json             # Chronological turn records
│
├── Game_info/                        # Static Scenario Databases
│   ├── items.md                      # Weapons and gear stats
│   ├── locations.md                  # Scenario locations and exits
│   └── skills.md                     # FFG skill-to-stat map
│
├── dice.py                           # FFG Symbol Dice Roller
├── md_db.py                          # Markdown State Sync Engine
├── llm_agent.py                      # LLM Parser & Narrator Client
├── game_engine.py                    # Game Loop Controller
└── dungeonofthestars.py                       # Console UI Client (Rich)
```

---

## 3. Gameplay Mechanics

### FFG RPG Dice Pools
The system manages dice checks programmatically. The pool is constructed based on:
* **Green Ability Dice & Yellow Proficiency Dice:** Calculated by upgrading a characteristic attribute score (e.g., Intellect) with a skill rank (e.g., Computers).
* **Purple Difficulty Dice & Red Challenge Dice:** Set by the task difficulty.
* **Setback and Boost Dice:** Added dynamically based on environment status.

Opposing symbols cancel out (Success cancels Failure; Advantage cancels Threat). Triumph and Despair are tracked independently to trigger critical narrative events.

### Markdown Database
Game state persists in human-readable Markdown files. The custom regex database writer matches and rewrites:
* Table entries (e.g., `| Wounds (Health) | 14 | [ 2 ] |`)
* Status checkmarks (e.g., `* **Hyperdrive:** [ ] Nominal | [X] Damaged`)
* Key-value parameters (e.g., `* **Credits:** [1000000]`)

---

## 4. Console Interface & Slash Commands

The interface divides terminal windows into panels for player attributes, fleet health, and narration. In addition to natural language inputs, the command prompt supports specific slash commands:
* `/settings`: Displays current configuration parameters and live instructions on how to update models, endpoints, or API keys.
* `/set <parameter> <value>`: Updates configurations (e.g., `/set model qwen2.5:3b` or `/set url http://localhost:11434`). Updates are saved to `config.json`.
* `/save`: Compiles and copies all live game states to `GameData/Saves/manual_save/`.
* `/back` or `/exit`: Returns to the main logging screen (from settings) or terminates the application (from game screen).

---

## 5. Setup and Execution

### Prerequisites
* Python 3.10 or higher
* Python package dependencies: `requests`, `rich`
* Ollama installed and running locally with the target model:
  ```bash
  ollama run qwen2.5:3b
  ```
  *Note: To run via cloud API instead, set the `GEMINI_API_KEY` environment variable.*

### Starting the Game
Run the command-line application from the repository root:
```bash
python3 dungeonofthestars.py
```
