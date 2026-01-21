
import os

def fix():
    path = r"c:\Users\arqui\.gemini\antigravity\scratch\AO_Development\backend\templates\project_detail.html"
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    # Use 'rb' to avoid newlines mess, then decode
    with open(path, 'rb') as f:
        raw = f.read()
    
    content = raw.decode('utf-8')
    lines = content.splitlines()
    
    found = False
    new_lines = []
    skip_next = False
    
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
            
        # Check for the specific broken split
        # We look for the line ending in `0.0) }` (maybe checking stripped)
        # And next line starting with `} -`
        
        stripped = line.strip()
        if 'avail: 100' in line and 'total_allocations.get(c.id, 0.0)' in line:
            # Check if it ends weirdly
            print(f"Inspecting line {i+1}: {line}")
            
            # Look ahead
            if i + 1 < len(lines):
                next_line = lines[i+1]
                print(f"Next line {i+2}: {next_line}")
                
                if 'assignedCollabs' in next_line and 'assignedCollabs' not in line:
                     # This confirms split
                     print("Found split! Fixing...")
                     
                     # Construct fixed line
                     # We want: 
                     # avail: 100 - ({{ total_allocations.get(c.id, 0.0) }} - (assignedCollabs["{{ c.id }}"] || 0))
                     
                     # Preserve indentation
                     indent = line[:line.find('avail')]
                     fixed = indent + 'avail: 100 - ({{ total_allocations.get(c.id, 0.0) }} - (assignedCollabs["{{ c.id }}"] || 0))'
                     
                     new_lines.append(fixed)
                     skip_next = True
                     found = True
                     continue

        new_lines.append(line)

    if found:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        print("File updated successfully.")
    else:
        print("Pattern not found. File might be already fixed?")

if __name__ == "__main__":
    fix()
