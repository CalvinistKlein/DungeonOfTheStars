"""
npc_brains.py — Persistent "brain" layer for DungeonOfTheStars NPCs.

Architecture (Speed-first config):
  - DIRECTOR  (qwen2.5:3b) : picks which NPCs are physically in-scene each turn.
  - NARRATOR  (qwen2.5:3b) : writes the prose, grounded by the selected brains.
  - PARSER   (gary_gigax)  : mechanics / state mutations (unchanged).
  - BRAIN    (VibeThinker)  : DEFERRED memory consolidation, runs off the hot
                              path and is evicted from VRAM afterwards.

Isolation guarantee: context for the narrator is rebuilt from scratch every
turn and contains ONLY the brains of NPCs the director selected this turn.
No brain text from a non-selected NPC can leak into the prompt, and history
stores narration only (never raw brain contents).
"""
import os
import re
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(BASE_DIR, "GameData", "NPC Brains")

# ----------------------------------------------------------------------------
# Static registry of the core cast. Brains are seeded on disk on first use.
# id must be snake_case and match the ids the director is asked to return.
# ----------------------------------------------------------------------------
REGISTRY = {
    "aris_thorne":   {"name": "Aris Thorne",   "role": "First Mate",            "faction": "Imperial Navy",        "where": "on the bridge / command decks of the Broken Sunrise", "aboard": True},
    "vandar_kross":  {"name": "Vandar Kross",  "role": "Commander / Liaison",   "faction": "Imperial Navy",        "where": "on the bridge with the Commodore", "aboard": True},
    "mek":           {"name": "Mek",           "role": "Engineering Droid",     "faction": "ISD Broken Sunrise",   "where": "in Engineering / where the Commodore is working", "aboard": True},
    "doctor_lyn":    {"name": "Doctor Lyn",    "role": "Ship Doctor",           "faction": "Imperial Navy",        "where": "in the medbay unless summoned", "aboard": True},
    "titus_thul":    {"name": "Titus Thul",    "role": "Chief Engineer",        "faction": "Imperial Navy",        "where": "in Engineering", "aboard": True},
    "inquisitor":    {"name": "The Inquisitor","role": "Imperial Inquisitor",   "faction": "Imperial Inquisition", "where": "present only when meeting the Commodore privately", "aboard": True},
    "governor_vess": {"name": "Governor Vess", "role": "Planetary Governor",    "faction": "Sworinta IV",          "where": "PLANETSIDE on Sworinta IV — NOT aboard the ship", "aboard": False},
    "shadow_cultist":{"name": "Shadow Cultist","role": "Sith Cult Operative",   "faction": "Shadow Cult",          "where": "OFF-SHIP, reachable only via encrypted comms", "aboard": False},
}

