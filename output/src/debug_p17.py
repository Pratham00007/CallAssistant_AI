import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluator import Evaluator

ev = Evaluator()
# Run PC017 turn 1 to 4
ev.step3_agent.reset_state("PC017")
r1 = ev.step3_agent.respond("Hello, mujhe order ke baare mein help chahiye.", conversation_id="PC017", forced_turn=1)
r2 = ev.step3_agent.respond("Order number hai 3506 1733.", conversation_id="PC017", forced_turn=2)
r3 = ev.step3_agent.respond("Last four digits 2743 hain.", conversation_id="PC017", forced_turn=3)
r4 = ev.step3_agent.respond("Please ise cancel kar do.", conversation_id="PC017", forced_turn=4)

print("T4 Reply:", repr(r4['reply']))
print("T4 Decision:", r4['decision'])
