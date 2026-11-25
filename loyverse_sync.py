import requests
import json
from typing import Dict, Any, List, Optional
from database import record_transaction, get_member, get_connection

LOYVERSE_API_BASE = "https://api.loyverse.com/v1.0"

class LoyverseClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        } if token else {}

    def is_configured(self) -> bool:
        return bool(self.token)

    def get_customers(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        url = f"{LOYVERSE_API_BASE}/customers?limit={limit}"
        resp = requests.get(url, headers=self.headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("customers", [])
        return []

    def get_receipts(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        url = f"{LOYVERSE_API_BASE}/receipts?limit={limit}"
        resp = requests.get(url, headers=self.headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("receipts", [])
        return []

    def process_webhook_receipt(self, receipt: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a Loyverse receipt:
        - If contains an item with 'Recarga' -> Records RECARGA
        - If paid with 'Monedero' or 'Argos' -> Records CONSUMO
        """
        receipt_id = receipt.get("receipt_number") or receipt.get("id")
        customer_id = receipt.get("customer_id")
        
        member_code = None
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT code FROM members WHERE loyverse_id = ? OR code = ?", (customer_id, customer_id))
        row = cursor.fetchone()
        if row:
            member_code = row["code"]
        else:
            cursor.execute("SELECT code FROM members LIMIT 1")
            fallback = cursor.fetchone()
            member_code = fallback["code"] if fallback else "Argonauta 01"
        conn.close()

        results = []
        
        # 1. Line items: Recargas
        line_items = receipt.get("line_items", [])
        for item in line_items:
            item_name = item.get("item_name", "")
            if "recarga" in item_name.lower():
                amount = float(item.get("total_money_amount", 0.0))
                if amount > 0:
                    record_transaction(
                        member_code=member_code,
                        tx_type="RECARGA",
                        amount=amount,
                        payment_method="Efectivo/Tarjeta",
                        receipt_id=str(receipt_id),
                        description=f"Recarga en caja: {item_name}"
                    )
                    results.append({"type": "RECARGA", "amount": amount, "member": member_code})

        # 2. Payments: Monedero / Argos / Argonauta
        payments = receipt.get("payments", [])
        for p in payments:
            p_name = p.get("name", "")
            if any(k in p_name.lower() for k in ["monedero", "argos", "argonauta"]):
                amount = float(p.get("money_amount", 0.0))
                if amount > 0:
                    record_transaction(
                        member_code=member_code,
                        tx_type="CONSUMO",
                        amount=amount,
                        payment_method="Monedero Argonauta",
                        receipt_id=str(receipt_id),
                        description="Consumo en cafetería"
                    )
                    results.append({"type": "CONSUMO", "amount": amount, "member": member_code})

        return {"processed": len(results), "transactions": results}
