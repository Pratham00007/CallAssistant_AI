import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.config import PRACTICE_DIR

q_file = PRACTICE_DIR / "questions.csv"
with open(q_file, encoding='utf-8') as f:
    qs = {r['id']: r for r in csv.DictReader(f)}

ids = ['PQ0020', 'PQ0024', 'PQ0030', 'PQ0036', 'PQ0039', 'PQ0040', 'PQ0042', 'PQ0044', 'PQ0045', 'PQ0046', 'PQ0048', 'PQ0049', 'PQ0050', 'PQ0058', 'PQ0060']
for i in ids:
    r = qs[i]
    print(f"ID: {r['id']}")
    print(f"  Question: {r['question']}")
    print(f"  Gold Evidence: {r['gold_evidence']}")
    print(f"  Entities: {r['entities']}")
    print(f"  Notes: {r['notes']}")
    print("-" * 50)
