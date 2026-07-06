# Dungeon of the Stars 🌌

**Dungeon of the Stars** is a hybrid text-adventure roleplaying engine set in the Star Wars universe. It merges **deterministic codebase rules** with **Large Language Models (LLMs)** to create an atmospheric, consistent, and logically sound gameplay experience. 

The system implements a simplified, programmatic simulation of the **Fantasy Flight Games (FFG) Star Wars RPG** rules system, utilizing physical character sheets on disk, real-time dice cancellation mechanics, and long-term narrative memory.

---

## 🛠️ System Architecture

To avoid logical hallucinations (e.g., losing inventory, entering locked rooms, walking through walls), the game separates state management from storytelling:

```
                  ┌──────────────────────┐
                  │     Player Input     │
                  └──────────┬───────────┘
                             │ (Natural Language)
                             ▼
                  ┌──────────────────────┐
                  │    Terminal UI       │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │      LLM Parser      │ <── Translates intent to JSON
                  └──────────┬───────────┘
                             │
                             ▼
  ┌──────────────────────────┴──────────────────────────┐
  │                   Game Engine                       │
  │  • Reads/writes Markdown files (MarkdownDB)         │
  │  • Programmatic FFG Symbol Dice Rolls               │
  │  • Updates strain, wounds, credits & inventory      │
  └──────────────────────────┬──────────────────────────┘
                             │ (Raw state output & dice outcome)
                             ▼
                  ┌──────────────────────┐
                  │     LLM Narrator     │ <── RAG Lore DB Context Injection
                  └──────────┬───────────┘
                             │ (Rich thematic prose)
                             ▼
                  ┌──────────────────────┐
                  │    Terminal UI       │ <── Updates btop-style dashboard
                  └──────────────────────┘
```

---

## 📖 Key Systems

### 1. FFG RPG Dice Pools
The system manages dice checks programmatically. The pool is constructed based on:
* **Green Ability & Yellow Proficiency Dice:** Upgraded dynamically by comparing character attributes (e.g., Intellect) against skill ranks (e.g., Computers).
* **Purple Difficulty & Red Challenge Dice:** Set based on parser difficulty.
* **Setback & Boost Dice:** Appended depending on environmental or tactical states.
* **Symbol Resolution:** Successes cancel Failures, and Advantages cancel Threats. Triumphs and Despairs are tracked independently for major narrative events.

### 2. File-Based Markdown Database (`MarkdownDB`)
Active game states (attributes, checkmarks, ship hull trauma, inventories) are saved in human-readable Markdown files. The engine reads, parses, and commits mutations directly to these files, preserving formatting, layout, and comments.

### 3. Chronological Campaign Chronicle
To ensure the LLM remembers past encounters, dialogue choices, and plot progression over long sessions without bloating the VRAM or triggering repetition loops, a factual journal (`GameData/campaign_chronicle.md`) is maintained. A fast, low-temperature LLM Archivist appends bullet points after significant turns, which are injected back into all subsequent LLM calls.

### 4. Dynamic NPC Data Cards
When players interact with new or canonical characters, the engine dynamically generates a local FFG RPG character sheet (`.md`) under `GameData/NPC Data/` or `GameData/Player Data/Command Staff/` to track stats, role, and current health/strain.

---

## 📂 Directory Layout

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
│   ├── game_history.json             # Detailed turn logs
│   └── campaign_chronicle.md         # Factual narrative memory
│
├── Game_info/                        # Static Scenario Databases
│   ├── items.md                      # Weapons and gear stats
│   ├── locations.md                  # Scenario locations and exits
│   └── skills.md                     # FFG skill-to-stat map
│
├── KnowledgeBase/                    # Target directory for lore scraping
├── StarWars_Wookepedia_2026_07_06/   # Local ChromaDB Vector Store
│
├── dice.py                           # FFG Symbol Dice Roller
├── md_db.py                          # Markdown State Sync Engine
├── llm_agent.py                      # LLM Parser, Narrator & Archivist
├── game_engine.py                    # Game Loop Controller
├── rag_engine.py                     # Lore database indexer & searcher
├── parse_wookieepedia_dump.py        # Wikipedia XML bulk parser
├── lore_scraper.py                   # On-demand API web scraper
└── dungeonofthestars.py              # Console UI Client (Rich)
```

---

## 🚀 Setup & Execution

### Prerequisites
1. **Python 3.10+**
2. Python dependencies:
   ```bash
   pip install requests rich chromadb
   ```
3. **Ollama** installed and running locally with the target model:
   ```bash
   ollama run qwen2.5:3b
   ```
   *(Optional: To use cloud execution, set the `GEMINI_API_KEY` environment variable).*

### Run the game
Execute the main interface script:
```bash
python3 dungeonofthestars.py
```

---

## 📚 Wookieepedia Lore RAG Setup

The game features Retrieval-Augmented Generation (RAG). By embedding canon Star Wars data locally, the Narrator can generate lore-accurate descriptions, and the NPC generator can create realistic character sheets for canon figures.

You can seed your local ChromaDB vector database using one of two methods:

> [!TIP]
> Make sure `nomic-embed-text` is installed on your Ollama server before running ingestion:
> ```bash
> ollama pull nomic-embed-text
> ```

---

### Method A: Targeted On-Demand Scraper (Recommended / Faster)
This method queries the live Wookieepedia API directly for specific topics, sanitizes the articles, and ingests them. It is lightweight, requires minimal RAM, and builds a targeted dataset.

1. **Scrape specific articles:**
   Run `lore_scraper.py` passing the exact article title as a parameter:
   ```bash
   python3 lore_scraper.py "Lightsaber"
   python3 lore_scraper.py "TIE Interceptor"
   python3 lore_scraper.py "Sworinta"
   ```
   *This cleans the articles and saves them as text files in the `KnowledgeBase/` folder.*

2. **Ingest scraped files into ChromaDB:**
   Build embeddings and index the files into the vector database:
   ```bash
   python3 rag_engine.py
   ```

---

### Method B: Bulk XML Database Dump Ingestion (Offline / Complete)
This method processes the official Wookieepedia database backup dump to build a massive, fully offline, local encyclopedia.

1. **Download the Wookieepedia Database Dump:**
   * Go to the **[Wookieepedia Statistics Page](https://starwars.fandom.com/wiki/Special:Statistics)**.
   * Under the **Database Dumps** section, download the latest current articles archive (typically named `starwars_pages_current.xml.gz` or similar).
   * Extract the `.gz` file into your project directory.

2. **Run the Streaming XML Parser:**
   Run the parser utility pointing to the XML file. Because the database is massive, it is highly recommended to run it with a `--limit` option first to test the pipeline:
   ```bash
   # Ingest a test batch of 1,000 articles
   python3 parse_wookieepedia_dump.py starwars_pages_current.xml --limit 1000
   
   # Ingest the entire database (warning: takes several hours and significant disk space)
   python3 parse_wookieepedia_dump.py starwars_pages_current.xml
   ```
   *The parser uses a streaming XML pipeline to process pages efficiently and write batches to ChromaDB in parallel using multi-threading.*

---

## 🎮 Slash Commands
When inside the TUI dashboard, you can type natural language commands or use specific system overrides:
* `/settings` — Opens the dashboard showing active LLM configurations and server endpoints.
* `/set <param> <value>` — Modifies configurations (e.g., `/set model qwen2.5:3b` or `/set url http://localhost:11434`).
* `/save` — Automatically backs up all current Markdown sheets and logs to `GameData/Saves/manual_save/`.
* `/back` or `/exit` — Navigates back from settings or terminates the game.
