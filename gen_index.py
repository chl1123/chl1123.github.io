"""
生成index目录
"""

import os

for root, dirs, files in os.walk("docs"):
    # assets、en、__目录不生成index.md
    if "assets" in root or "en" in root or "__" in root:
        continue
    md_files = [f for f in files if f.endswith(".md")]
    if "index.md" not in md_files:
        with open(os.path.join(root, "index.md"), "w") as index_file:
            index_file.write("# Index\n\n")
            for file in md_files:
                if file != "index.md":
                    file_name = os.path.splitext(file)[0]
                    index_file.write(f"- [{file_name}]({file})\n")
