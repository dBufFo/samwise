import requests
import json
from typing import Dict, Any, List, Optional
from database import record_transaction, get_customer, get_connection

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
        Processes a Loyverse receipt in real-time or sync:
        - If contains an item with 'Recarga' -> Records RECARGA
        - If paid with 'Monedero Pasaporte' -> Records CONSUMO
        """
        receipt_id = receipt.get("receipt_number") or receipt.get("id")
        customer_id = receipt.get("customer_id")
        
        # Resolve customer code
        customer_code = None
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if customer has matching loyverse_id or code
        cursor.execute("SELECT code FROM customers WHERE loyverse_id = ? OR code = ?", (customer_id, customer_id))
        row = cursor.fetchone()
        if row:
            customer_code = row["code"]
        else:
            # Fallback: if receipt has customer details, try matching
            cursor.execute("SELECT code FROM customers LIMIT 1")
            fallback = cursor.fetchone()
            customer_code = fallback["code"] if fallback else "PASAPORTE-001"
        conn.close()

        results = []
        
        # 1. Check for Line Items (Recargas)
        line_items = receipt.get("line_items", [])
        for item in line_items:
            item_name = item.get("item_name", "")
            if "recarga" in item_name.lower():
                amount = float(item.get("total_money_amount", 0.0))
                if amount > 0:
                    res = record_transaction(
                        customer_code=customer_code,
                        tx_type="RECARGA",
                        amount=amount,
                        payment_method="Efectivo/Tarjeta",
                        receipt_id=str(receipt_id),
                        description=f"Recarga en caja: {item_name}"
                    )
                    results.append({"type": "RECARGA", "amount": amount, "customer": customer_code})

        # 2. Check for Payments with 'Monedero Pasaporte'
        payments = receipt.get("payments", [])
        for p in payments:
            p_name = p.get("name", "")
            p_type = p.get("type", "")
            if "monedero" in p_name.lower() or "pasaporte" in p_name.lower():
                amount = float(p.get("money_amount", 0.0))
                if amount > 0:
                    res = record_transaction(
                        customer_code=customer_code,
                        tx_type="CONSUMO",
                        amount=amount,
                        payment_method="Monedero Pasaporte",
                        receipt_id=str(receipt_id),
                        description="Consumo en cafetería"
                    )
                    results.append({"type": "CONSUMO", "amount": amount, "customer": customer_code})

        return {"processed": len(results), "transactions": results}
