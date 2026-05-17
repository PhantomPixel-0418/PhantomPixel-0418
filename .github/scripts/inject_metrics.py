import re

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

with open("metrics-text.md", "r", encoding="utf-8") as f:
    metrics_text = f.read()

# 替换标记块
pattern = r"<!-- METRICS-TEXT-START -->.*<!-- METRICS-TEXT-END -->"
replacement = metrics_text.strip()
new_readme = re.sub(pattern, replacement, readme, flags=re.DOTALL)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(new_readme)