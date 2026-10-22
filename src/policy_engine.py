"""ZentroMart Policy & Business Logic Engine.
Implements exact company policies: return windows, refund dates, fees, escalation triggers,
business day counting, and verification constraints.
"""
import datetime
from typing import Dict, Any, Optional, Tuple, List
from .config import REFERENCE_DATE, is_business_day, add_business_days, get_refund_window
from .data_loader import DataLoader

class PolicyEngine:
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
        self.today = REFERENCE_DATE

    def calculate_refund_dates(self, start_date_str: str, method: str) -> Dict[str, Any]:
        """Calculates refund completion window using business days."""
        try:
            start_date = datetime.date.fromisoformat(start_date_str[:10])
        except Exception:
            start_date = self.today

        method = (method or "").lower()
        if "wallet" in method:
            return {
                "type": "instant",
                "text_en": "Instant, within 2 hours of initiation.",
                "text_hi": "तुरंत, 2 घंटे के अंदर आपके ZentroMart Wallet में।",
                "text_hien": "Instant, 2 hours ke andar aapke ZentroMart Wallet mein.",
            }

        days_range = (1, 3) if "upi" in method else (3, 5) if "netbanking" in method or "net banking" in method else (5, 7)
        d_min = add_business_days(start_date, days_range[0])
        d_max = add_business_days(start_date, days_range[1])

        fmt_min_en = d_min.strftime("%d %B %Y").lstrip("0")
        fmt_max_en = d_max.strftime("%d %B %Y").lstrip("0")
        iso_max = d_max.isoformat()

        # Hindi month names
        hi_months = {
            1: "जनवरी", 2: "फ़रवरी", 3: "मार्च", 4: "अप्रैल", 5: "मई", 6: "जून",
            7: "जुलाई", 8: "अगस्त", 9: "सितंबर", 10: "अक्टूबर", 11: "नवंबर", 12: "दिसंबर"
        }
        fmt_min_hi = f"{d_min.day} {hi_months[d_min.month]} {d_min.year}"
        fmt_max_hi = f"{d_max.day} {hi_months[d_max.month]} {d_max.year}"

        return {
            "type": "business_days",
            "min_days": days_range[0],
            "max_days": days_range[1],
            "earliest_date": d_min,
            "latest_date": d_max,
            "iso_max": iso_max,
            "text_en": f"Between {fmt_min_en} and {fmt_max_en}, counting business days: Monday to Saturday, skipping warehouse holidays.",
            "text_hien": f"{fmt_min_en} se {fmt_max_en} ke beech; Sunday aur warehouse holidays nahi gine jaate.",
            "text_hi": f"{fmt_min_hi} से {fmt_max_hi} के बीच (रविवार और गोदाम की छुट्टियाँ छोड़कर)।",
            "target_deadline": fmt_max_en,
            "target_deadline_hi": fmt_max_hi,
        }

    def calculate_return_window(self, product_sku: str, delivered_date_str: Optional[str] = None,
                                placed_date_str: Optional[str] = None) -> Dict[str, Any]:
        """Calculates return window in calendar days according to RET-2, RET-3, RET-8."""
        prod = self.data_loader.get_product(product_sku)
        if not prod:
            return {"returnable": False, "reason": "Product not found"}

        cat = prod.get("return_category", "unknown")
        
        # Non-returnable categories (RET-5)
        if cat in ("grocery", "innerwear", "digital"):
            return {
                "returnable": False,
                "category": cat,
                "days": 0,
                "text_en": "This item is not returnable for change of mind under policy RET-5.",
                "text_hi": "यह सामान पॉलिसी के तहत वापस नहीं किया जा सकता।",
                "text_hien": "Yeh item policy ke mutabiq return nahi kiya ja sakta.",
            }

        # Delivered date
        deliv_date = None
        if delivered_date_str:
            try:
                deliv_date = datetime.date.fromisoformat(delivered_date_str[:10])
            except Exception:
                pass

        # Placed date
        placed_date = None
        if placed_date_str:
            try:
                placed_date = datetime.date.fromisoformat(placed_date_str[:10])
            except Exception:
                pass

        # Base days by category
        days = 10
        if cat == "electronics":
            # RET-3: If delivered before 1 August 2026, 10 days; else 7 days
            if deliv_date and deliv_date < datetime.date(2026, 8, 1):
                days = 10
            else:
                days = 7
        elif cat == "fashion":
            # RET-8: Festive sale placed between 01 Oct 2026 and 15 Oct 2026 gets 30 days; else 15 days
            if placed_date and datetime.date(2026, 10, 1) <= placed_date <= datetime.date(2026, 10, 15):
                days = 30
            else:
                days = 15
        elif cat == "beauty_sealed":
            days = 7
        elif cat in ("home_kitchen", "books_media"):
            days = 10

        deadline_str = ""
        deadline_hi = ""
        iso_deadline = ""
        is_expired = False
        if deliv_date:
            deadline = deliv_date + datetime.timedelta(days=days)
            iso_deadline = deadline.isoformat()
            deadline_str = deadline.strftime("%d %B %Y").lstrip("0")
            hi_months = {
                1: "जनवरी", 2: "फ़रवरी", 3: "मार्च", 4: "अप्रैल", 5: "मई", 6: "जून",
                7: "जुलाई", 8: "अगस्त", 9: "सितंबर", 10: "अक्टूबर", 11: "नवंबर", 12: "दिसंबर"
            }
            deadline_hi = f"{deadline.day} {hi_months[deadline.month]} {deadline.year}"
            is_expired = self.today > deadline

        return {
            "returnable": True,
            "category": cat,
            "days": days,
            "deliv_date": deliv_date,
            "deadline_str": deadline_str,
            "deadline_hi": deadline_hi,
            "iso_deadline": iso_deadline,
            "is_expired": is_expired,
            "festive_eligible": (days == 30),
        }

    def check_escalation(self, order: Optional[Dict[str, Any]], query_intent: str, message: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Checks ESC-1 escalation conditions. Returns (should_escalate, reason, intent)."""
        msg_lower = message.lower()

        # 1. High value damage > 10,000
        if order:
            dmg_sku = order.get("damage_sku")
            items = order.get("items", [])
            for itm in items:
                price = itm.get("unit_price_inr", 0)
                qty = itm.get("qty", 1)
                if price * qty > 10000 and (dmg_sku == itm.get("sku") or any(w in msg_lower for w in ('damage', 'tv', 'smart tv', 'laptop', 'खराब', 'टूट'))):
                    return True, "high_value_damage", "damaged_item"

        # 2. Unauthorized order / account fraud
        if any(w in msg_lower for w in ("never placed", "didn't order", "not my order", "fraud", "hacked", "account security")):
            return True, "fraud_report", "fraud"

        # 3. Legal / police / court
        if any(w in msg_lower for w in ("lawyer", "legal", "court", "police", "consumer forum", "consumer court")):
            return True, "legal_threat", "escalation"

        # 4. Repeat contact >= 2
        if order and order.get("contacts_last_7_days", 0) >= 2:
            return True, "repeat_contact", "repeat_contact"

        # 5. Customer explicitly requests human
        if any(w in msg_lower for w in ("human", "person", "agent", "colleague", "इंसान", "बात करनी", "बात कर सकती", "बात कर सकता", "someone else")):
            return True, "human_requested", "human_requested"

        # 6. Safety risk
        if any(w in msg_lower for w in ("spark", "burning", "smoke", "swelling", "shock", "fire", "blast", "injury")):
            return True, "safety_risk", "safety"

        return False, None, None
