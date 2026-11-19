import os
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
from database import init_db, get_customer_balance, record_transaction, get_customer, get_connection
from loyverse_sync import LoyverseClient

app = FastAPI(title="Pasaporte Primavera Backend", version="1.0.0")

# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()

# Loyverse Client instance (set token via env or config)
LOYVERSE_TOKEN = os.getenv("LOYVERSE_TOKEN", "")
loyverse_client = LoyverseClient(LOYVERSE_TOKEN)

# Pydantic Models
class TransactionCreate(BaseModel):
    customer_code: str
    tx_type: str # 'RECARGA', 'CONSUMO', 'BREAKAGE'
    amount: float
    payment_method: Optional[str] = "Efectivo"
    receipt_id: Optional[str] = None
    description: Optional[str] = None

# -----------------
# VISTAS WEB (HTML)
# -----------------

@app.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse(url="/consulta")

@app.get("/consulta", response_class=HTMLResponse)
def consulta_form():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Consultar Saldo | Pasaporte Primavera</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-slate-800 rounded-3xl p-8 border border-slate-700 shadow-2xl">
            <div class="text-center mb-8">
                <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-amber-500/20 text-amber-400 mb-4 text-3xl">
                    ☕
                </div>
                <h1 class="text-2xl font-bold tracking-tight text-white">Pasaporte Primavera</h1>
                <p class="text-sm text-slate-400 mt-1">Cafetería de Especialidad · Cuernavaca</p>
            </div>

            <form action="/buscar" method="POST" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                        Código de Pasaporte
                    </label>
                    <input type="text" name="code" placeholder="Ej: PASAPORTE-001" required
                        class="w-full px-4 py-3.5 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 text-center uppercase tracking-widest font-mono text-lg font-bold">
                </div>
                <button type="submit" 
                    class="w-full py-4 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 font-bold hover:brightness-110 active:scale-[0.99] transition shadow-lg shadow-amber-500/20">
                    Consultar Saldo Disponible
                </button>
            </form>

            <div class="mt-8 pt-6 border-t border-slate-700/60 text-center">
                <p class="text-xs text-slate-400">Pases rápidos de prueba:</p>
                <div class="flex justify-center gap-2 mt-2">
                    <a href="/saldo/PASAPORTE-001" class="text-xs bg-slate-700 hover:bg-slate-600 px-2.5 py-1 rounded-lg text-amber-300 font-mono">001</a>
                    <a href="/saldo/PASAPORTE-002" class="text-xs bg-slate-700 hover:bg-slate-600 px-2.5 py-1 rounded-lg text-amber-300 font-mono">002</a>
                    <a href="/saldo/PASAPORTE-003" class="text-xs bg-slate-700 hover:bg-slate-600 px-2.5 py-1 rounded-lg text-amber-300 font-mono">003</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/buscar")
def buscar_saldo(code: str = Form(...)):
    clean_code = code.strip().upper()
    return RedirectResponse(url=f"/saldo/{clean_code}", status_code=303)

