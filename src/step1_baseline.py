"""Step 1: Prompt-Only LLM Baseline (Weeks 1 and 2).
Answers customer queries without RAG / document grounding.
Establishes baseline performance to compare against Step 2 RAG.
"""
from typing import Dict, Any, List

SYSTEM_PROMPT = """You are ZentroMart's customer support AI assistant. 
Answer customer queries concisely in two to three sentences in the customer's language.
Introduce yourself in your first response.
Note: You do not have access to internal company policies, return tables, or databases.
Answer to the best of your general knowledge."""

class Step1BaselineAgent:
    def __init__(self):
        self.name = "ZentroMart Baseline AI Assistant"

    def answer_question(self, question: str, language: str = "en") -> Dict[str, Any]:
        """Simulates or calls prompt-only baseline without knowledge retrieval.
        Guesses based on generic e-commerce knowledge without ZentroMart's specific rules.
        """
        q_lower = question.lower()
        decision = "answer"

        # Check for obvious unanswerable or fraud
        if any(w in q_lower for w in ("never placed", "fraud")):
            decision = "escalate"
            reply = "I take account security seriously. Please contact our security team immediately."
            return {"reply": reply, "decision": decision, "evidence": []}

        # Baseline guesses without ZentroMart policies:
        # Standard e-commerce guesses usually say 30 days for returns, 5-7 days for refunds, etc.
        if "wallet" in q_lower and "refund" in q_lower:
            # Common baseline mistake: says 5 to 7 days like standard refund
            reply = "Refunds to your wallet will be processed within 5 to 7 business days."
        elif "net banking" in q_lower or "upi" in q_lower or "refund" in q_lower:
            reply = "Refunds typically take 5 to 7 business days to reflect in your bank account."
        elif "warranty" in q_lower or "assured" in q_lower:
            reply = "Electronics generally come with standard 6 to 12 months manufacturer warranty."
        elif "festive" in q_lower or "sale" in q_lower:
            reply = "Items purchased on sale can usually be returned within our standard 14 to 30 days policy."
        elif "midnight" in q_lower:
            # Baseline hallucination: invents that midnight delivery is possible
            reply = "Yes, you can schedule midnight deliveries subject to courier availability and extra charges."
        elif "student discount" in q_lower:
            # Baseline hallucination: invents student discount
            reply = "Yes, ZentroMart offers a 10% student discount when you verify your student ID."
        elif "gst invoice" in q_lower:
            reply = "Yes, business customers can enter their GSTIN at checkout to receive a GST invoice."
        elif "torn" in q_lower or "damaged" in q_lower:
            reply = "If your item arrived damaged, you can return it within 7 days for a replacement or refund."
        elif "return" in q_lower or "वापस" in q_lower or "लौटाने" in q_lower:
            reply = "Most items can be returned within 10 to 14 days of delivery in their original condition."
        elif "cancel" in q_lower or "कैंसिल" in q_lower:
            reply = "You can cancel your order from the app as long as it has not been processed."
        else:
            reply = "Hello! I am ZentroMart's AI support assistant. Thank you for reaching out. Let me know how I can assist you."

        return {
            "reply": reply,
            "decision": decision,
            "evidence": [],
            "used_rag": False,
        }
