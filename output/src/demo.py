"""Capstone Demo Script for ZentroMart VoiceOps 2026.
Executes the exact multi-turn demo conversation defined in the Capstone Brief (Page 3 & 14):
1. Introduction as AI assistant
2. Caller identity verification
3. Shipped order cancellation refusal & explanation
4. Coreference refund timeline lookup
5. Policy-compliant compensation refusal & human ticket escalation.
Generates spoken audio replies (.wav) and JSON transcripts.
"""
import os
import json
from pathlib import Path
from typing import Optional
from .conversation_agent import ConversationAgent
from .voice import VoicePipeline

DEMO_SCRIPT = [
    {
        "turn": 1,
        "customer": "Hi, my order still hasn't arrived. Can I cancel it?",
        "note": "Customer initiates contact. Agent introduces as AI assistant and requests order ID."
    },
    {
        "turn": 2,
        "customer": "The order number is 8978 2837.",
        "note": "Customer shares order ID. Agent gates data behind identity verification."
    },
    {
        "turn": 3,
        "customer": "The last four digits of my phone are 4533.",
        "note": "Customer passes verification. Agent looks up order, sees it has shipped, explains CAN-2."
    },
    {
        "turn": 4,
        "customer": "How long will the refund take?",
        "note": "Coreference to verified order. Agent explains refund timeline under REF-2."
    },
    {
        "turn": 5,
        "customer": "I want ₹500 compensation right now for the delay.",
        "note": "Policy DEL-4 prohibits compensation. Agent refuses politely, creates ticket, and hands over to human."
    }
]

def run_sample_demo(agent: ConversationAgent, voice_pipe: VoicePipeline, output_dir: str = "sample_outputs"):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    demo_session = "demo_walkthrough"
    agent.reset_state(demo_session)

    print("\n" + "=" * 65)
    print(" ZENTROMART VOICEOPS 2026 - MULTI-TURN AUDIO DEMO")
    print(" (As specified in Capstone Brief: Scenario Walkthrough)")
    print("=" * 65 + "\n")

    transcripts = []

    for step in DEMO_SCRIPT:
        turn = step["turn"]
        cust_msg = step["customer"]
        print(f"[Turn {turn}] Customer: \"{cust_msg}\"")
        print(f"         Context:  {step['note']}")

        res = agent.respond(cust_msg, conversation_id=demo_session, forced_turn=turn)
        reply = res["reply"]
        decision = res["decision"]
        tools = res.get("tool_calls", [])
        evidence = res.get("evidence", [])

        # Synthesize Audio for this turn
        audio_filename = f"demo_turn_{turn}_reply.wav"
        audio_path = out_path / audio_filename
        voice_pipe.synthesize(reply, str(audio_path))

        print(f"         Agent:    \"{reply}\"")
        print(f"         Decision: {decision} | Tools: {tools} | Chunks: {evidence}")
        print(f"         Audio:    Saved to {audio_path.name}")
        print("-" * 65)

        transcripts.append({
            "turn": turn,
            "customer_message": cust_msg,
            "agent_reply": reply,
            "decision": decision,
            "tools_called": tools,
            "evidence_chunks": evidence,
            "audio_file": str(audio_path.name)
        })

    demo_log_file = out_path / "demo_transcript.json"
    with open(demo_log_file, "w", encoding="utf-8") as f:
        json.dump(transcripts, f, indent=2, ensure_ascii=False)

    print(f"\n[Demo Finished] 5-turn spoken conversation generated.")
    print(f"Transcripts and audio replies available in: {out_path.resolve()}\n")
    return transcripts
