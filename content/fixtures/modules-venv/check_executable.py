import sys
from pathlib import Path

exe = Path(sys.executable)
print(exe.is_absolute() and exe.exists())
