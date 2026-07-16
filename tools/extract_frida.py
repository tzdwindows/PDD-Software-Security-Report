# -*- coding: utf-8 -*-
import lzma
import shutil
import os
import sys

src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "frida", "frida-server-17.15.5-android-x86_64.xz")
dst = os.path.join(os.path.dirname(src), "frida-server-17.15.5-android-x86_64")

print("Source:", src)
print("Dest:", dst)
print("Source exists:", os.path.exists(src))

try:
    with lzma.open(src, 'rb') as f_in:
        with open(dst, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    print("SUCCESS! Size:", os.path.getsize(dst))
except Exception as e:
    print("FAILED:", type(e).__name__, str(e))
    # Try alternative: use subprocess to call external tools
    import subprocess
    # Try using tar
    result = subprocess.run(["tar", "-xf", src, "-C", os.path.dirname(src)], capture_output=True, text=True)
    print("tar result:", result.returncode, result.stdout, result.stderr)