SEED_BRAINS = {
    "aris_thorne": (
        "# Brain: Aris Thorne (First Mate)\n"
        "- Loyal Imperial officer; serves directly under the Commodore on the ISD Broken Sunrise.\n"
        "- Professional, by-the-book, trusts the chain of command.\n"
        "- Believes the distress signal is from a derelict warship (does NOT know it is a Sith beacon).\n"
        "- Attitude: dutiful, mildly wary of Commander Kross.\n"
    ),
    "vandar_kross": (
        "# Brain: Vandar Kross (Commander / Liaison)\n"
        "- The Commodore's second-in-command; charismatic but politically slippery.\n"
        "- Publicly loyal; privately maintains side deals (e.g. with Governor Vess).\n"
        "- Owes the Commodore 200 credits from a prior smuggling job.\n"
        "- Knows the Commodore hunts the Shadow Cult.\n"
        "- Attitude: friendly front, secretly self-interested; will not openly betray without leverage.\n"
    ),
    "mek": (
        "# Brain: Mek (Engineering Droid)\n"
        "- Custodian of the Broken Sunrise engineering decks.\n"
        "- Speaks in clipped, literal droid cadence.\n"
        "- Reports coolant, reactor, and hull status plainly.\n"
        "- Attitude: neutral, duty-bound to ship integrity.\n"
    ),
    "doctor_lyn": (
        "# Brain: Doctor Lyn (Ship Doctor)\n"
        "- Chief medical officer of the Broken Sunrise.\n"
        "- Calm, clinical, protective of the crew's wellbeing.\n"
        "- Attitude: professional; intervenes on wounds/strain matters.\n"
    ),
    "titus_thul": (
        "# Brain: Titus Thul (Chief Engineer)\n"
        "- Runs the engineering department under Mek's oversight.\n"
        "- Reports hyperdrive and subsystem status.\n"
        "- Attitude: gruff, practical.\n"
    ),
    "inquisitor": (
        "# Brain: The Inquisitor\n"
        "- Imperial Inquisitor attached to the operation.\n"
        "- ONE of only two who know the signal is an ancient Sith beacon (the Commodore is the other).\n"
        "- Speaks to the Commodore privately / via encrypted channels about the artifact's true nature.\n"
        "- Attitude: intense, secretive, expects absolute discretion.\n"
    ),
    "governor_vess": (
        "# Brain: Governor Vess (Sworinta IV)\n"
        "- Planetary governor; administrates the system.\n"
        "- Believes the signal is a derelict distress call.\n"
        "- Has a quiet side arrangement with Commander Kross.\n"
        "- Attitude: officious, self-preserving.\n"
    ),
    "shadow_cultist": (
        "# Brain: Shadow Cultist (Sith Cult)\n"
        "- Operative of the Shadow Cult that guards the Sith beacon.\n"
        "- Communicates via encrypted comms; rarely physically aboard.\n"
        "- Hostile to the Imperial operation; seeks to protect the beacon.\n"
        "- Attitude: hostile, duplicitous.\n"
    ),
}


def _ensure_dir():
    os.makedirs(BRAIN_DIR, exist_ok=True)


def brain_path(npc_id):
    return os.path.join(BRAIN_DIR, f"{npc_id}.md")


def load_brain(npc_id):
    """Return brain text for an NPC, seeding it from REGISTRY if absent."""
    _ensure_dir()
    p = brain_path(npc_id)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    if npc_id in SEED_BRAINS:
        save_brain(npc_id, SEED_BRAINS[npc_id])
        return SEED_BRAINS[npc_id]
    # Unknown NPC: create a minimal brain so it can still participate.
    meta = REGISTRY.get(npc_id, {"name": npc_id.replace("_", " ").title(),
                                 "role": "NPC", "faction": "Unknown"})
    seed = (f"# Brain: {meta['name']} ({meta['role']})\n"
            f"- Faction: {meta['faction']}.\n- No established history yet.\n")
    save_brain(npc_id, seed)
    return seed


def save_brain(npc_id, text):
    _ensure_dir()
    with open(brain_path(npc_id), "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")


def append_turn(npc_id, event_text):
    """Append a raw turn event to the NPC's memory log (pre-compaction)."""
    existing = load_brain(npc_id)
    combined = f"{existing}\n\n## Turn Event (raw)\n{event_text.strip()}\n"
    save_brain(npc_id, combined)


def _strip_think(text):
    # Remove closed <think>...</think> reasoning blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Remove any dangling/unclosed <think> ... to end of string (truncated CoT)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL).strip()
    return text


