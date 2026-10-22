import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluator import check_must_include

reply = "You can cancel your order free of charge from the My Orders section in the app before it ships."
must_inc = "My Orders / app / free"

print("Test check_must_include:", check_must_include(reply, must_inc))
