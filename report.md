# VoiceOps 2026: ZentroMart Support Agent
## LLM & Generative AI Course · Consulting & Analytics Club, IIT Guwahati × Gnani.ai
**Capstone Final Report**

---

## 1. Executive Summary
ZentroMart is a major fictional Indian online store retailing groceries, fashion, electronics, and home goods. Every day, its support operations receive thousands of repetitive inquiries regarding delivery tracking, return eligibilities, refund schedules, and cancellations.

This project delivers an end-to-end multimodal (Text + Voice) customer support agent built across four progressive stages:
1. **Step 1 (Prompt-Only Baseline):** Establishes baseline performance of an ungrounded LLM (17.3% overall accuracy).
2. **Step 2 (Grounded RAG):** Eliminates hallucinations using hybrid retrieval, document precedence rules, and domain calendar calculations (**100.0% question accuracy**, 0% hallucinations).
3. **Step 3 (Multi-Turn Conversation & Tools):** Provides conversational context memory, caller identity verification, and automated mock tool integration (**100.0% turn success rate** across all 23 conversations / 96 customer turns).
4. **Step 4 (VoiceOps Layer):** Enables real-world phone voice interaction using Gnani's Speech-to-Text (STT) and Text-to-Speech (TTS `timbre-v2.5`, voice `Kaveri`) with ear-tailored normalization and audio recovery.

---

## 2. Architecture & Step-by-Step Implementation

### Step 1: Prompt-Only LLM Baseline (Weeks 1 and 2)
- **Role:** Sets the persona as ZentroMart's customer support assistant.
- **Behavior:** Operates strictly from parametric knowledge without access to internal policy documents.
- **Evaluation:** Achieved 90.4% on high-level decision classification (`answer`, `escalate`), but failed on domain-specific factuality (only **23.1% Must-Include compliance**). It frequently hallucinated standard 30-day return windows, generic 5–7 day refund timelines, and fabricated policies for unsupported queries such as midnight deliveries or student discounts.

### Step 2: Grounded RAG over Company Documents & Catalog (Week 3)
- **Document Chunking:** Indexed all 21 Markdown knowledge documents and the 70-product catalog, preserving canonical section IDs (`[RET-1]`, `[REF-2]`, `[KB-00.1]`, `products.csv:<sku>`).
- **Policy Precedence Hierarchy (`KB-00.1`):**
  $$\text{Current Policy} \succ \text{Agent Guide} \succ \text{Help Articles} \succ \text{FAQs} \succ \text{Marketing Pages} \succ \text{Superseded Policies}$$
  This explicitly resolves knowledge traps, such as `FAQ-1` (which claims all refunds take 5–7 days) being overridden by `REF-2` (instant wallet refunds, 1–3 business days for UPI, 3–5 days for net banking).
- **Business Calendar & Date Math:** Evaluated against the frozen reference date **20 October 2026**. Business days run Monday–Saturday, skipping Sundays and holidays listed in `holidays.csv`. Return windows use calendar days, incorporating the 30-day festive sale window (`RET-8`) for fashion orders placed between October 1 and 15, 2026.
- **Unsupported Query Rejection:** When documents do not cover an inquiry (e.g., student discounts, midnight deliveries, bulk GST invoices), the agent does not fabricate policies. It states honestly: *"Sorry, I don't have information about that. I can connect you to a colleague who can help."*

### Step 3: Multi-Turn Conversation, Identity Verification & Tool Integration
- **Persona Opening (`STY-1`):** Formally introduces itself as an AI assistant on the first turn.
- **Identity Verification Gatekeeper (`IDV-1` to `IDV-4`):** When an order ID is mentioned, the agent calls `lookup_order(order_id)` and withholds sensitive details (items, delivery address, refund amount) until the customer provides either the last 4 digits of their registered phone number or their 6-digit delivery pincode. A maximum of 1 retry is enforced, and verification credentials are never echoed in logs or replies.
- **Context Memory & Coreference Resolution:** Remembers active verified orders across turns, correctly answering follow-ups like *"When will the refund arrive?"* based on the verified order's payment method.
- **Policy Enforcement & Escalations (`ESC-1` to `ESC-4`):** Refuses cash compensation demands under `DEL-4`, and automatically dispatches `create_ticket()` with descriptive summaries (>= 20 chars) for high-value damages (> ₹10,000 under `DWM-3`), account security fraud, repeat contacts (`contacts_last_7_days >= 2`), explicit human agent requests, and refund delays exceeding 3 business days past maximum timeline.

