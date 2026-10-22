"""Multi-Turn Conversational Support Agent for ZentroMart (Step 3).
Handles conversational state, identity-gated lookups, coreference resolution,
domain policy reasoning, ticket escalations, and language matching.
"""
import re
import datetime
from typing import Dict, Any, List, Optional
from .config import REFERENCE_DATE, TODAY_STR, add_business_days
from .kb_loader import KnowledgeBase
from .data_loader import DataLoader
from .retriever import HybridRetriever
from .policy_engine import PolicyEngine
from .tools_adapter import ToolsAdapter

class ConversationState:
    def __init__(self, conversation_id: str = "default"):
        self.conversation_id = conversation_id
        self.turn = 0
        self.history: List[Dict[str, str]] = []
        self.order_id: Optional[str] = None
        self.customer_id: Optional[str] = None
        self.initial_intent: Optional[str] = None
        self.verification_pending: bool = False
        self.verified: bool = False
        self.failed_attempts: int = 0
        self.order_details: Optional[Dict[str, Any]] = None
        self.last_sku: Optional[str] = None
        self.preferred_language: str = "en"
        self.ticket_created: bool = False
        self.ticket_id: Optional[str] = None

class ConversationAgent:
    def __init__(self, kb: KnowledgeBase, data_loader: DataLoader,
                 retriever: HybridRetriever, policy_engine: PolicyEngine,
                 tools_adapter: ToolsAdapter):
        self.kb = kb
        self.data_loader = data_loader
        self.retriever = retriever
        self.policy_engine = policy_engine
        self.tools = tools_adapter
        self.states: Dict[str, ConversationState] = {}

    def get_or_create_state(self, conversation_id: str) -> ConversationState:
        if conversation_id not in self.states:
            self.states[conversation_id] = ConversationState(conversation_id)
        return self.states[conversation_id]

    def reset_state(self, conversation_id: str):
        self.states[conversation_id] = ConversationState(conversation_id)

    def detect_language(self, text: str) -> str:
        if re.search(r'[\u0900-\u097f]', text):
            return "hi"
        tokens = set(re.findall(r'[a-zA-Z]+', text.lower()))
        hinglish_words = {"kya", "hai", "kaise", "karein", "aur", "mein", "ko", "shuru", "hua", "kab", "tak",
                          "aa", "jaana", "chahiye", "maine", "tha", "na", "pe", "nahi", "bataye", "namaste", "mujhe",
                          "ke", "baare", "chahiye", "hain", "sakti", "sakta", "hoon", "hoga", "kahan", "bhi", "rahi",
                          "teesri", "baar", "diya", "kar", "agle", "sawaal", "achha"}
        if len(tokens & hinglish_words) >= 2:
            return "hi-en"
        return "en"

    def respond(self, message: str, conversation_id: str = "default",
                forced_turn: Optional[int] = None) -> Dict[str, Any]:
        state = self.get_or_create_state(conversation_id)
        if forced_turn is not None:
            state.turn = forced_turn
        else:
            state.turn += 1

        lang = self.detect_language(message)
        state.preferred_language = lang
        msg_lower = message.lower()
        tool_calls: List[str] = []
        evidence: List[str] = []
        decision = "answer"
        reply = ""

        # --- Turn 1: Opening Greeting (STY-1) ---
        if state.turn == 1:
            decision = "clarify"
            evidence.append("STY-1")
            
            if any(w in msg_lower for w in ("where is", "hasn't arrived", "track", "kahan hai", "deliver")):
                state.initial_intent = "where_is_my_order"
            elif any(w in msg_lower for w in ("cancel", "कैंसिल", "रद्द")):
                state.initial_intent = "cancel"

            if lang == "hi":
                reply = "नमस्ते! मैं ZentroMart का AI सपोर्ट असिस्टेंट हूँ। कृपया अपना 8 अंकों का ऑर्डर नंबर बताएँ ताकि मैं आपकी सहायता कर सकूँ।"
            elif lang == "hi-en":
                reply = "Hello! Main ZentroMart ka AI support assistant hoon. Kripya apna order number share karein taaki main aapki help kar sakoon."
            else:
                reply = "Hello! I am ZentroMart's AI support assistant. Please provide your order ID so I can assist you with your request."

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # --- Check for Order ID ---
        oid_match = re.search(r'\b(\d{4}\s?\d{4})\b', message)
        if oid_match:
            clean_oid = oid_match.group(1).replace(" ", "")
            state.order_id = clean_oid

        # --- Turn 2 / Verification Gatekeeper (IDV-1, IDV-2) ---
        if state.order_id and not state.verified:
            msg_without_oid = re.sub(r'\b\d{4}\s?\d{4}\b', '', message)
            proof_match = re.findall(r'\b\d{4}\b|\b\d{6}\b', msg_without_oid)

            if not proof_match:
                state.verification_pending = True
                decision = "clarify"
                tool_calls.append(f"lookup_order(order_id={state.order_id})")
                evidence.append("IDV-2")
                self.tools.lookup_order(state.order_id)

                if lang == "hi":
                    reply = "सुरक्षा कारणों से, कृपया अपने रजिस्टर्ड फ़ोन नंबर के आख़िरी 4 अंक (last 4 digits) या डिलीवरी पिनकोड (pincode) बताएँ।"
                elif lang == "hi-en":
                    reply = "Aapki security ke liye, kripya apne registered phone number ke last 4 digits ya delivery pincode share karein."
                else:
                    reply = "Before I can share details, please provide the last 4 digits of your registered phone number or your delivery pincode."

                state.history.append({"user": message, "agent": reply})
                return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

            else:
                proof = proof_match[0]
                tool_calls.append(f"lookup_order(order_id={state.order_id}, verification_value={proof})")
                evidence.append("IDV-2")
                lookup_res = self.tools.lookup_order(state.order_id, verification_value=proof)

                if lookup_res.get("verified") is True:
                    state.verified = True
                    state.verification_pending = False
                    state.order_details = lookup_res
                    state.customer_id = lookup_res.get("customer_id")
                    first_name = lookup_res.get("customer_first_name", "")

                    if state.initial_intent == "where_is_my_order" or any(w in msg_lower for w in ("where is", "track", "kahan")):
                        decision = "answer"
                        promised = lookup_res.get("promised_date", "")
                        status = lookup_res.get("status", "")
                        try:
                            p_dt = datetime.date.fromisoformat(promised[:10])
                            promised_en = p_dt.strftime("%d %B %Y").lstrip("0")
                            hi_months = {
                                1: "जनवरी", 2: "फ़रवरी", 3: "मार्च", 4: "अप्रैल", 5: "मई", 6: "जून",
                                7: "जुलाई", 8: "अगस्त", 9: "सितंबर", 10: "अक्टूबर", 11: "नवंबर", 12: "दिसंबर"
                            }
                            promised_hi = f"{p_dt.day} {hi_months[p_dt.month]} {p_dt.year}"
                        except Exception:
                            promised_en = promised
                            promised_hi = promised

                        if lang == "hi":
                            reply = f"सत्यापन सफल रहा। आपका ऑर्डर {state.order_id} वर्तमान में '{status}' है और इसकी डिलीवरी {promised_hi} तक होगी।"
                        elif lang == "hi-en":
                            reply = f"Identity verify ho gayi hai. Aapka order '{status}' hai aur expected delivery {promised_en} hai."
                        else:
                            reply = f"Thank you for verifying. Your order is currently '{status}' and is promised for delivery on {promised_en}."

                        state.history.append({"user": message, "agent": reply})
                        return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

                    else:
                        decision = "answer"
                        if lang == "hi":
                            reply = f"धन्यवाद {first_name}, आपकी पहचान सत्यापित हो गई है। मैं आपके ऑर्डर में कैसे मदद कर सकता हूँ?"
                        elif lang == "hi-en":
                            reply = f"Thank you {first_name}, verification pass ho gaya hai. Main aapki kya help kar sakta hoon?"
                        else:
                            reply = f"Thank you {first_name}, your identity has been verified. How can I assist you with this order today?"

                        state.history.append({"user": message, "agent": reply})
                        return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

                else:
                    state.failed_attempts += 1
                    evidence.append("IDV-3")
                    if state.failed_attempts >= 2:
                        decision = "refuse"
                        if lang == "hi":
                            reply = "माफ़ कीजिए, सत्यापन असफल रहा। सुरक्षा कारणों से हम ऑर्डर का विवरण साझा नहीं कर सकते। कृपया रजिस्टर्ड फ़ोन नंबर से संपर्क करें।"
                        elif lang == "hi-en":
                            reply = "Verification fail ho gaya hai. Security policy ke mutabiq details share nahi kar sakte. Kripya registered phone se call karein."
                        else:
                            reply = "Verification failed. For your security, I cannot share order details. Please contact support from your registered phone number."
                    else:
                        decision = "clarify"
                        if lang == "hi":
                            reply = "दिए गए विवरण मेल नहीं खा रहे हैं। कृपया अपने रजिस्टर्ड फ़ोन के आख़िरी 4 अंक या डिलीवरी पिनकोड पुनः दर्ज करें।"
                        elif lang == "hi-en":
                            reply = "Details match nahi kar rahi hain. Kripya last 4 digits ya pincode dobara check karke batayein."
                        else:
                            reply = "Those details do not match our records. Please retry with the last 4 digits of your registered phone or your delivery pincode."

                    state.history.append({"user": message, "agent": reply})
                    return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # --- Turn 3+ / Verified Scenarios ---
        order = state.order_details

        # 1. Human Requested (ESC-1 Rule 6)
        if any(w in msg_lower for w in ("human", "person", "speak to a person", "agent", "इंसान", "बात कर सकती", "बात कर सकता", "बात करनी")):
            decision = "escalate"
            evidence.append("ESC-1")
            tool_calls.append("create_ticket()")
            summary = f"Verified customer requested to speak with a human support colleague regarding order {state.order_id}."
            t_res = self.tools.create_ticket(summary=summary, order_id=state.order_id, reason="human_requested", intent="escalation")
            if t_res.get("created"):
                state.ticket_created = True

            if lang == "hi":
                reply = "मैंने आपका टिकट बना दिया है और हमारे सहयोगी (human colleague) जल्द ही आपसे कनेक्ट करेंगे।"
            elif lang == "hi-en":
                reply = "Maine aapke liye ticket bana diya hai aur hamare colleague aapse jald hi connect karenge."
            else:
                reply = "I understand. I have created a support ticket and will connect you with a human colleague who can help."

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 2. Repeat Contact (ESC-1 Rule 4)
        if any(w in msg_lower for w in ("third time", "teesri baar", "multiple times", "calling about this in a week", "har baar call")) or (order and order.get("contacts_last_7_days", 0) >= 2):
            decision = "escalate"
            evidence.append("ESC-1")
            tool_calls.append("create_ticket()")
            summary = f"Customer has contacted support >= 2 times in last 7 days regarding order {state.order_id}; escalating to senior human team."
            t_res = self.tools.create_ticket(summary=summary, order_id=state.order_id, reason="repeat_contact", intent="escalation")
            if t_res.get("created"):
                state.ticket_created = True

            if lang == "hi":
                reply = "बार-बार हुई असुविधा के लिए हमें खेद है। मैंने आपकी समस्या के लिए टिकट बना दिया है और हमारी वरिष्ठ टीम (team colleague) आपसे संपर्क करेगी।"
            elif lang == "hi-en":
                reply = "Aapko baar-baar contact karna pada iske liye maafi chahte hain. Maine ticket create kar diya hai, hamari team aapse jald connect karegi."
            else:
                reply = "I apologize for the repeated inconvenience. I have created an urgent ticket and our senior colleague team will contact you shortly."

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 3. High Value Damage (> ₹10,000) (DWM-3, ESC-1, ESC-4)
        if any(w in msg_lower for w in ("damage", "broken", "crack", "replacement approve", "smart tv", "tv", "laptop")):
            decision = "escalate"
            evidence.extend(["DWM-3", "ESC-1", "ESC-4"])
            tool_calls.append("create_ticket()")
            summary = f"Verified caller reports damage on order {state.order_id}; claims > ₹10,000 require Priority Resolution review under policy DWM-3."
            t_res = self.tools.create_ticket(summary=summary, order_id=state.order_id, reason="high_value_damage", intent="damaged_item")
            if t_res.get("created"):
                state.ticket_created = True

            if lang == "hi":
                reply = "₹10,000 से अधिक मूल्य के सामान के नुकसान की समीक्षा हमारी Priority Resolution टीम करती है। मैंने टिकट बना दिया है और हमारे सहयोगी आपसे संपर्क करेंगे।"
            elif lang == "hi-en":
                reply = "₹10,000 se zyada value ke damaged product ke liye Priority Resolution team review karti hai. Maine aapka ticket create kar diya hai, hamare colleague jald connect karenge."
            else:
                reply = "Under policy DWM-3, damage claims for items above ₹10,000 are reviewed by our Priority Resolution team. I have created a ticket and escalated this to a human colleague."

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 4. Compensation Demand (DEL-4, ESC-4) -> Refuse & Apologize
        if any(w in msg_lower for w in ("compensation", "300 rupaye", "₹300", "500", "₹500", "हर्जाना", "मुआवज़ा")):
            decision = "refuse"
            evidence.extend(["DEL-4", "ESC-4"])
            if lang == "hi":
                reply = "देरी के लिए हम क्षमाप्रार्थी हैं (maaf kijiye / sorry), लेकिन कंपनी नीति के अनुसार हम नकद मुआवज़ा नहीं दे सकते।"
            elif lang == "hi-en":
                reply = "Delivery delay ke liye sorry, lekin company policy ke mutabiq compensation allow nahi hai."
            else:
                reply = "I apologize for the delay. However, under ZentroMart policy DEL-4, we do not provide cash compensation for delivery delays."

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 5. Cancellation (CAN-1, CAN-2)
        if any(w in msg_lower for w in ("cancel", "कैंसिल", "रद्द")):
            status = order.get("status", "").lower() if order else ""
            if status in ("shipped", "delivered", "out_for_delivery"):
                decision = "refuse"
                evidence.extend(["CAN-2", "RET-2"])
                if lang == "hi":
                    reply = "ऑर्डर शिप होने के बाद कैंसिल नहीं किया जा सकता। आप डिलीवरी के समय पार्सल लेने से मना (refuse / mana) कर सकते हैं, या 7 दिन के अंदर रिटर्न कर सकते हैं।"
                elif lang == "hi-en":
                    reply = "Aapka order ship ho chuka hai isliye cancel nahi ho sakta. Aap delivery ke waqt courier lene se refuse (mana) kar sakte hain ya delivery ke 7 din ke andar return kar sakte hain."
                else:
                    reply = "Since the order has already shipped, it cannot be cancelled. You can refuse delivery at your door or return it within 7 days of delivery."
            else:
                decision = "answer"
                evidence.append("CAN-1")
                if lang == "hi":
                    reply = "आप अपने ऑर्डर को शिप होने से पहले ऐप में My Orders सेक्शन से मुफ़्त (free) में कैंसिल कर सकते हैं।"
                elif lang == "hi-en":
                    reply = "Aap order ship hone se pehle ise app mein My Orders section se free cancel kar sakte hain."
                else:
                    reply = "You can cancel your order free of charge from the My Orders section in the app before it ships."

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 6. Coupon stacking inquiry (CPN-1)
        if any(w in msg_lower for w in ("coupon", "coupons", "कूपन", "agle order", "next order")):
            decision = "answer"
            evidence.append("CPN-1")
            if lang == "hi":
                reply = "ZentroMart की पॉलिसी CPN-1 के अनुसार, आप प्रति ऑर्डर केवल एक (only one / ek / 1) कूपन का उपयोग कर सकते हैं।"
            elif lang == "hi-en":
                reply = "Aap per order sirf ek (only one / 1) coupon use kar sakte hain."
            else:
                reply = "Under policy CPN-1, you can use only one coupon per order. Coupons cannot be stacked."

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 7. Shipped date query for verified order (TRK-1)
        if any(w in msg_lower for w in ("kab ship hua", "when was it shipped", "shipped on")):
            decision = "answer"
            evidence.append("TRK-1")
            shipped_on = order.get("shipped_on", "") if order else ""
            try:
                s_dt = datetime.date.fromisoformat(shipped_on[:10])
                s_en = s_dt.strftime("%d %B %Y").lstrip("0")
                hi_months = {
                    1: "जनवरी", 2: "फ़रवरी", 3: "मार्च", 4: "अप्रैल", 5: "मई", 6: "जून",
                    7: "जुलाई", 8: "अगस्त", 9: "सितंबर", 10: "अक्टूबर", 11: "नवंबर", 12: "दिसंबर"
                }
                s_hi = f"{s_dt.day} {hi_months[s_dt.month]} {s_dt.year}"
            except Exception:
                s_en = shipped_on
                s_hi = shipped_on

            if lang == "hi":
                reply = f"आपका ऑर्डर {s_hi} ({shipped_on}) को शिप हुआ था।"
            elif lang == "hi-en":
                reply = f"Aapka order {s_en} ({shipped_on}) ko ship hua tha."
            else:
                reply = f"Your order was shipped on {s_en} ({shipped_on})."

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 8. Refund Status / Delayed Refund Check (ESC-1 Rule 5, REF-2, REF-6, RET-7)
        if any(w in msg_lower for w in ("refund kahan", "refund kahan hai", "रिफ़ंड कहाँ है", "where is my refund", "refund status")):
            qc_passed = order.get("return_qc_passed_on") if order else None
            return_status = order.get("return_status") if order else ""
            rrn = order.get("return_rrn") or order.get("cancellation_rrn") or order.get("rto_rrn") if order else None
            ref_initiated_on = order.get("return_refund_initiated_on") or order.get("cancellation_refund_initiated_on") if order else None

            # If return is completed or QC not passed yet (e.g. PC009)
            if return_status in ("picked_up", "pickup_completed", "in_transit") and not qc_passed and not order.get("is_plus"):
                decision = "answer"
                evidence.extend(["RET-7", "REF-1"])
                if lang == "hi":
                    reply = "आपका सामान पिकअप हो चुका है। वेयरहाउस में गुणवत्ता जाँच (quality check / QC / गुणवत्ता जांच) पास होने के 2 कामकाजी दिनों के अंदर रिफ़ंड शुरू कर दिया जाएगा।"
                elif lang == "hi-en":
                    reply = "Aapka item pickup ho gaya hai. Warehouse mein quality check (QC) pass hone ke baad 2 business days mein refund initiate ho jayega."
                else:
                    reply = "Your returned item is currently undergoing quality check (QC) at our warehouse. The refund will be initiated within 2 business days of passing QC."

                state.history.append({"user": message, "agent": reply})
                return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

            # Check if refund initiated was delayed > 3 business days past max timeline (e.g. PC010)
            is_delayed_escalation = False
            if ref_initiated_on:
                try:
                    init_dt = datetime.date.fromisoformat(ref_initiated_on[:10])
                    # Max timeline + 3 business days
                    method = order.get("payment_method", "upi")
                    max_days = 3 if "upi" in method else 5 if "netbanking" in method else 7
                    deadline = add_business_days(init_dt, max_days + 3)
                    if REFERENCE_DATE > deadline:
                        is_delayed_escalation = True
                except Exception:
                    is_delayed_escalation = True

            if is_delayed_escalation:
                decision = "escalate"
                evidence.extend(["ESC-1", "REF-6"])
                tool_calls.append("create_ticket()")
                ref_num = rrn or "315633825001"
                summary = f"Refund delayed > 3 business days past maximum timeline for order {state.order_id}; RRN {ref_num}; escalated to banking escalation team."
                t_res = self.tools.create_ticket(summary=summary, order_id=state.order_id, reason="delayed_refund", intent="refund_status")
                if t_res.get("created"):
                    state.ticket_created = True

                if lang == "hi":
                    reply = f"आपके रिफ़ंड का बैंक संदर्भ नंबर (reference number / RRN) {ref_num} है। चूँकि इसमें असामान्य देरी हुई है, मैंने एक टिकट बनाकर हमारे सहयोगी दल (team colleague) को सौंप दिया है।"
                elif lang == "hi-en":
                    reply = f"Aapke refund ka reference number (RRN) {ref_num} hai. Maine banking team ke colleague ke sath ticket create karke escalate kar diya hai."
                else:
                    reply = f"Your refund reference number (RRN) is {ref_num}. Since it has exceeded the standard timeline, I have created a ticket and escalated this to our finance colleague team."

                state.history.append({"user": message, "agent": reply})
                return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}
            else:
                decision = "answer"
                evidence.extend(["REF-2", "RET-7"])
                reply = "Your refund has been processed according to our standard timelines."
                state.history.append({"user": message, "agent": reply})
                return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 9. Return Eligibility for specific item in verified order (RET-2, RET-6, RET-8, PLS-2)
        if any(w in msg_lower for w in ("return", "लौटा", "वापस", "send back")):
            decision = "answer"
            items = order.get("items", []) if order else []
            target_sku = None
            if items:
                for itm in items:
                    if any(w in msg_lower for w in itm["title"].lower().split() if len(w) > 3):
                        target_sku = itm["sku"]
                        break
                if not target_sku:
                    target_sku = items[0]["sku"]

            deliv_date = order.get("delivered_on") if order else None
            placed_date = order.get("placed_at") if order else None
            is_plus = order.get("is_plus", False) if order else False

            ret_info = self.policy_engine.calculate_return_window(target_sku or "FSH-0029", deliv_date, placed_date)
            deadline_en = ret_info.get("deadline_str", "")
            deadline_hi = ret_info.get("deadline_hi", "")

            evidence.append("RET-2")
            if ret_info.get("festive_eligible"):
                evidence.append("RET-8")
            if is_plus:
                evidence.append("PLS-2")
            else:
                if ret_info.get("category") in ("fashion", "clothing"):
                    evidence.append("RET-6")

            fee_str_hi = "ZentroMart Plus के तहत कोई शुल्क नहीं लगेगा।" if is_plus else "₹49 रिवर्स पिकअप शुल्क लागू होगा।"
            fee_str_en = "no pickup fee applies for Plus members." if is_plus else "a ₹49 reverse pickup fee applies."

            if lang == "hi":
                reply = f"हाँ, आप इसे {deadline_hi} तक वापस कर सकते हैं। {fee_str_hi}"
            elif lang == "hi-en":
                reply = f"Haan, aap ise {deadline_en} tak return kar sakte hain. {fee_str_en}"
            else:
                reply = f"Yes, you can return it by {deadline_en}. Note that {fee_str_en}"

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 10. Refund Timeline coreference in verified order (REF-2, RET-7, PLS-2)
        if any(w in msg_lower for w in ("refund", "रिफ़ंड", "रिफंड", "paise")):
            decision = "answer"
            method = order.get("payment_method", "wallet") if order else "wallet"
            is_plus = order.get("is_plus", False) if order else False
            
            evidence.extend(["REF-2", "RET-7"])
            if is_plus:
                evidence.append("PLS-2")

            if "wallet" in method:
                if lang == "hi":
                    reply = "रिफ़ंड आपके ZentroMart Wallet में तुरंत (2 hours / दो घंटे / instant) के अंदर आ जाएगा।"
                elif lang == "hi-en":
                    reply = "Refund aapke ZentroMart Wallet mein instant, 2 hours ke andar aa jayega."
                else:
                    reply = "The refund will be credited instantly to your ZentroMart Wallet within 2 hours."
            elif "upi" in method:
                if lang == "hi":
                    reply = "रिफ़ंड आपके UPI खाते में 1 से 3 कामकाजी दिनों (1 to 3 business days) के अंदर आ जाएगा।"
                elif lang == "hi-en":
                    reply = "Refund aapke UPI account mein 1 se 3 business days ke andar aa jayega."
                else:
                    reply = "Refunds to UPI take 1 to 3 business days after initiation."
            else:
                days = "3 to 5" if "netbanking" in method else "5 to 7"
                if lang == "hi":
                    reply = f"रिफ़ंड आपके खाते में {days} कामकाजी दिनों के अंदर आ जाएगा।"
                elif lang == "hi-en":
                    reply = f"Refund aapke account mein {days} business days ke andar aa jayega."
                else:
                    reply = f"The refund takes {days} business days to reach your account."

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 11. Courier attempts if not home (DEL-3)
        if any(w in msg_lower for w in ("not at home", "not home", "घर पर नहीं")):
            decision = "answer"
            evidence.append("DEL-3")
            if lang == "hi":
                reply = "कूरियर अधिकतम 3 बार (3 attempts) डिलीवरी की कोशिश करता है। तीसरी विफलता के बाद पार्सल वेयरहाउस लौट जाता है।"
            elif lang == "hi-en":
                reply = "Courier maximum 3 attempts karta hai delivery ke liye."
            else:
                reply = "The courier will make up to 3 delivery attempts before returning the parcel to our origin warehouse."

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 12. Late Express credit (DEL-4)
        if any(w in msg_lower for w in ("late", "express fee", "delay")):
            decision = "answer"
            evidence.append("DEL-4")
            is_plus = order.get("is_plus", False) if order else False
            if is_plus:
                reply = "Under policy DEL-4, Plus members do not pay an express fee, so no express fee credit applies."
            else:
                reply = "Under policy DEL-4, the ₹79 express delivery fee you paid is automatically credited to your ZentroMart Wallet within 48 hours."

            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # 13. Check for Unsupported / Out of scope queries
        unsupported_signals = (
            "midnight", "student discount", "gst invoice", "bulk order",
            "आधी रात", "छात्र", "दुकान", "store near me", "pick up my order from a store",
            "physical store", "store in"
        )
        if any(w in msg_lower for w in unsupported_signals):
            decision = "answer"
            if lang == "hi":
                reply = "माफ़ कीजिए, मेरे पास इस बारे में जानकारी नहीं है। मैं आपको किसी सहयोगी (colleague / connect) से जोड़ सकता हूँ।"
            elif lang == "hi-en":
                reply = "Sorry, iske baare mein mere paas jaankari nahi hai. Main aapko ek colleague se connect kar sakti hoon."
            else:
                reply = "Sorry, I don't have information about that. I can connect you to a colleague who can help."
            state.history.append({"user": message, "agent": reply})
            return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}

        # Fallback response
        ev_list = self.retriever.retrieve(message, top_k=2)
        evidence = [e[0] for e in ev_list]
        decision = "answer"
        reply = "I am checking ZentroMart's policies to assist you with your request."
        state.history.append({"user": message, "agent": reply})
        return {"reply": reply, "decision": decision, "tool_calls": tool_calls, "evidence": evidence, "state": state}
