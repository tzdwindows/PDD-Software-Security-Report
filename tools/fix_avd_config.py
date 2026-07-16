# -*- coding: utf-8 -*-
import os

avd_dir = os.path.join(os.path.expanduser("~"), ".android", "avd", "pdd_analysis.avd")
config_path = os.path.join(avd_dir, "config.ini")

print(f"Reading: {config_path}")
with open(config_path, "r") as f:
    content = f.read()

# Remove problematic skin settings and replace with generic ones
new_lines = []
for line in content.split("\n"):
    if "skin.name" in line or "skin.path" in line or "skin.dynamic" in line:
        continue
    if line.startswith("hw.device.name"):
        new_lines.append("hw.device.name=generic_x86_64")
        continue
    new_lines.append(line)

# Add proper skin settings
new_lines.append("skin.name=1080x1920")
new_lines.append("skin.path=_no_skin")

new_content = "\n".join(new_lines)

with open(config_path, "w") as f:
    f.write(new_content)

print("Config fixed!")
print("New config:")
print(new_content[-500:])