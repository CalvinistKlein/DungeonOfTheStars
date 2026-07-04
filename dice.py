import random
import re
import sys

# Define the face distributions for each FFG Star Wars RPG die.
# Each face is represented as a list of symbol dictionaries.
# positive values are Success/Advantage, negative are Failure/Threat.
# Triumph and Despair are tracked separately and do not cancel out.

SUCCESS = {"success": 1}
DOUBLE_SUCCESS = {"success": 2}
ADVANTAGE = {"advantage": 1}
DOUBLE_ADVANTAGE = {"advantage": 2}
SUCCESS_ADVANTAGE = {"success": 1, "advantage": 1}

FAILURE = {"success": -1}
DOUBLE_FAILURE = {"success": -2}
THREAT = {"advantage": -1}
DOUBLE_THREAT = {"advantage": -2}
FAILURE_THREAT = {"success": -1, "advantage": -1}

TRIUMPH = {"success": 1, "triumph": 1}
DESPAIR = {"success": -1, "despair": 1}

LIGHT = {"light": 1}
DOUBLE_LIGHT = {"light": 2}
DARK = {"dark": 1}
DOUBLE_DARK = {"dark": 2}

BLANK = {}

DIE_FACES = {
    # Boost Die (Blue - d6)
    # 2 Blank, 1 Success, 1 Success+Advantage, 1 double-Advantage, 1 Advantage
    "b": [
        BLANK, BLANK,
        SUCCESS,
        SUCCESS_ADVANTAGE,
        DOUBLE_ADVANTAGE,
        ADVANTAGE
    ],
    
    # Setback Die (Black - d6)
    # 2 Blank, 2 Failure, 2 Threat
    "s": [
        BLANK, BLANK,
        FAILURE, FAILURE,
        THREAT, THREAT
    ],
    
    # Ability Die (Green - d8)
    # 1 Blank, 2 Success, 1 double-Success, 2 Advantage, 1 double-Advantage, 1 Success+Advantage
    "a": [
        BLANK,
        SUCCESS, SUCCESS,
        DOUBLE_SUCCESS,
        ADVANTAGE, ADVANTAGE,
        DOUBLE_ADVANTAGE,
        SUCCESS_ADVANTAGE
    ],
    
    # Difficulty Die (Purple - d8)
    # 1 Blank, 1 Failure, 1 double-Failure, 3 Threat, 1 double-Threat, 1 Failure+Threat
    "d": [
        BLANK,
        FAILURE,
        DOUBLE_FAILURE,
        THREAT, THREAT, THREAT,
        DOUBLE_THREAT,
        FAILURE_THREAT
    ],
    
    # Proficiency Die (Yellow - d12)
    # 1 Blank, 2 Success, 2 double-Success, 1 Advantage, 3 Success+Advantage, 2 double-Advantage, 1 Triumph
    "p": [
        BLANK,
        SUCCESS, SUCCESS,
        DOUBLE_SUCCESS, DOUBLE_SUCCESS,
        ADVANTAGE,
        SUCCESS_ADVANTAGE, SUCCESS_ADVANTAGE, SUCCESS_ADVANTAGE,
        DOUBLE_ADVANTAGE, DOUBLE_ADVANTAGE,
        TRIUMPH
    ],
    
    # Challenge Die (Red - d12)
    # 1 Blank, 2 Failure, 2 double-Failure, 2 Threat, 2 Failure+Threat, 2 double-Threat, 1 Despair
    "c": [
        BLANK,
        FAILURE, FAILURE,
        DOUBLE_FAILURE, DOUBLE_FAILURE,
        THREAT, THREAT,
        FAILURE_THREAT, FAILURE_THREAT,
        DOUBLE_THREAT, DOUBLE_THREAT,
        DESPAIR
    ],
    
    # Force Die (White - d12)
    # 6 Dark, 1 double-Dark, 2 Light, 3 double-Light
    "f": [
        DARK, DARK, DARK, DARK, DARK, DARK,
        DOUBLE_DARK,
        LIGHT, LIGHT,
        DOUBLE_LIGHT, DOUBLE_LIGHT, DOUBLE_LIGHT
    ]
}