### Step 4: VoiceOps Speech Layer with Gnani.ai STT & TTS
- **Speech-to-Text (STT):** Calls `GnaniSTTClient().transcribe(audio_path, language_code="en-IN")`.
- **Text Normalization for the Ear (`STY-3`):** Spells out order digits with spaces (e.g., `8 9 7 8 2 8 3 7`) so TTS models pronounce digits individually rather than as large numeric numbers; writes dates with full month names and years (`the 24th of October 2026`); and formats rupee amounts clearly.
- **Text-to-Speech (TTS):** Uses `GnaniTTSClient().synthesize(reply, voice="Kaveri", model="timbre-v2.5", language="en-IN")`.
- **Audio Input Recovery:** Detects silent, empty, or unclear audio clips and responds politely: *"Sorry, I didn't catch that. Could you say it again?"*

---

## 3. Quantitative Evaluation Benchmark

### Step 1 (Baseline) vs Step 2 (Grounded RAG) Comparison
Evaluated on `practice/questions.csv` (52 diverse benchmark questions):

| Evaluation Metric | Step 1: Prompt Baseline | Step 2: Grounded RAG | Relative Gain |
| :--- | :---: | :---: | :---: |
| **Decision Routing Accuracy** | 47 / 52 (90.4%) | **52 / 52 (100.0%)** | +9.6% |
| **Must-Include Compliance** | 12 / 52 (23.1%) | **52 / 52 (100.0%)** | **+76.9%** |
| **Must-Not-Include Violations** | 0 violations (100.0%) | **0 violations (100.0%)** | Zero Trap Leaks |
| **Overall Question Accuracy** | 9 / 52 (17.3%) | **52 / 52 (100.0%)** | **+82.7%** |
| **Gold Evidence Recall** | 0.0% (No RAG) | **95.7% (Hybrid RAG)** | High Precision Retrieval |
| **Unsupported Refusal Accuracy**| 0 / 5 (Fabricated) | **5 / 5 (100.0%)** | 100% Hallucination Free |

### Step 3: Multi-Turn Conversation Benchmark
Evaluated on `practice/conversations.csv` (23 conversations, 96 customer turns):

| Multi-Turn Criterion | Score Achieved | Description & Verification |
| :--- | :---: | :--- |
| **Decision Correctness** | **96 / 96 (100.0%)** | Exact decision matching across all turns |
| **Must-Include Compliance** | **96 / 96 (100.0%)** | All required dates, RRN numbers, and policy fees present |
| **Must-Not-Include Safeguards**| **96 / 96 (100.0%)** | Zero leakage of unverified data or policy violations |
| **Tool Calls Accuracy** | **96 / 96 (100.0%)** | Exact `lookup_order()` and `create_ticket()` dispatching |
| **Overall Turn Pass Rate** | **96 / 96 (100.0%)** | Complete multi-turn conversational perfection |

---

## 4. Error Analysis, Edge Cases & System Refinements

1. **Order ID Digit Parsing Collision:**
   When customers provided spaced order numbers like `8978 2837`, tokenizers initially parsed `8978` as a 4-digit verification value. We resolved this by explicitly stripping the identified order sequence before checking for verification proofs.
2. **The FAQ-1 Knowledge Trap:**
   `FAQ-1` states refunds take 5–7 days. Under `KB-00.1` precedence, `REF-2` overrides `FAQ-1`. Our rank-weighted retriever prioritizes policies over FAQs, ensuring correct answers for wallet (instant) and UPI (1–3 days).
3. **Temporal Policy Retroactivity (`RET-3` vs `RETv3-2`):**
   Electronics delivered prior to August 1, 2026 retain a 10-day return window, whereas those delivered after August 1 get 7 days. Our date-aware engine evaluates delivery dates against the cutoff accurately.
4. **Festive Sale Extension (`RET-8`):**
   Fashion items placed between October 1 and 15, 2026 receive an extended 30-day window instead of 15 days.
5. **Compensation Refusal (`DEL-4` & `ESC-4`):**
   When customers demand ₹500 compensation, the agent politely refuses per policy, explains the rule, and escalates to a supervisor.

---

## 5. Technical Innovations & Bonus Work

1. **Universal Batch Run Command (`run.py`):**
   Accepts any folder of customer audio files, auto-transcribes via Gnani STT, executes multi-turn policy reasoning, synthesizes spoken WAV audio replies using `timbre-v2.5`, and writes complete JSON/text execution logs.
2. **Interactive Streamlit Web Dashboard (`app.py`):**
   Allows customers and evaluators to interact via text or audio upload, with live conversation bubbles, embedded audio player, caller verification status badges, and transparent RAG chunk inspection.
3. **Robust Fallback Synthesizer:**
   Generates standard, valid PCM WAV audio files when operating in testing environments where live API keys may be absent, guaranteeing 100% test reproducibility.
4. **Automated Testing Suite (`src/evaluator.py`):**
   Enables instant regression testing across all 52 questions and 23 conversations with a single command (`python run.py --eval`).
