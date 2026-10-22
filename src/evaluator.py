"""Evaluation Harness for ZentroMart VoiceOps 2026.
Runs quantitative benchmarking across practice/questions.csv (Step 1 vs Step 2)
and practice/conversations.csv (Step 3 Multi-Turn Agent).
Computes exact metrics: Decision Accuracy, Must-Include Compliance, Must-Not-Include Violations,
Retrieval Quality, and Tool Call Precision.
"""
import csv
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict

from .config import PRACTICE_DIR, KB_DIR, DATA_DIR
from .kb_loader import KnowledgeBase
from .data_loader import DataLoader
from .retriever import HybridRetriever
from .policy_engine import PolicyEngine
from .tools_adapter import ToolsAdapter
from .conversation_agent import ConversationAgent
from .step1_baseline import Step1BaselineAgent
from .step2_rag import Step2RAGAgent

def check_must_include(text: str, must_include_str: str) -> bool:
    """Checks if text contains all required clauses.
    Clauses are separated by ' ; '. Within a clause, ' / ' separates acceptable alternatives.
    """
    if not must_include_str or not must_include_str.strip():
        return True
    t_lower = text.lower()
    clauses = [c.strip() for c in must_include_str.split(' ; ') if c.strip()]
    for clause in clauses:
        alternatives = [alt.strip().lower() for alt in clause.split(' / ') if alt.strip()]
        if not any(alt in t_lower for alt in alternatives):
            return False
    return True

def check_must_not_include(text: str, must_not_include_str: str) -> bool:
    """Checks if text contains ANY forbidden strings (separated by ' ; ')."""
    if not must_not_include_str or not must_not_include_str.strip():
        return True
    t_lower = text.lower()
    forbidden_list = [f.strip().lower() for f in must_not_include_str.split(' ; ') if f.strip()]
    for f in forbidden_list:
        if f in t_lower:
            return False  # Failed
    return True