def roll_die(die_type):
    """Rolls a single die and returns the raw face dictionary."""
    die_type = die_type.lower()
    if die_type not in DIE_FACES:
        raise ValueError(f"Unknown die type: '{die_type}'. Choose from b, s, a, d, p, c, f.")
    return random.choice(DIE_FACES[die_type])

def roll_pool(pool_str):
    """
    Parses a dice pool string and rolls all dice, returning the net results.
    
    pool_str format can be like: 'aabdd' (2 Ability, 1 Boost, 2 Difficulty)
    or space-separated count-type pairs: '2a 1b 2d'
    """
    # Clean pool string
    pool_str = pool_str.strip()
    
    # Parse either shorthand 'aabdd' or format '2a 1b'
    dice_to_roll = []
    if ' ' in pool_str or any(char.isdigit() for char in pool_str):
        # Format: '2a 1b 2d'
        matches = re.findall(r"(\d+)?([abpdfcsABPDFCS])", pool_str)
        for count, die in matches:
            n = int(count) if count else 1
            dice_to_roll.extend([die.lower()] * n)
    else:
        # Format: 'aabdd'
        for char in pool_str:
            if char.lower() in DIE_FACES:
                dice_to_roll.append(char.lower())
    
    # Accumulate results
    raw_rolls = []
    totals = {
        "success": 0,
        "advantage": 0,
        "triumph": 0,
        "despair": 0,
        "light": 0,
        "dark": 0
    }
    
    for die in dice_to_roll:
        face = roll_die(die)
        raw_rolls.append((die, face))
        for symbol, amount in face.items():
            totals[symbol] += amount
            
    # Success/Failure cancellation is already handled implicitly because
    # Failure has {"success": -1}. The total['success'] is the net.
    # Advantage/Threat cancellation is handled implicitly because
    # Threat has {"advantage": -1}. The total['advantage'] is the net.
    
    net_success = totals["success"]
    net_advantage = totals["advantage"]
    
    resolved = {
        "success": max(0, net_success) if net_success > 0 else 0,
        "failure": max(0, -net_success) if net_success < 0 else 0,
        "advantage": max(0, net_advantage) if net_advantage > 0 else 0,
        "threat": max(0, -net_advantage) if net_advantage < 0 else 0,
        "triumph": totals["triumph"],
        "despair": totals["despair"],
        "light": totals["light"],
        "dark": totals["dark"],
        "is_success": net_success > 0,
        "dice_rolled": "".join(dice_to_roll)
    }
    
    return resolved, raw_rolls

def pretty_print_results(resolved):
    """Returns a user-friendly string of the roll result."""
    output = []
    # Success / Failure
    if resolved["is_success"]:
        output.append(f"SUCCESS ({resolved['success']} net success{'es' if resolved['success'] > 1 else ''})")
    else:
        output.append(f"FAILURE ({resolved['failure']} net failure{'s' if resolved['failure'] > 1 else ''})")
        
    # Advantage / Threat
    if resolved["advantage"] > 0:
        output.append(f"{resolved['advantage']} Advantage")
    elif resolved["threat"] > 0:
        output.append(f"{resolved['threat']} Threat")
        
    # Triumph / Despair
    if resolved["triumph"] > 0:
        output.append(f"★ TRIUMPH x{resolved['triumph']} ★")
    if resolved["despair"] > 0:
        output.append(f"☠ DESPAIR x{resolved['despair']} ☠")
        
    # Force Points
    if resolved["light"] > 0 or resolved["dark"] > 0:
        output.append(f"Force: {resolved['light']} Light / {resolved['dark']} Dark")
        
    return ", ".join(output)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dice.py <pool_string>")
        print("Example: python dice.py aabdd")
        print("Dice: a=Ability (green), p=Proficiency (yellow), b=Boost (blue), d=Difficulty (purple), c=Challenge (red), s=Setback (black), f=Force (white)")
        sys.exit(1)
        
    pool = sys.argv[1]
    res, raw = roll_pool(pool)
    print(f"Rolled: {res['dice_rolled']}")
    print(f"Result: {pretty_print_results(res)}")
