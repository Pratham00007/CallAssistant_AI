import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('Capstone_Project_Dataset_FTTT_2026/Capstone_Project_Dataset_FTTT_2026/practice/conversations.csv', encoding='utf-8') as f:
    c_rows = [r for r in csv.DictReader(f) if r['conversation_id'] in ('PC017', 'PC018')]

with open('Capstone_Project_Dataset_FTTT_2026/Capstone_Project_Dataset_FTTT_2026/data/orders.csv', encoding='utf-8') as f:
    orders = {r['order_id']: r for r in csv.DictReader(f)}

for r in c_rows:
    oid = r['order_id']
    o = orders.get(oid, {})
    print(f"CID: {r['conversation_id']} | T{r['turn']} | OID: {oid} (status: {o.get('status')}) | Dec: {r['expected_decision']} | MustInc: {r['must_include']} | Msg: {r['customer_message']}")
