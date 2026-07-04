import os
import re

class MarkdownDB:
    """
    A bidirectional Markdown database parser and writer.
    Reads player sheets and ship manifest markdown files into python dicts,
    and updates them while preserving formatting, comments, and structure.
    """

    @staticmethod
    def read_file(file_path):
        """
        Reads a markdown file and extracts all variables from tables,
        lists, and checklists.
        
        Returns a dictionary of extracted variables:
        {
            "fields": { "Wounds (Health)": "12", "Credits": "1000", ... },
            "checklists": { "Hyperdrive": "Nominal", "Operational Status": "Active", ... }
        }
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        data = {
            "fields": {},
            "checklists": {}
        }
        
        for line in lines:
            line_str = line.strip()
            
            # 1. Parse checklist line: * **Key:** [ ] Opt1 | [X] Opt2 | [ ] Opt3
            if line_str.startswith("*") and "[" in line_str and "|" in line_str:
                # Extract key (note colon inside bold text: **Key:**)
                key_match = re.match(r"^\*\s+\*\*([^*]+):\*\*\s*", line_str)
                if key_match:
                    key = key_match.group(1).strip()
                    remainder = line_str[key_match.end():]
                    # Find all checklist items like [X] Nominal
                    items = re.findall(r"\[([ xX]*?)\]\s*([^|]+)", remainder)
                    for checked, val in items:
                        val = val.strip()
                        if checked.strip().lower() in ("x", "1", "true"):
                            data["checklists"][key] = val
                            
            # 2. Parse simple brackets line: * **Key:** [value] / details
            elif line_str.startswith("*") and "[" in line_str:
                key_match = re.match(r"^\*\s+\*\*([^*]+):\*\*\s*", line_str)
                if key_match:
                    key = key_match.group(1).strip()
                    remainder = line_str[key_match.end():]
                    bracket_match = re.search(r"\[(.*?)\]", remainder)
                    if bracket_match:
                        data["fields"][key] = bracket_match.group(1).strip()
                        
            # 3. Parse non-bracketed simple list line: * **Key:** value
            elif line_str.startswith("*") and ":" in line_str:
                key_match = re.match(r"^\*\s+\*\*([^*]+):\*\*\s*(.*)$", line_str)
                if key_match:
                    key = key_match.group(1).strip()
                    val = key_match.group(2).strip()
                    # Skip if it is part of a list of sub-items without values
                    if val and not val.startswith("*") and "[" not in val:
                        data["fields"][key] = val
                        
            # 4. Parse table row with brackets: | **Wounds (Health)** | 0 | [ ] |
            elif line_str.startswith("|") and "[" in line_str and "]" in line_str:
                cols = [c.strip() for c in line_str.split("|")[1:-1]]
                if len(cols) >= 2:
                    key = cols[0].replace("**", "").strip()
                    for col in cols[1:]:
                        bracket_match = re.search(r"\[(.*?)\]", col)
                        if bracket_match:
                            data["fields"][key] = bracket_match.group(1).strip()
                            break
                            
        return data

    @staticmethod
    def write_file(file_path, updates):
        """
        Updates a markdown file with new values.
        
        updates is a dict:
        {
            "fields": { "Wounds (Health)": "12", "Credits": "1000", ... },
            "checklists": { "Hyperdrive": "Nominal", ... }
        }
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        fields_to_update = updates.get("fields", {})
        checklists_to_update = updates.get("checklists", {})
        
        for line in lines:
            line_str = line.strip()
            updated = False
            
            # 1. Update checklist line
            if line_str.startswith("*") and "[" in line_str and "|" in line_str:
                key_match = re.match(r"^\*\s+\*\*([^*]+):\*\*\s*", line_str)
                if key_match:
                    key = key_match.group(1).strip()
                    if key in checklists_to_update:
                        target_val = checklists_to_update[key]
                        remainder = line_str[key_match.end():]
                        
                        # Re-build checklist options
                        parts = remainder.split("|")
                        new_parts = []
                        for part in parts:
                            opt_match = re.search(r"\[([ xX]*?)\]\s*(.*)", part)
                            if opt_match:
                                opt_label = opt_match.group(2).strip()
                                is_target = (opt_label.lower() == target_val.lower())
                                new_box = "[X]" if is_target else "[ ]"
                                new_parts.append(f" {new_box} {opt_label} ")
                            else:
                                new_parts.append(part)
                                
                        indent = line[:line.find("*")]
                        line = f"{indent}*   **{key}:**{'|'.join(new_parts).rstrip()}\n"
                        updated = True
                        
            # 2. Update simple brackets line
            elif line_str.startswith("*") and "[" in line_str:
                key_match = re.match(r"^\*\s+\*\*([^*]+):\*\*\s*", line_str)
                if key_match:
                    key = key_match.group(1).strip()
                    if key in fields_to_update:
                        new_val = fields_to_update[key]
                        indent = line[:line.find("*")]
                        remainder = line_str[key_match.end():]
                        new_remainder = re.sub(r"\[.*?\]", f"[{new_val}]", remainder, count=1)
                        line = f"{indent}*   **{key}:** {new_remainder}\n"
                        updated = True
                        
            # 3. Update non-bracketed simple list line
            elif line_str.startswith("*") and ":" in line_str:
                key_match = re.match(r"^\*\s+\*\*([^*]+):\*\*\s*(.*)$", line_str)
                if key_match:
                    key = key_match.group(1).strip()
                    val = key_match.group(2).strip()
                    if key in fields_to_update and val and not val.startswith("*") and "[" not in val:
                        new_val = fields_to_update[key]
                        indent = line[:line.find("*")]
                        line = f"{indent}*   **{key}:** {new_val}\n"
                        updated = True
                        
            # 4. Update table row
            elif line_str.startswith("|") and "[" in line_str and "]" in line_str:
                cols = [c.strip() for c in line_str.split("|")[1:-1]]
                if len(cols) >= 2:
                    key = cols[0].replace("**", "").strip()
                    if key in fields_to_update:
                        new_val = fields_to_update[key]
                        new_cols = []
                        for i, col in enumerate(cols):
                            if i == 0:
                                new_cols.append(col)
                            else:
                                if "[" in col and "]" in col:
                                    new_col = re.sub(r"\[.*?\]", f"[ {new_val} ]", col)
                                    new_cols.append(new_col)
                                else:
                                    new_cols.append(col)
                        line = "| " + " | ".join(new_cols) + " |\n"
                        updated = True
                        
            new_lines.append(line)
            
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)


def get_all_state_files(data_dir):
    """
    Returns a list of all markdown state files in the GameData directory.
    """
    state_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".md"):
                state_files.append(os.path.join(root, file))
    return state_files
