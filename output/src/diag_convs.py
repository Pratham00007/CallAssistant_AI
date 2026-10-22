import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.evaluator import Evaluator, check_must_include, check_must_not_include

ev = Evaluator()
with open('Capstone_Project_Dataset_FTTT_2026/Capstone_Project_Dataset_FTTT_2026/practice/conversations.csv', encoding='utf-8') as f:
    turns = list(csv.DictReader(f))

from collections import defaultdict
convs = defaultdict(list)
for t in turns:
    convs[t['conversation_id']].append(t)

print("Checking conversation discrepancies:")
count = 0
for cid, t_list in convs.items():
    ev.step3_agent.reset_state(cid)
    for t in sorted(t_list, key=lambda x: int(x['turn'])):
        turn_num = int(t['turn'])
        msg = t['customer_message']
        exp_dec = t['expected_decision']
        must_inc = t.get('must_include', '')
        must_not = t.get('must_not_include', '')
        exp_tools = t.get('expected_tool_calls', '').strip()

        res = ev.step3_agent.respond(msg, conversation_id=cid, forced_turn=turn_num)
        reply = res['reply']
        dec = res['decision']
        act_tools = res['tool_calls']

        dec_ok = (dec == exp_dec)
        inc_ok = check_must_include(reply, must_inc)
        not_ok = check_must_not_include(reply, must_not)
        tools_ok = (any(exp_tools in a for a in act_tools) if exp_tools else len(act_tools) == 0)

        if not (dec_ok and inc_ok and not_ok and tools_ok):
            count += 1
            if count <= 15:
                print(f"[{cid} T{turn_num}] msg: {msg[:35]}")
                if not dec_ok: print(f"   Dec: act={dec} vs exp={exp_dec}")
                if not inc_ok: print(f"   Must inc miss: '{must_inc}'")
                if not not_ok: print(f"   Must not miss: '{must_not}'")
                if not tools_ok: print(f"   Tools: act={act_tools} vs exp='{exp_tools}'")

print(f"Total turn discrepancies: {count}")
