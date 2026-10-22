# ZentroMart VoiceOps 2026: 2-Minute Demo Script

This script documents the exact demo scenario requested by the Capstone Brief (Page 3 & Page 14):
*"Max 2 minutes: a question answered from the documents with a follow-up, plus one handover or 'I don't know'"*

You can run this demo live with spoken audio generation using:
```bash
python run.py --demo
```
or interactively in the web UI using:
```bash
streamlit run app.py
```

---

## Demo Walkthrough (Turn-by-Turn)

### Turn 1: Opening & Intent Gathering
- **Customer Audio:** *"Hi, my order still hasn't arrived. Can I cancel it?"*
- **Agent Action:** Greets customer, introduces identity as ZentroMart's AI support assistant, and requests the 8-digit order number (`STY-1`).
- **Agent Audio Reply:** *"Hello! I am ZentroMart's AI support assistant. Please provide your order ID so I can assist you with your request."*
- **Decision:** `clarify` | **Evidence:** `[STY-1]`

---

### Turn 2: Identity Verification Request
- **Customer Audio:** *"The order number is 8978 2837."*
- **Agent Action:** Dispatches unverified lookup `lookup_order(order_id=89782837)`. Order details are withheld. Agent requests caller verification credentials (`IDV-2`).
- **Agent Audio Reply:** *"Before I can share details, please provide the last 4 digits of your registered phone number or your delivery pincode."*
- **Decision:** `clarify` | **Tool Call:** `lookup_order(order_id=89782837)` | **Evidence:** `[IDV-2]`

---

### Turn 3: Caller Verified & Shipped Order Cancellation Refusal
- **Customer Audio:** *"The last four digits of my phone are 4533."*
- **Agent Action:** Dispatches verification `lookup_order(order_id=89782837, verification_value=4533)`. Verification succeeds. Agent notes order is shipped/delivered, explaining shipped cancellation policy (`CAN-2`).
- **Agent Audio Reply:** *"Thank you for verifying. Your order is currently delivered and was promised for delivery on 15 October 2026. Under policy CAN-2, an order that has already shipped cannot be cancelled. You can refuse delivery at your door or return it within its return window."*
- **Decision:** `answer` | **Tool Call:** `lookup_order(order_id=89782837, verification_value=4533)` | **Evidence:** `[IDV-2]`, `[CAN-2]`

---

### Turn 4: Follow-up Coreference (Refund Timeline)
- **Customer Audio:** *"How long will the refund take?"*
- **Agent Action:** Understands coreference (same verified order item paid via UPI). Quotes business-day timeline from `REF-2` without asking customer to repeat.
- **Agent Audio Reply:** *"Refunds to UPI take 1 to 3 business days after initiation."*
- **Decision:** `answer` | **Evidence:** `[REF-2]`, `[RET-7]`

---

### Turn 5: Compensation Demand & Human Escalation
- **Customer Audio:** *"I want ₹500 compensation right now for the delay."*
- **Agent Action:** Policy `DEL-4` prohibits cash compensation. Agent politely refuses, explains the policy rule, dispatches `create_ticket()` to escalate to human colleague (`ESC-1`, `ESC-4`).
- **Agent Audio Reply:** *"I apologize for the delay. However, under ZentroMart policy DEL-4, we do not provide cash compensation for delivery delays. I have created a support ticket and escalated this to a human colleague who will contact you."*
- **Decision:** `refuse` / `escalate` | **Tool Call:** `create_ticket()` | **Evidence:** `[DEL-4]`, `[ESC-1]`, `[ESC-4]`

---

## Generated Audio Files
The generated audio files for this demonstration are saved in `sample_outputs/`:
- `demo_turn_1_reply.wav`
- `demo_turn_2_reply.wav`
- `demo_turn_3_reply.wav`
- `demo_turn_4_reply.wav`
- `demo_turn_5_reply.wav`
- Complete JSON log: `sample_outputs/demo_transcript.json`
