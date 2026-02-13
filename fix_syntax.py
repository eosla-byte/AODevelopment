
import os

file_path = r"a:\AO_DEVELOPMENT\AODevelopment\backend\services\finance\templates\project_detail.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# The broken string pattern. Since we don't know exact whitespace, we'll replace the split expression.
# Pattern: ({{ total_allocations.get(c.id, 0.0) } <newline/spaces> }
# We want: ({{ total_allocations.get(c.id, 0.0) }}

old_snippet = "total_allocations.get(c.id, 0.0) }\n"
# Looking at view_file, it breaks after the closing brace of the method call, then space, then brace?
# 548: ... get(c.id, 0.0) }
# 549: ... } - ...

import re
# Regex to find: {{ total_allocations.get(c.id, 0.0) }\s+}
pattern = r"\{\{\s*total_allocations\.get\(c\.id,\s*0\.0\)\s*\}\s+\}"

# Only one occurrence?
matches = re.findall(pattern, content)
print(f"Found {len(matches)} matches via regex.")

if len(matches) == 0:
    # Try literal match based on view_file observation
    # It might be: "total_allocations.get(c.id, 0.0) }\n                    }"
    # Let's try a broader replacement
    custom_pattern = r"(avail: 100 - \(\{\{ total_allocations\.get\(c\.id, 0\.0\) \})\s+\}\s+-\s+\(assignedCollabs"
    
    match = re.search(custom_pattern, content)
    if match:
        print("Found match with custom regex!")
        print(f"Match: {match.group(0)}")
        
        replacement = r"avail: 100 - ({{ total_allocations.get(c.id, 0.0) }} - (assignedCollabs"
        new_content = re.sub(custom_pattern, replacement, content)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("File updated successfully.")
    else:
        print("No match found. Dumping snippet around target area:")
        idx = content.find("total_allocations.get(c.id")
        if idx != -1:
            print(repr(content[idx:idx+100]))
else:
    # Safe replace
    new_content = re.sub(pattern, "{{ total_allocations.get(c.id, 0.0) }}", content)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("File updated with regex replace.")
