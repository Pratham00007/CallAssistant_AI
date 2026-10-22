#!/usr/bin/env python3
"""ZentroMart VoiceOps 2026 - Main Execution and Batch Evaluation Script.
Organizer-compatible CLI taking customer audio files, transcribing via Gnani STT,
reasoning over grounded policies, synthesizing via Gnani TTS (timbre-v2.5),
and logging responses with retrieved document chunk IDs.

Usage:
  python run.py <audio_folder> [output_folder]
  python run.py --input_dir <audio_folder> --output_dir <output_folder>
  python run.py --eval
  python run.py --interactive
  python run.py --demo
"""
import os
import sys
import argparse
import json
import time
from pathlib import Path

# Configure utf-8 stdout on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import KB_DIR, DATA_DIR, PRACTICE_DIR, DEFAULT_VOICE, DEFAULT_TTS_MODEL
from src.kb_loader import KnowledgeBase
from src.data_loader import DataLoader
from src.retriever import HybridRetriever
from src.policy_engine import PolicyEngine
from src.tools_adapter import ToolsAdapter
from src.conversation_agent import ConversationAgent
from src.voice import VoicePipeline
from src.evaluator import Evaluator


def process_audio_batch(input_dir: str, output_dir: str, voice_pipe: VoicePipeline, agent: ConversationAgent):
    """Processes a folder of customer audio files as specified by Capstone Brief."""
    in_path = Path(input_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    audio_extensions = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
    audio_files = sorted([f for f in in_path.iterdir() if f.is_file() and f.suffix.lower() in audio_extensions])

    if not audio_files:
        # Check if there are .txt practice inputs
        txt_files = sorted([f for f in in_path.iterdir() if f.is_file() and f.suffix.lower() == ".txt"])
        if txt_files:
            print(f"[Batch] Found {len(txt_files)} text query files in {input_dir}.")
            return process_text_batch(txt_files, out_path, voice_pipe, agent)
        else:
            print(f"[Batch] No audio files found in '{input_dir}'.")
            return []

    print(f"\n=======================================================")
    print(f" ZentroMart VoiceOps: Processing {len(audio_files)} Customer Audio Files")
    print(f" Input Directory:  {in_path.resolve()}")
    print(f" Output Directory: {out_path.resolve()}")
    print(f" TTS Model: {DEFAULT_TTS_MODEL} | Voice: {DEFAULT_VOICE}")
    print(f"=======================================================\n")

    summary_records = []
    agent.reset_state("batch_session")

    for idx, audio_file in enumerate(audio_files, 1):
        stem = audio_file.stem
        print(f"[{idx}/{len(audio_files)}] Processing '{audio_file.name}'...")

        # 1. Transcribe with Gnani STT
        heard = voice_pipe.transcribe(str(audio_file))
        if not heard or not heard.strip():
            # Check for sidecar transcript text
            sidecar = audio_file.with_suffix(".txt")
            if sidecar.exists():
                heard = sidecar.read_text(encoding="utf-8").strip()

        print(f"   Customer (STT): \"{heard}\"")

        # 2. Agent Brain (Step 3 Multi-Turn / RAG)
        if not heard or not heard.strip():
            reply = "Sorry, I didn't catch that. Could you say it again?"
            decision = "clarify"
            tool_calls = []
            evidence = []
        else:
            agent_res = agent.respond(heard, conversation_id="batch_session")
            reply = agent_res.get("reply", "")
            decision = agent_res.get("decision", "answer")
            tool_calls = agent_res.get("tool_calls", [])
            evidence = agent_res.get("evidence", [])

        print(f"   Agent Reply:    \"{reply}\"")
        print(f"   Decision:       {decision}")
        if tool_calls:
            print(f"   Tool Calls:     {tool_calls}")
        if evidence:
            print(f"   Evidence Chunks: {evidence}")

        # 3. Synthesize Voice with Gnani TTS
        reply_wav = out_path / f"{stem}_reply.wav"
        voice_pipe.synthesize(reply, str(reply_wav))
        print(f"   Generated Audio: {reply_wav.name}")

        # 4. Save Text and Metadata
        reply_txt = out_path / f"{stem}_reply.txt"
        reply_txt.write_text(
            f"INPUT_FILE: {audio_file.name}\n"
            f"TRANSCRIPT: {heard}\n"
            f"REPLY: {reply}\n"
            f"DECISION: {decision}\n"
            f"TOOL_CALLS: {', '.join(tool_calls)}\n"
            f"RETRIEVED_CHUNKS: {', '.join(evidence)}\n",
            encoding="utf-8"
        )

        record = {
            "index": idx,
            "input_file": audio_file.name,
            "transcript": heard,
            "reply": reply,
            "decision": decision,
            "tool_calls": tool_calls,
            "retrieved_chunks": evidence,
            "audio_output": reply_wav.name,
        }
        summary_records.append(record)
        print("-" * 55)

    summary_file = out_path / "batch_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_records, f, indent=2, ensure_ascii=False)

    print(f"\n[Batch Complete] Processed {len(audio_files)} audio queries.")
    print(f"Results and audio saved to: {out_path.resolve()}\n")
    return summary_records


def process_text_batch(txt_files, out_path: Path, voice_pipe: VoicePipeline, agent: ConversationAgent):
    summary_records = []
    agent.reset_state("batch_text_session")

    for idx, txt_file in enumerate(txt_files, 1):
        stem = txt_file.stem
        query = txt_file.read_text(encoding="utf-8").strip()
        print(f"[{idx}/{len(txt_files)}] Query: \"{query}\"")

        agent_res = agent.respond(query, conversation_id="batch_text_session")
        reply = agent_res.get("reply", "")
        decision = agent_res.get("decision", "answer")
        tool_calls = agent_res.get("tool_calls", [])
        evidence = agent_res.get("evidence", [])

        reply_wav = out_path / f"{stem}_reply.wav"
        voice_pipe.synthesize(reply, str(reply_wav))

        reply_txt = out_path / f"{stem}_reply.txt"
        reply_txt.write_text(
            f"QUERY: {query}\n"
            f"REPLY: {reply}\n"
            f"DECISION: {decision}\n"
            f"TOOL_CALLS: {', '.join(tool_calls)}\n"
            f"RETRIEVED_CHUNKS: {', '.join(evidence)}\n",
            encoding="utf-8"
        )

        record = {
            "index": idx,
            "query": query,
            "reply": reply,
            "decision": decision,
            "tool_calls": tool_calls,
            "retrieved_chunks": evidence,
            "audio_output": reply_wav.name,
        }
        summary_records.append(record)

    summary_file = out_path / "batch_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_records, f, indent=2, ensure_ascii=False)

    print(f"\n[Batch Complete] Results saved to: {out_path.resolve()}\n")
    return summary_records


def run_interactive(agent: ConversationAgent, voice_pipe: VoicePipeline):
    """Interactive command-line support assistant session with live voice TTS."""
    print("\n" + "=" * 60)
    print(" ZentroMart VoiceOps 2026: Interactive Support Agent")
    print(" (Type 'exit' to quit, 'reset' to start new session)")
    print("=" * 60 + "\n")

    session_id = f"cli_{int(time.time())}"
    agent.reset_state(session_id)

    # Turn 1
    init_res = agent.respond("Hello", conversation_id=session_id, forced_turn=1)
    print(f"Agent: {init_res['reply']}\n")
    voice_pipe.synthesize(init_res['reply'], "output/live_reply.wav")

    while True:
        try:
            user_msg = input("Customer: ").strip()
            if not user_msg:
                continue
            if user_msg.lower() in ("exit", "quit"):
                print("Ending session. Have a great day!")
                break
            if user_msg.lower() == "reset":
                session_id = f"cli_{int(time.time())}"
                agent.reset_state(session_id)
                init_res = agent.respond("Hello", conversation_id=session_id, forced_turn=1)
                print(f"\n[New Session Started]")
                print(f"Agent: {init_res['reply']}\n")
                continue

            res = agent.respond(user_msg, conversation_id=session_id)
            print(f"Agent: {res['reply']}")
            if res.get('tool_calls'):
                print(f"  [Tool Calls]: {res['tool_calls']}")
            if res.get('evidence'):
                print(f"  [Evidence]:   {res['evidence']}")
            print()
            voice_pipe.synthesize(res['reply'], "output/live_reply.wav")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break


def main():
    parser = argparse.ArgumentParser(description="ZentroMart VoiceOps 2026 Support Agent Runner")
    parser.add_argument("pos_input", nargs="?", default=None, help="Input directory of customer audio files")
    parser.add_argument("pos_output", nargs="?", default=None, help="Output directory to save replies and audio")
    parser.add_argument("--input_dir", "-i", type=str, default=None, help="Input folder of customer audio files")
    parser.add_argument("--output_dir", "-o", type=str, default="sample_outputs", help="Output directory")
    parser.add_argument("--eval", action="store_true", help="Run full quantitative evaluation suite")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive CLI session")
    parser.add_argument("--demo", action="store_true", help="Run demonstration scenario and generate sample audio")
    parser.add_argument("--web", action="store_true", help="Launch Streamlit web UI")

    args = parser.parse_args()

    # Route options
    if args.web:
        os.system("streamlit run app.py")
        return

    if args.eval:
        ev = Evaluator()
        print("\n" + "=" * 65)
        print(" RUNNING COMPLETE QUANTITATIVE EVALUATION SUITE")
        print("=" * 65)
        q_res = ev.evaluate_questions()
        c_res = ev.evaluate_conversations()

        print(f"\n[1] Step 1 (Prompt-Only Baseline) vs Step 2 (Grounded RAG)")
        print(f"    Total Questions: {q_res['total_questions']}")
        print(f"    Step 1 Overall Accuracy: {q_res['step1']['overall_correct']}/{q_res['total_questions']} ({q_res['step1']['overall_correct']/q_res['total_questions']*100:.1f}%)")
        print(f"    Step 2 Overall Accuracy: {q_res['step2']['overall_correct']}/{q_res['total_questions']} ({q_res['step2']['overall_correct']/q_res['total_questions']*100:.1f}%)")
        print(f"    Step 2 Retrieval Recall: {q_res['step2']['gold_evidence_recall']:.1f}%")

        print(f"\n[2] Step 3 (Multi-Turn Conversations & Caller Verification)")
        print(f"    Total Conversations: {c_res['total_conversations']} | Total Turns: {c_res['total_turns']}")
        print(f"    Decisions Correct:   {c_res['decision_correct']}/{c_res['total_turns']} ({c_res['decision_correct']/c_res['total_turns']*100:.1f}%)")
        print(f"    Tool Calls Exact:    {c_res['tool_calls_correct']}/{c_res['total_turns']} ({c_res['tool_calls_correct']/c_res['total_turns']*100:.1f}%)")
        print(f"    Must-Include Passed: {c_res['must_include_passed']}/{c_res['total_turns']} ({c_res['must_include_passed']/c_res['total_turns']*100:.1f}%)")
        print(f"    Overall Turn Score:  {c_res['overall_turns_passed']}/{c_res['total_turns']} ({c_res['overall_turns_passed']/c_res['total_turns']*100:.1f}%)")
        print("\nEvaluation successfully finished.\n")
        return

    # Initialize components
    kb = KnowledgeBase(KB_DIR)
    data_loader = DataLoader(DATA_DIR)
    retriever = HybridRetriever(kb, data_loader)
    policy_engine = PolicyEngine(data_loader)
    tools_adapter = ToolsAdapter()
    agent = ConversationAgent(kb, data_loader, retriever, policy_engine, tools_adapter)
    voice_pipe = VoicePipeline()

    if args.demo:
        from src.demo import run_sample_demo
        run_sample_demo(agent, voice_pipe, args.output_dir)
        return

    if args.interactive:
        run_interactive(agent, voice_pipe)
        return

    # Batch audio folder run (Organizer command)
    in_dir = args.input_dir or args.pos_input
    out_dir = args.output_dir or args.pos_output or "sample_outputs"

    if in_dir:
        process_audio_batch(in_dir, out_dir, voice_pipe, agent)
    else:
        # Default behavior: run demo and show instructions
        print("\nZentroMart VoiceOps 2026 Ready.")
        print("To process customer audio folder, run:")
        print("   python run.py <audio_folder> <output_folder>")
        print("To evaluate benchmarks:")
        print("   python run.py --eval")
        print("To run demo conversation:")
        print("   python run.py --demo")
        print("To chat interactively:")
        print("   python run.py --interactive")


if __name__ == "__main__":
    main()
