import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.config import KB_DIR, DATA_DIR, PRACTICE_DIR
from src.kb_loader import KnowledgeBase
from src.data_loader import DataLoader
from src.retriever import HybridRetriever

kb = KnowledgeBase(KB_DIR)
dl = DataLoader(DATA_DIR)
ret = HybridRetriever(kb, dl)

q_file = PRACTICE_DIR / "questions.csv"
with open(q_file, encoding='utf-8') as f:
    questions = list(csv.DictReader(f))

hit = 0
total = 0
for q in questions:
    gold_str = q['gold_evidence'].strip()
    if not gold_str:
        continue
    total += 1
    gold_items = [g.strip() for g in gold_str.split(' ; ') if g.strip()]
    results = [r[0] for r in ret.retrieve(q['question'], entities=q['entities'], top_k=6)]
    found = [g in results for g in gold_items]
    if all(found):
        hit += 1
    else:
        missing = [g for g in gold_items if g not in results]
        print(f"ID: {q['id']}, Missing: {missing}, Retrieved: {results[:5]}")

print(f"Retrieval Exact Gold Recall: {hit}/{total} ({hit/total*100:.1f}%)")
