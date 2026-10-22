"""Data Loader for ZentroMart Capstone CSV Tables.
Loads customers, orders, order items, products, pincodes, and holidays with string ID preservation.
"""
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
from .config import DATA_DIR

TEXT_COLS = {
    'order_id', 'customer_id', 'delivery_pincode', 'return_rrn',
    'cancellation_rrn', 'rto_rrn', 'sku', 'return_sku', 'damage_sku',
    'pincode', 'phone', 'coupon_code'
}

def clean_row(row: Dict[str, str]) -> Dict[str, Any]:
    out = {}
    for key, val in row.items():
        if val == '' or val is None:
            out[key] = None
        elif val == 'True':
            out[key] = True
        elif val == 'False':
            out[key] = False
        elif key not in TEXT_COLS and val.lstrip('-').isdigit():
            out[key] = int(val)
        else:
            out[key] = val
    return out

class DataLoader:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.order_items: Dict[str, List[Dict[str, Any]]] = {}
        self.products: Dict[str, Dict[str, Any]] = {}
        self.pincodes: Dict[str, Dict[str, Any]] = {}
        self.holidays: List[Dict[str, Any]] = []
        self._load_all()

    def _read_csv(self, filename: str) -> List[Dict[str, Any]]:
        path = self.data_dir / filename
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8", newline="") as f:
            return [clean_row(row) for row in csv.DictReader(f)]

    def _load_all(self):
        # Customers
        for c in self._read_csv("customers.csv"):
            self.customers[c["customer_id"]] = c

        # Products
        for p in self._read_csv("products.csv"):
            self.products[p["sku"]] = p

        # Pincodes
        for pc in self._read_csv("pincodes.csv"):
            self.pincodes[pc["pincode"]] = pc

        # Holidays
        self.holidays = self._read_csv("holidays.csv")

        # Orders
        for o in self._read_csv("orders.csv"):
            self.orders[o["order_id"]] = o

        # Order Items
        for item in self._read_csv("order_items.csv"):
            oid = item["order_id"]
            if oid not in self.order_items:
                self.order_items[oid] = []
            self.order_items[oid].append(item)

    def get_product(self, sku: str) -> Optional[Dict[str, Any]]:
        return self.products.get(sku)

    def find_product_by_name(self, query: str) -> Optional[Dict[str, Any]]:
        q = query.lower()
        # Direct exact or substring match
        best_match = None
        best_len = 0
        for sku, prod in self.products.items():
            title_lower = prod["title"].lower()
            if title_lower in q or any(word in q for word in title_lower.split() if len(word) > 4):
                if len(title_lower) > best_len:
                    best_match = prod
                    best_len = len(title_lower)
        return best_match

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self.orders.get(str(order_id).strip())

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        return self.customers.get(str(customer_id).strip())

    def get_pincode_info(self, pincode: str) -> Optional[Dict[str, Any]]:
        return self.pincodes.get(str(pincode).strip())