@app.get("/saldo/{customer_code}", response_class=HTMLResponse)
def ver_saldo(customer_code: str):
    data = get_customer_balance(customer_code.upper())
    if not data:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>No Encontrado</title><script src="https://cdn.tailwindcss.com"></script></head>
        <body class="bg-slate-900 text-white min-h-screen flex items-center justify-center p-4">
            <div class="max-w-md w-full bg-slate-800 p-8 rounded-3xl text-center border border-slate-700">
                <div class="text-4xl mb-4">🔍</div>
                <h2 class="text-xl font-bold mb-2">Pasaporte no encontrado</h2>
                <p class="text-slate-400 text-sm mb-6">El código <b>{customer_code}</b> no está registrado en el sistema.</p>
                <a href="/consulta" class="inline-block px-6 py-2.5 bg-amber-500 text-slate-950 font-bold rounded-xl text-sm">Intentar de nuevo</a>
            </div>
        </body>
        </html>
        """, status_code=404)

    history_rows = ""
    for tx in data["history"]:
        is_recarga = tx["tx_type"] == "RECARGA"
        color = "text-emerald-400" if is_recarga else "text-rose-400"
        sign = "+" if is_recarga else "-"
        date_str = tx["created_at"][:16].replace("T", " ")
        history_rows += f"""
        <div class="flex items-center justify-between py-2.5 border-b border-slate-700/50 last:border-0 text-sm">
            <div>
                <p class="font-medium text-slate-200">{tx['description'] or tx['tx_type']}</p>
                <p class="text-xs text-slate-500">{date_str}</p>
            </div>
            <div class="font-mono font-bold {color}">
                {sign}${tx['amount']:.2f}
            </div>
        </div>
        """

    if not history_rows:
        history_rows = '<p class="text-xs text-slate-500 text-center py-4">Aún no hay movimientos registrados.</p>'

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mi Saldo · {data['name']}</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen p-4 flex justify-center items-start pt-6 sm:pt-12 font-sans">
        <div class="max-w-md w-full space-y-4">
            
            <!-- HEADER -->
            <div class="flex items-center justify-between px-2">
                <a href="/consulta" class="text-xs text-slate-400 hover:text-white transition flex items-center gap-1">
                    ← Volver
                </a>
                <span class="text-xs font-mono uppercase bg-amber-500/10 text-amber-400 border border-amber-500/30 px-2.5 py-0.5 rounded-full font-bold">
                    Pasaporte Activo
                </span>
            </div>

            <!-- CARD PRINCIPAL -->
            <div class="rounded-3xl p-6 bg-gradient-to-br from-amber-600 via-amber-700 to-amber-900 shadow-2xl relative overflow-hidden border border-amber-500/40 text-slate-950">
                <div class="absolute -right-6 -bottom-6 text-9xl opacity-10 select-none">☕</div>
                
                <div class="flex justify-between items-start mb-6">
                    <div>
                        <p class="text-xs uppercase tracking-widest font-bold text-amber-200">Pasaporte Primavera</p>
                        <h2 class="text-lg font-bold text-white mt-0.5">{data['name']}</h2>
                    </div>
                    <span class="font-mono text-xs font-bold bg-black/20 text-white px-2 py-1 rounded-lg backdrop-blur">
                        {data['code']}
                    </span>
                </div>

                <div class="mt-4">
                    <p class="text-xs text-amber-200 font-medium">Saldo Disponible</p>
                    <div class="text-4xl font-extrabold text-white font-mono tracking-tight mt-1">
                        ${data['balance']:.2f} <span class="text-sm font-normal text-amber-200">MXN</span>
                    </div>
                </div>

                <div class="mt-6 pt-4 border-t border-amber-500/30 flex justify-between items-center text-xs text-amber-100">
                    <div>
                        <span class="block text-amber-300 font-semibold">Puntos Recompensa</span>
                        <span class="text-base font-bold text-white font-mono">{data['points']:.1f} pts</span>
                    </div>
                    <div class="text-right">
                        <span class="block text-amber-300 font-semibold">Total Recargas</span>
                        <span class="font-mono text-white">${data['total_recargas']:.2f}</span>
                    </div>
                </div>
            </div>

            <!-- SIMULADOR RÁPIDO DE MOVIMIENTO (Para pruebas en vivo) -->
            <div class="bg-slate-900 rounded-2xl p-4 border border-slate-800">
                <p class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 text-center">Acciones de Prueba en Vivo</p>
                <div class="grid grid-cols-2 gap-2">
                    <form action="/api/v1/simular-recarga" method="POST">
                        <input type="hidden" name="customer_code" value="{data['code']}">
                        <input type="hidden" name="amount" value="100.0">
                        <button type="submit" class="w-full py-2 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded-xl text-xs font-bold transition">
                            + Recargar $100
                        </button>
                    </form>
                    <form action="/api/v1/simular-consumo" method="POST">
                        <input type="hidden" name="customer_code" value="{data['code']}">
                        <input type="hidden" name="amount" value="45.0">
                        <button type="submit" class="w-full py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 rounded-xl text-xs font-bold transition">
                            - Café $45
                        </button>
                    </form>
                </div>
            </div>

            <!-- HISTORIAL DE MOVIMIENTOS -->
            <div class="bg-slate-900 rounded-3xl p-6 border border-slate-800 shadow-lg">
                <h3 class="text-sm font-bold text-white mb-4 flex items-center justify-between">
                    <span>Últimos Movimientos</span>
                    <span class="text-xs font-normal text-slate-400">Ledger FIFO</span>
                </h3>
                <div class="space-y-1">
                    {history_rows}
                </div>
            </div>

            <p class="text-center text-[11px] text-slate-500">
                Pasaporte Primavera · Sistema NIF D-1 / IFRS 15
            </p>
        </div>
    </body>
    </html>
    """

# -----------------
# API REST (JSON)
# -----------------

@app.get("/api/v1/balance/{customer_code}")
def api_get_balance(customer_code: str):
    res = get_customer_balance(customer_code.upper())
    if not res:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return res

@app.post("/api/v1/transaction")
def api_create_transaction(tx: TransactionCreate):
    cust = get_customer(tx.customer_code.upper())
    if not cust:
        raise HTTPException(status_code=404, detail="Cliente no registrado")
    
    updated = record_transaction(
        customer_code=tx.customer_code.upper(),
        tx_type=tx.tx_type,
        amount=tx.amount,
        payment_method=tx.payment_method,
        receipt_id=tx.receipt_id,
        description=tx.description
    )
    return {"status": "success", "data": updated}

# Endpoints auxiliares para simulación directa desde la interfaz
@app.post("/api/v1/simular-recarga")
def simular_recarga(customer_code: str = Form(...), amount: float = Form(...)):
    record_transaction(
        customer_code=customer_code,
        tx_type="RECARGA",
        amount=amount,
        payment_method="Efectivo en Caja",
        description="Recarga Simulada"
    )
    return RedirectResponse(url=f"/saldo/{customer_code}", status_code=303)

@app.post("/api/v1/simular-consumo")
def simular_consumo(customer_code: str = Form(...), amount: float = Form(...)):
    record_transaction(
        customer_code=customer_code,
        tx_type="CONSUMO",
        amount=amount,
        payment_method="Monedero Pasaporte",
        description="Consumo Café Americano"
    )
    return RedirectResponse(url=f"/saldo/{customer_code}", status_code=303)

# Webhook para Loyverse POS
@app.post("/api/v1/loyverse/webhook")
async def loyverse_webhook(request: Request):
    payload = await request.json()
    receipt = payload.get("receipt", payload)
    result = loyverse_client.process_webhook_receipt(receipt)
    return {"status": "received", "result": result}
