import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "pasaporte.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        loyverse_id TEXT,
        points REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Transacciones (Ledger)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_code TEXT NOT NULL,
        tx_type TEXT NOT NULL, -- 'RECARGA', 'CONSUMO', 'BREAKAGE'
        amount REAL NOT NULL,
        payment_method TEXT,
        receipt_id TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_code) REFERENCES customers(code)
    )
    """)
    
    # Breakage Log (NIF D-1 / IFRS 15)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS breakage_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_code TEXT NOT NULL,
        expired_amount REAL NOT NULL,
        recognized_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT
    )
    """)
    
    # Seed initial beta customers if not present
    beta_customers = [
        ("PASAPORTE-001", "Carlos Beta (Amigo)", "carlos@beta.com", 10.0),
        ("PASAPORTE-002", "Ana Beta (Familiar)", "ana@beta.com", 5.0),
        ("PASAPORTE-003", "Prueba Beta 3", "prueba@beta.com", 0.0)
    ]
    
    for code, name, email, points in beta_customers:
        cursor.execute("""
        INSERT OR IGNORE INTO customers (code, name, email, points)
        VALUES (?, ?, ?, ?)
        """, (code, name, email, points))
        
    conn.commit()
    conn.close()

def get_customer(code: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE code = ?", (code,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_customer_balance(code: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get Customer
    cursor.execute("SELECT * FROM customers WHERE code = ?", (code,))
    cust_row = cursor.fetchone()
    if not cust_row:
        conn.close()
        return None
    
    # Calculate sum of RECARGA minus CONSUMO and BREAKAGE
    cursor.execute("""
    SELECT 
        COALESCE(SUM(CASE WHEN tx_type = 'RECARGA' THEN amount ELSE 0 END), 0) as total_recargas,
        COALESCE(SUM(CASE WHEN tx_type = 'CONSUMO' THEN amount ELSE 0 END), 0) as total_consumos,
        COALESCE(SUM(CASE WHEN tx_type = 'BREAKAGE' THEN amount ELSE 0 END), 0) as total_breakage
    FROM transactions 
    WHERE customer_code = ?
    """, (code,))
    
    calc = cursor.fetchone()
    balance = calc["total_recargas"] - calc["total_consumos"] - calc["total_breakage"]
    
    # Recent transactions
    cursor.execute("""
    SELECT id, tx_type, amount, payment_method, receipt_id, description, created_at
    FROM transactions
    WHERE customer_code = ?
    ORDER BY created_at DESC LIMIT 10
    """, (code,))
    history = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        "code": cust_row["code"],
        "name": cust_row["name"],
        "points": cust_row["points"],
        "balance": round(balance, 2),
        "total_recargas": round(calc["total_recargas"], 2),
        "total_consumos": round(calc["total_consumos"], 2),
        "history": history
    }

def record_transaction(customer_code: str, tx_type: str, amount: float, 
                       payment_method: str = "Efectivo", receipt_id: str = None, 
                       description: str = None) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO transactions (customer_code, tx_type, amount, payment_method, receipt_id, description)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (customer_code, tx_type.upper(), amount, payment_method, receipt_id, description))
    
    tx_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return get_customer_balance(customer_code)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