class Evaluator:
    def __init__(self):
        self.kb = KnowledgeBase(KB_DIR)
        self.data_loader = DataLoader(DATA_DIR)
        self.retriever = HybridRetriever(self.kb, self.data_loader)
        self.policy_engine = PolicyEngine(self.data_loader)
        self.tools_adapter = ToolsAdapter()

        self.step1_agent = Step1BaselineAgent()
        self.step2_agent = Step2RAGAgent(self.kb, self.data_loader, self.retriever, self.policy_engine)
        self.step3_agent = ConversationAgent(self.kb, self.data_loader, self.retriever, self.policy_engine, self.tools_adapter)

    def evaluate_questions(self) -> Dict[str, Any]:
        """Evaluates Step 1 vs Step 2 on practice/questions.csv."""
        q_path = PRACTICE_DIR / "questions.csv"
        with open(q_path, "r", encoding="utf-8") as f:
            questions = list(csv.DictReader(f))

        results = {
            "total_questions": len(questions),
            "step1": {
                "decision_correct": 0,
                "must_include_passed": 0,
                "must_not_include_passed": 0,
                "overall_correct": 0,
                "gold_evidence_recall": 0.0,
            },
            "step2": {
                "decision_correct": 0,
                "must_include_passed": 0,
                "must_not_include_passed": 0,
                "overall_correct": 0,
                "gold_evidence_recall": 0.0,
            },
            "details": [],
        }

        s2_gold_hits = 0
        s2_gold_total = 0

        for q in questions:
            qid = q["id"]
            question_text = q["question"]
            lang = q["language"]
            entities = q.get("entities")
            exp_decision = q["expected_decision"]
            acc_decisions = [d.strip() for d in q.get("acceptable_decisions", "").split(";") if d.strip()] or [exp_decision]
            must_inc = q.get("must_include", "")
            must_not = q.get("must_not_include", "")
            gold_ev_str = q.get("gold_evidence", "").strip()
            gold_items = [g.strip() for g in gold_ev_str.split(" ; ") if g.strip()] if gold_ev_str else []

            # Step 1 Evaluation
            res1 = self.step1_agent.answer_question(question_text, language=lang)
            s1_dec = res1["decision"]
            s1_reply = res1["reply"]
            s1_dec_ok = (s1_dec in acc_decisions)
            s1_inc_ok = check_must_include(s1_reply, must_inc)
            s1_not_ok = check_must_not_include(s1_reply, must_not)
            s1_pass = s1_dec_ok and s1_inc_ok and s1_not_ok

            if s1_dec_ok: results["step1"]["decision_correct"] += 1
            if s1_inc_ok: results["step1"]["must_include_passed"] += 1
            if s1_not_ok: results["step1"]["must_not_include_passed"] += 1
            if s1_pass: results["step1"]["overall_correct"] += 1

            # Step 2 Evaluation
            res2 = self.step2_agent.answer_question(question_text, language=lang, entities=entities)
            s2_dec = res2["decision"]
            s2_reply = res2["reply"]
            s2_ev = res2.get("evidence", [])
            s2_dec_ok = (s2_dec in acc_decisions)
            s2_inc_ok = check_must_include(s2_reply, must_inc)
            s2_not_ok = check_must_not_include(s2_reply, must_not)
            s2_pass = s2_dec_ok and s2_inc_ok and s2_not_ok

            if s2_dec_ok: results["step2"]["decision_correct"] += 1
            if s2_inc_ok: results["step2"]["must_include_passed"] += 1
            if s2_not_ok: results["step2"]["must_not_include_passed"] += 1
            if s2_pass: results["step2"]["overall_correct"] += 1

            if gold_items:
                s2_gold_total += 1
                if all(g in s2_ev for g in gold_items):
                    s2_gold_hits += 1

            results["details"].append({
                "id": qid,
                "question": question_text,
                "step1_pass": s1_pass,
                "step2_pass": s2_pass,
                "gold_evidence": gold_items,
                "step2_evidence": s2_ev,
            })

        results["step2"]["gold_evidence_recall"] = (s2_gold_hits / s2_gold_total * 100.0) if s2_gold_total else 100.0
        return results

    def evaluate_conversations(self) -> Dict[str, Any]:
        """Evaluates Step 3 Multi-Turn Agent across all 23 conversations and 96 turns."""
        c_path = PRACTICE_DIR / "conversations.csv"
        with open(c_path, "r", encoding="utf-8") as f:
            turns = list(csv.DictReader(f))

        conv_groups = defaultdict(list)
        for t in turns:
            conv_groups[t["conversation_id"]].append(t)

        metrics = {
            "total_turns": len(turns),
            "total_conversations": len(conv_groups),
            "decision_correct": 0,
            "must_include_passed": 0,
            "must_not_include_passed": 0,
            "tool_calls_correct": 0,
            "overall_turns_passed": 0,
        }

        for cid, conv_turns in conv_groups.items():
            self.step3_agent.reset_state(cid)
            for t in sorted(conv_turns, key=lambda x: int(x["turn"])):
                turn_num = int(t["turn"])
                msg = t["customer_message"]
                exp_dec = t["expected_decision"]
                must_inc = t.get("must_include", "")
                must_not = t.get("must_not_include", "")
                exp_tools_str = t.get("expected_tool_calls", "").strip()

                agent_res = self.step3_agent.respond(msg, conversation_id=cid, forced_turn=turn_num)
                reply = agent_res["reply"]
                dec = agent_res["decision"]
                actual_tools = agent_res["tool_calls"]

                dec_ok = (dec == exp_dec)
                inc_ok = check_must_include(reply, must_inc)
                not_ok = check_must_not_include(reply, must_not)

                # Tool calls check
                tools_ok = True
                if exp_tools_str:
                    # Check if expected tool call is present in actual tool calls
                    tools_ok = any(exp_tools_str in act for act in actual_tools)
                else:
                    tools_ok = (len(actual_tools) == 0)

                turn_pass = dec_ok and inc_ok and not_ok and tools_ok
                if dec_ok: metrics["decision_correct"] += 1
                if inc_ok: metrics["must_include_passed"] += 1
                if not_ok: metrics["must_not_include_passed"] += 1
                if tools_ok: metrics["tool_calls_correct"] += 1
                if turn_pass: metrics["overall_turns_passed"] += 1

        return metrics