def director_select(scene_text, agent, model=None):
    """
    Ask the director model which registered NPCs are physically in-scene.
    Returns a list of NPC ids (subset of REGISTRY keys). Robust to bad JSON.
    """
    model = model or getattr(agent, "director_model", None) or agent.narrator_model
    # Only NPCs aboard the ship are eligible to be in-scene. Off-site NPCs
    # (planetside governor, off-ship cultist) are structurally excluded so the
    # director cannot leak them into the prompt.
    candidates = {nid: r for nid, r in REGISTRY.items() if r.get("aboard", True)}
    roster = "\n".join(
        f"  - {nid}: {r['name']} ({r['role']})"
        for nid, r in candidates.items()
    )
    prompt = (
        "You are the Scene Director for a Star Wars tactical RPG. "
        "The NPCs listed in the ROSTER are all aboard the ship and eligible to appear. "
        "Given the SCENE description, output ONLY a JSON array of the NPC ids that are "
        "PHYSICALLY PRESENT in THIS specific scene right now (e.g. on the bridge, in the "
        "room, or directly interacting). Exclude the player (the Commodore). If none are "
        "present, output []. Respond with the JSON array and nothing else.\n\n"
        f"ROSTER (aboard, eligible):\n{roster}\n\n"
        f"SCENE:\n{scene_text}\n\n"
        "JSON array of in-scene NPC ids:"
    )
    try:
        raw = agent.ask_model(prompt, model, num_predict=200)
    except Exception as e:
        print(f"[director] select failed: {e}")
        return []
    raw = _strip_think(raw)
    # Extract a JSON list
    s = raw.find("[")
    e = raw.rfind("]")
    if s == -1 or e == -1 or e < s:
        return []
    try:
        ids = json.loads(raw[s:e + 1])
    except Exception:
        return []
    if not isinstance(ids, list):
        return []
    # Restrict to known registry ids; ignore garbage
    return [str(i) for i in ids if str(i) in REGISTRY]


def compact_brain(npc_id, agent, model=None):
    """
    Consolidate an NPC's (possibly verbose) brain into a compact memory using
    the BRAIN model. Writes the result back to disk. Runs DEFERRED/off-path.
    """
    model = model or getattr(agent, "brain_model", None) or agent.narrator_model
    current = load_brain(npc_id)
    prompt = (
        "You are a memory consolidator for an NPC in a Star Wars RPG. "
        "Given the NPC's CURRENT memory and the NEW events from the latest turn, "
        "produce an UPDATED, compact memory in Markdown (at most 12 short bullet "
        "lines or sections). PRESERVE: identity, relationships, debts, allegiances, "
        "attitudes, current location, and any new concrete facts. DROP transient "
        "noise and duplicated turn-event headers. Output ONLY the updated memory, "
        "no commentary or code fences.\n\n"
        f"CURRENT MEMORY:\n{current}\n\n"
        "Produce the updated compact memory now:"
    )
    try:
        updated = agent.ask_model(prompt, model, num_predict=1500)
        updated = _strip_think(updated)
        if updated:
            save_brain(npc_id, updated)
            return updated
    except Exception as e:
        print(f"[brain] compact failed for {npc_id}: {e}")
    return current


def assemble_context(selected_ids):
    """
    Build the narrator's private brain context from ONLY the selected NPC ids.
    Returns (context_string, list_of_in_scene_names).
    Isolation: only selected ids are included; non-selected brains never appear.
    """
    blocks = []
    names = []
    for nid in selected_ids:
        if nid not in REGISTRY:
            continue
        brain = load_brain(nid)
        names.append(REGISTRY[nid]["name"])
        blocks.append(f"<<BRAIN: {nid}>>\n{brain}\n<</BRAIN>>")
    if not blocks:
        return "", []
    ctx = (
        "NPC PRIVATE BRAINS (grounding context for in-scene NPCs ONLY — use these "
        "to make each NPC's words and reactions consistent with their history, "
        "relationships, debts, and secrets; do NOT reveal these notes to the player):\n\n"
        + "\n\n".join(blocks)
    )
    return ctx, names


def assert_isolation(context, selected_ids):
    """Defensive check: no non-selected brain id may appear in the context."""
    for nid in REGISTRY:
        if nid in selected_ids:
            continue
        if f"<<BRAIN: {nid}" in context or f"<<BRAIN:{nid}" in context:
            return False, nid
    return True, None
