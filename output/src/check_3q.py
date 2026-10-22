import csv
import sys
from pathlib import Path
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('Capstone_Project_Dataset_FTTT_2026/Capstone_Project_Dataset_FTTT_2026/practice/questions.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['id'] in ('PQ0037', 'PQ0051', 'PQ0053'):
            print(f"ID: {r['id']}")
            print(f"  Question: {r['question']}")
            print(f"  Decision: {r['expected_decision']} (acceptable: {r['acceptable_decisions']})")
            print(f"  Answerable: {r['answerable']}")
            print(f"  Must Include: {r['must_include']}")
            print(f"  Must Not Include: {r['must_not_include']}")
            print(f"  Gold Evidence: {r['gold_evidence']}")
            print("-" * 50)
