import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_demo_tool

print(import_demo_tool.count_words("SQL sql"))
