"""Interactive Web Interface for ZentroMart VoiceOps 2026 Support Agent.
Built with Streamlit for live text/voice customer support, audio playback,
caller verification status, and transparent RAG chunk inspection.
"""
import os
import sys
import tempfile
from pathlib import Path
import streamlit as st

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import KB_DIR, DATA_DIR, DEFAULT_VOICE, DEFAULT_TTS_MODEL
from src.kb_loader import KnowledgeBase
from src.data_loader import DataLoader
from src.retriever import HybridRetriever
from src.policy_engine import PolicyEngine
from src.tools_adapter import ToolsAdapter
from src.conversation_agent import ConversationAgent
from src.voice import VoicePipeline

st.set_page_config(
    page_title="ZentroMart VoiceOps 2026",
    page_icon="🎙️",
    layout="wide"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.1rem; color: #4B5563; margin-bottom: 1.5rem; }
    .badge-verified { background-color: #D1FAE5; color: #065F46; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; }
    .badge-pending { background-color: #FEF3C7; color: #92400E; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; }
    .chat-box { background-color: #F9FAFB; border-radius: 12px; padding: 15px; margin-bottom: 12px; border: 1px solid #E5E7EB; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_agent():
    kb = KnowledgeBase(KB_DIR)
    data_loader = DataLoader(DATA_DIR)
    retriever = HybridRetriever(kb, data_loader)
    policy_engine = PolicyEngine(data_loader)
    tools_adapter = ToolsAdapter()
    agent = ConversationAgent(kb, data_loader, retriever, policy_engine, tools_adapter)
    voice_pipe = VoicePipeline()
    return agent, voice_pipe

agent, voice_pipe = load_agent()

# Sidebar: Controls & Metadata
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&h=200&q=80", width=90)
    st.title("ZentroMart Support")
    st.markdown("**LLM & Generative AI Capstone**")
    st.markdown("*Consulting & Analytics Club, IIT Guwahati × Gnani.ai*")
    st.divider()

    st.subheader("⚙️ System Status")
    st.markdown(f"**TTS Model:** `{DEFAULT_TTS_MODEL}`")
    st.markdown(f"**Voice:** `{DEFAULT_VOICE}`")
    st.markdown(f"**Dataset Reference Date:** `20 Oct 2026`")

    st.divider()
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent_state = None
        st.rerun()

    st.markdown("### 💡 Quick Sample Queries")
    quick_queries = [
        "Hello, mujhe order ke baare mein help chahiye.",
        "Order number hai 8978 2837.",
        "Last four digits 4533 hain.",
        "Aur refund kitne din mein aayega?",
        "I want ₹500 compensation right now.",
        "Can I schedule a delivery at midnight?",
        "Is there a student discount?"
    ]
    for q in quick_queries:
        if st.button(q, key=f"btn_{q}"):
            st.session_state.preset_query = q

# Main App Body
st.markdown('<div class="main-header">🎙️ VoiceOps 2026: ZentroMart AI Support</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Turn Conversational Agent with Identity Verification, Grounded RAG, and Gnani Speech Synthesis</div>', unsafe_allow_html=True)

# Initialize session messages
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Turn 1 Greeting
    init_res = agent.respond("Hello", conversation_id="web_session", forced_turn=1)
    st.session_state.messages.append({
        "role": "assistant",
        "content": init_res["reply"],
        "decision": init_res["decision"],
        "tools": init_res["tool_calls"],
        "evidence": init_res["evidence"],
        "audio": None
    })

# Layout: Chat Column (left) and Status/RAG Column (right)
col1, col2 = st.columns([7, 5])

with col1:
    st.markdown("### 💬 Conversation")
    
    # Render chat history
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("audio") and os.path.exists(msg["audio"]):
                st.audio(msg["audio"], format="audio/wav")

    # Input area: Audio or Text
    input_tab1, input_tab2 = st.tabs(["✍️ Text Message", "🎤 Audio Upload"])

    user_input = None
    with input_tab1:
        text_val = st.session_state.pop("preset_query", None)
        typed_input = st.chat_input("Type your message here...", key="chat_input")
        if typed_input:
            user_input = typed_input
        elif text_val:
            user_input = text_val

    with input_tab2:
        uploaded_audio = st.file_uploader("Upload customer voice clip (.wav / .mp3)", type=["wav", "mp3"])
        if uploaded_audio and st.button("Transcribe & Send Audio"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(uploaded_audio.read())
                tmp_path = tmp.name
            stt_transcript = voice_pipe.transcribe(tmp_path)
            user_input = stt_transcript

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Agent Turn
        agent_res = agent.respond(user_input, conversation_id="web_session")
        reply = agent_res.get("reply", "")
        dec = agent_res.get("decision", "answer")
        tools = agent_res.get("tool_calls", [])
        evidence = agent_res.get("evidence", [])

        # Generate audio reply
        out_wav_path = f"sample_outputs/web_turn_{len(st.session_state.messages)}_reply.wav"
        voice_pipe.synthesize(reply, out_wav_path)

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply,
            "decision": dec,
            "tools": tools,
            "evidence": evidence,
            "audio": out_wav_path
        })
        st.rerun()

with col2:
    st.markdown("### 🛡️ Agent Intelligence & Tool Inspector")
    
    state = agent.get_or_create_state("web_session")
    
    # Identity Verification Card
    with st.container():
        st.markdown("#### Caller Verification Status")
        if state.verified:
            st.markdown('<span class="badge-verified">✓ Verified Caller</span>', unsafe_allow_html=True)
            order_info = state.order_details or {}
            st.markdown(f"**Customer:** `{order_info.get('customer_first_name', 'N/A')}`")
            st.markdown(f"**Order ID:** `{state.order_id}`")
            st.markdown(f"**Order Status:** `{order_info.get('status', 'N/A')}`")
            st.markdown(f"**Delivery Pincode:** `{order_info.get('delivery_pincode', 'N/A')}`")
            st.markdown(f"**Plus Member:** `{order_info.get('is_plus', False)}`")
        elif state.order_id:
            st.markdown('<span class="badge-pending">⏳ Identity Verification Pending</span>', unsafe_allow_html=True)
            st.markdown(f"**Identified Order ID:** `{state.order_id}`")
            st.info("Order details withheld until verification succeeds (4-digit phone suffix or delivery pincode).")
        else:
            st.markdown('<span class="badge-pending">⚪ No Order Specified</span>', unsafe_allow_html=True)

    st.divider()

    # RAG Chunks Inspector for last turn
    st.markdown("#### Retrieved Policy Chunks (Gold Evidence)")
    last_assistant_msg = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
    if last_assistant_msg and last_assistant_msg.get("evidence"):
        for chunk_id in last_assistant_msg["evidence"]:
            with st.expander(f"📄 Section: [{chunk_id}]"):
                chunk_obj = agent.kb.get_chunk(chunk_id)
                if chunk_obj:
                    st.markdown(f"**Title:** {chunk_obj.title}")
                    st.markdown(f"**Doc Type:** `{chunk_obj.doc_type}` | **Status:** `{chunk_obj.status}`")
                    st.markdown(f"**Content:**\n> {chunk_obj.body}")
                else:
                    st.markdown(f"Catalog Evidence: `{chunk_id}`")
    else:
        st.write("No document chunks required for current turn.")

    # Tool Execution Log
    st.markdown("#### Executed Tool Calls")
    if last_assistant_msg and last_assistant_msg.get("tools"):
        for t in last_assistant_msg["tools"]:
            st.code(t, language="python")
    else:
        st.write("No external tools triggered this turn.")
