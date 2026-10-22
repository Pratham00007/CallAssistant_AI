import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.evaluator import Evaluator

evaluator = Evaluator()

print("=" * 60)
print("Evaluating Step 1 (Prompt-Only Baseline) vs Step 2 (Grounded RAG)")
print("=" * 60)
q_res = evaluator.evaluate_questions()

print(f"Total Questions: {q_res['total_questions']}")
print("\n--- STEP 1: Prompt-Only Baseline ---")
print(f"Decisions Correct: {q_res['step1']['decision_correct']}/{q_res['total_questions']} ({q_res['step1']['decision_correct']/q_res['total_questions']*100:.1f}%)")
print(f"Must-Include Passed: {q_res['step1']['must_include_passed']}/{q_res['total_questions']} ({q_res['step1']['must_include_passed']/q_res['total_questions']*100:.1f}%)")
print(f"Must-Not-Include Passed: {q_res['step1']['must_not_include_passed']}/{q_res['total_questions']} ({q_res['step1']['must_not_include_passed']/q_res['total_questions']*100:.1f}%)")
print(f"Overall Passed: {q_res['step1']['overall_correct']}/{q_res['total_questions']} ({q_res['step1']['overall_correct']/q_res['total_questions']*100:.1f}%)")

print("\n--- STEP 2: Grounded RAG Agent ---")
print(f"Decisions Correct: {q_res['step2']['decision_correct']}/{q_res['total_questions']} ({q_res['step2']['decision_correct']/q_res['total_questions']*100:.1f}%)")
print(f"Must-Include Passed: {q_res['step2']['must_include_passed']}/{q_res['total_questions']} ({q_res['step2']['must_include_passed']/q_res['total_questions']*100:.1f}%)")
print(f"Must-Not-Include Passed: {q_res['step2']['must_not_include_passed']}/{q_res['total_questions']} ({q_res['step2']['must_not_include_passed']/q_res['total_questions']*100:.1f}%)")
print(f"Overall Passed: {q_res['step2']['overall_correct']}/{q_res['total_questions']} ({q_res['step2']['overall_correct']/q_res['total_questions']*100:.1f}%)")
print(f"Gold Evidence Exact Recall: {q_res['step2']['gold_evidence_recall']:.1f}%")

print("\n" + "=" * 60)
print("Evaluating Step 3: Multi-Turn Support Conversations")
print("=" * 60)
c_res = evaluator.evaluate_conversations()
print(f"Total Conversations: {c_res['total_conversations']}")
print(f"Total Turns: {c_res['total_turns']}")
print(f"Decisions Correct: {c_res['decision_correct']}/{c_res['total_turns']} ({c_res['decision_correct']/c_res['total_turns']*100:.1f}%)")
print(f"Must-Include Passed: {c_res['must_include_passed']}/{c_res['total_turns']} ({c_res['must_include_passed']/c_res['total_turns']*100:.1f}%)")
print(f"Must-Not-Include Passed: {c_res['must_not_include_passed']}/{c_res['total_turns']} ({c_res['must_not_include_passed']/c_res['total_turns']*100:.1f}%)")
print(f"Tool Calls Correct: {c_res['tool_calls_correct']}/{c_res['total_turns']} ({c_res['tool_calls_correct']/c_res['total_turns']*100:.1f}%)")
print(f"Overall Turns Passed: {c_res['overall_turns_passed']}/{c_res['total_turns']} ({c_res['overall_turns_passed']/c_res['total_turns']*100:.1f}%)")
