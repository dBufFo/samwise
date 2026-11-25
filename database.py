import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "samwise.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clientes / Miembros de la Comunidad Argos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        affiliation_type TEXT DEFAULT 'Regular', -- 'Regular', 'Estudiante', 'Cliente Especial', 'Argonáuta', 'Escritor', 'Grey Creativa'
        discount_rate REAL DEFAULT 0.0,
        loyverse_id TEXT,
        stamps REAL DEFAULT 0.0,
        birthdate TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Transacciones (Ledger Inmutable)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_code TEXT NOT NULL,
        tx_type TEXT NOT NULL, -- 'RECARGA', 'CONSUMO', 'CANJE_SELLOS', 'BREAKAGE'
        amount REAL NOT NULL,
        stamps_delta REAL DEFAULT 0.0,
        payment_method TEXT,
        receipt_id TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (member_code) REFERENCES members(code)
    )
    """)
    
    # Catálogo de Premios por Sellos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rewards_catalog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        stamps_cost INTEGER NOT NULL,
        category TEXT DEFAULT 'Cafetería',
        active INTEGER DEFAULT 1
    )
    """)
    
    # Seed initial rewards
    rewards = [
        ("Café Americano de Especialidad", 6, "Cafetería"),
        ("Croissant Francés de Mantequilla", 8, "Repostería"),
        ("Termo Conmemorativo Argos", 25, "Colección"),
        ("Libro Selección Fondo Editorial", 40, "Librería")
    ]
    for r_name, r_stamps, r_cat in rewards:
        cursor.execute("""
        INSERT OR IGNORE INTO rewards_catalog (name, stamps_cost, category)
        VALUES (?, ?, ?)
        """, (r_name, r_stamps, r_cat))

    # Seed initial beta Argonautas
    beta_members = [
        ("Argonauta 01", "Carlos Beta (Amigo)", "carlos@argos.mx", "Estudiante", 0.10, 6.0, "1998-05-14"),
        ("Argonauta 02", "Ana Beta (Familiar)", "ana@argos.mx", "Grey Creativa", 0.05, 12.0, "1965-08-22"),
        ("Argonauta 03", "Prueba Beta 03", "prueba@argos.mx", "Regular", 0.00, 0.0, "2000-11-20")
    ]
    
    for code, name, email, aff, disc, stamps, bdate in beta_members:
        cursor.execute("""
        INSERT OR IGNORE INTO members (code, name, email, affiliation_type, discount_rate, stamps, birthdate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (code, name, email, aff, disc, stamps, bdate))
        
    conn.commit()
    conn.close()

def normalize_code(code: str) -> str:
    """Normalizes input like '01', 'argonauta 01', 'ARGONAUTA 1' to 'Argonauta 01'"""
    clean = code.strip()
    digits = "".join([c for c in clean if c.isdigit()])
    if digits:
        num = int(digits)
        return f"Argonauta {num:02d}"
    return clean

def get_member(code: str) -> Optional[Dict[str, Any]]:
    norm_code = normalize_code(code)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE code = ? COLLATE NOCASE", (norm_code,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_member_balance(code: str) -> Optional[Dict[str, Any]]:
    norm_code = normalize_code(code)
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM members WHERE code = ? COLLATE NOCASE", (norm_code,))
    m_row = cursor.fetchone()
    if not m_row:
        conn.close()
        return None
    
    real_code = m_row["code"]
    
    # Calculate sum of RECARGA minus CONSUMO and BREAKAGE
    cursor.execute("""
    SELECT 
        COALESCE(SUM(CASE WHEN tx_type = 'RECARGA' THEN amount ELSE 0 END), 0) as total_recargas,
        COALESCE(SUM(CASE WHEN tx_type = 'CONSUMO' THEN amount ELSE 0 END), 0) as total_consumos,
        COALESCE(SUM(CASE WHEN tx_type = 'BREAKAGE' THEN amount ELSE 0 END), 0) as total_breakage
    FROM transactions 
    WHERE member_code = ?
    """, (real_code,))
    
    calc = cursor.fetchone()
    cash_balance = calc["total_recargas"] - calc["total_consumos"] - calc["total_breakage"]
    
    # Recent transactions
    cursor.execute("""
    SELECT id, tx_type, amount, stamps_delta, payment_method, receipt_id, description, created_at
    FROM transactions
    WHERE member_code = ?
    ORDER BY created_at DESC LIMIT 10
    """, (real_code,))
    history = [dict(r) for r in cursor.fetchall()]
    
    # Catalog of available rewards
    cursor.execute("SELECT * FROM rewards_catalog WHERE active = 1 ORDER BY stamps_cost ASC")
    rewards = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        "code": real_code,
        "name": m_row["name"],
        "affiliation_type": m_row["affiliation_type"],
        "discount_rate": m_row["discount_rate"],
        "stamps": m_row["stamps"],
        "birthdate": m_row["birthdate"],
        "cash_balance": round(cash_balance, 2),
        "total_recargas": round(calc["total_recargas"], 2),
        "total_consumos": round(calc["total_consumos"], 2),
        "history": history,
        "rewards": rewards
    }

def record_transaction(member_code: str, tx_type: str, amount: float, 
                       payment_method: str = "Efectivo", receipt_id: str = None, 
                       description: str = None) -> Optional[Dict[str, Any]]:
    norm_code = normalize_code(member_code)
    member = get_member(norm_code)
    if not member:
        return None
        
    real_code = member["code"]
    
    # Calculate stamps: 8% on consumption (NOT on recharge)
    # $100 consumption = 1 stamp ($8 value)
    stamps_delta = 0.0
    if tx_type.upper() == "CONSUMO":
        stamps_delta = round(amount * 0.08 / 8.0, 2) # exactly 1 stamp per 100 pesos spent
    elif tx_type.upper() == "CANJE_SELLOS":
        stamps_delta = -float(amount) # amount represents stamps deducted
        
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO transactions (member_code, tx_type, amount, stamps_delta, payment_method, receipt_id, description)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (real_code, tx_type.upper(), amount, stamps_delta, payment_method, receipt_id, description))
    
    # Update member stamps
    if stamps_delta != 0.0:
        cursor.execute("UPDATE members SET stamps = MAX(0.0, stamps + ?) WHERE code = ?", (stamps_delta, real_code))
        
    conn.commit()
    conn.close()
    
    return get_member_balance(real_code)

if __name__ == "__main__":
    init_db()
    print("Database samwise.db initialized successfully!")
