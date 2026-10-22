import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('Capstone_Project_Dataset_FTTT_2026/Capstone_Project_Dataset_FTTT_2026/practice/conversations.csv', encoding='utf-8') as f:
    turns = list(csv.DictReader(f))

from collections import defaultdict
convs = defaultdict(list)
for t in turns:
    convs[t['conversation_id']].append(t)

for cid in sorted(convs.keys())[:10]:
    print(f"=== Conversation {cid} (scenario: {convs[cid][0]['scenario']}, order: {convs[cid][0]['order_id']}) ===")
    for t in convs[cid]:
        print(f"  T{t['turn']} | dec={t['expected_decision']} | tools={t['expected_tool_calls']} | must_inc={t['must_include']} | msg: {t['customer_message']}")
