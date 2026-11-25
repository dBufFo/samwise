import os
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
from database import init_db, get_member_balance, record_transaction, get_member, normalize_code
from loyverse_sync import LoyverseClient

app = FastAPI(title="Samwise API — Comunidad Argos", version="2.0.0")

@app.on_event("startup")
def startup():
    init_db()

LOYVERSE_TOKEN = os.getenv("LOYVERSE_TOKEN", "")
loyverse_client = LoyverseClient(LOYVERSE_TOKEN)

class TransactionCreate(BaseModel):
    member_code: str
    tx_type: str # 'RECARGA', 'CONSUMO', 'CANJE_SELLOS', 'BREAKAGE'
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
        <title>Comunidad Argos | Consulta de Saldo</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-slate-900 rounded-3xl p-8 border border-slate-800 shadow-2xl">
            <div class="text-center mb-8">
                <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-sky-500/10 text-sky-400 mb-4 text-3xl border border-sky-500/20">
                    🏛️
                </div>
                <h1 class="text-2xl font-bold tracking-tight text-white">Comunidad Argos</h1>
                <p class="text-sm text-slate-400 mt-1">Cafetería & Espacio Cultural · Samwise</p>
            </div>

            <form action="/buscar" method="POST" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                        Identificador de Argonauta
                    </label>
                    <input type="text" name="code" placeholder="Ej: Argonauta 01 o 01" required
                        class="w-full px-4 py-3.5 rounded-xl bg-slate-950 border border-slate-700 text-white placeholder-slate-600 focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400 text-center uppercase tracking-widest font-mono text-lg font-bold">
                </div>
                <button type="submit" 
                    class="w-full py-4 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 text-white font-bold hover:brightness-110 active:scale-[0.99] transition shadow-lg shadow-sky-500/20">
                    Consultar Credencial
                </button>
            </form>

            <div class="mt-8 pt-6 border-t border-slate-800 text-center">
                <p class="text-xs text-slate-400">Argonautas de prueba:</p>
                <div class="flex justify-center gap-2 mt-2">
                    <a href="/saldo/Argonauta 01" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg text-sky-300 font-mono">Argonauta 01</a>
                    <a href="/saldo/Argonauta 02" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg text-sky-300 font-mono">Argonauta 02</a>
                    <a href="/saldo/Argonauta 03" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg text-sky-300 font-mono">Argonauta 03</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/buscar")
def buscar_saldo(code: str = Form(...)):
    norm = normalize_code(code)
    return RedirectResponse(url=f"/saldo/{norm}", status_code=303)

@app.get("/saldo/{member_code}", response_class=HTMLResponse)
def ver_saldo(member_code: str):
    data = get_member_balance(member_code)
    if not data:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html lang="es"><head><meta charset="UTF-8"><title>No Encontrado</title><script src="https://cdn.tailwindcss.com"></script></head>
        <body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-4">
            <div class="max-w-md w-full bg-slate-900 p-8 rounded-3xl text-center border border-slate-800">
                <div class="text-4xl mb-4">🔍</div>
                <h2 class="text-xl font-bold mb-2">Argonauta no encontrado</h2>
                <p class="text-slate-400 text-sm mb-6">El código <b>{member_code}</b> no está registrado en Argos.</p>
                <a href="/consulta" class="inline-block px-6 py-2.5 bg-sky-500 text-white font-bold rounded-xl text-sm">Volver</a>
            </div>
        </body></html>
        """, status_code=404)

    # History list
    history_rows = ""
    for tx in data["history"]:
        is_pos = tx["tx_type"] in ["RECARGA"]
        color = "text-emerald-400" if is_pos else "text-rose-400"
        sign = "+" if is_pos else "-"
        date_str = tx["created_at"][:16].replace("T", " ")
        history_rows += f"""
        <div class="flex items-center justify-between py-2.5 border-b border-slate-800 last:border-0 text-sm">
            <div>
                <p class="font-medium text-slate-200">{tx['description'] or tx['tx_type']}</p>
                <p class="text-xs text-slate-500">{date_str}</p>
            </div>
            <div class="text-right">
                <div class="font-mono font-bold {color}">{sign}${tx['amount']:.2f}</div>
                {f'<div class="text-[10px] text-amber-400 font-mono">+{tx["stamps_delta"]} sellos</div>' if tx["stamps_delta"] > 0 else ''}
            </div>
        </div>
        """
    if not history_rows:
        history_rows = '<p class="text-xs text-slate-500 text-center py-4">Aún no hay movimientos registrados.</p>'

    # Rewards catalog cards
    rewards_cards = ""
    for rw in data["rewards"]:
        can_redeem = data["stamps"] >= rw["stamps_cost"]
        btn_class = "bg-amber-500 hover:bg-amber-400 text-slate-950" if can_redeem else "bg-slate-800 text-slate-600 cursor-not-allowed"
        rewards_cards += f"""
        <div class="p-3 bg-slate-950 rounded-2xl border border-slate-800 flex items-center justify-between">
            <div>
                <p class="text-xs font-bold text-white">{rw['name']}</p>
                <p class="text-[11px] text-amber-400 font-mono font-semibold">{rw['stamps_cost']} sellos</p>
            </div>
            <form action="/api/v1/canjear-premio" method="POST">
                <input type="hidden" name="member_code" value="{data['code']}">
                <input type="hidden" name="reward_name" value="{rw['name']}">
                <input type="hidden" name="stamps_cost" value="{rw['stamps_cost']}">
                <button type="submit" {'disabled' if not can_redeem else ''}
                    class="px-3 py-1.5 rounded-xl text-xs font-bold transition {btn_class}">
                    Canjear
                </button>
            </form>
        </div>
        """

    disc_pct = int(data["discount_rate"] * 100)

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{data['code']} · Comunidad Argos</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen p-4 flex justify-center items-start pt-6 sm:pt-10 font-sans">
        <div class="max-w-md w-full space-y-4">
            
            <!-- HEADER -->
            <div class="flex items-center justify-between px-2">
                <a href="/consulta" class="text-xs text-slate-400 hover:text-white transition flex items-center gap-1">
                    ← Volver
                </a>
                <span class="text-xs font-mono uppercase bg-sky-500/10 text-sky-400 border border-sky-500/30 px-3 py-0.5 rounded-full font-bold">
                    Comunidad Argos
                </span>
            </div>

            <!-- CARD PRINCIPAL: NAVEGANTE ARGONAUTA -->
            <div class="rounded-3xl p-6 bg-gradient-to-br from-slate-900 via-sky-950 to-blue-950 shadow-2xl relative overflow-hidden border border-sky-500/30 text-white">
                <div class="absolute -right-4 -bottom-4 text-9xl opacity-5 select-none font-serif">⛵</div>
                
                <div class="flex justify-between items-start mb-6">
                    <div>
                        <p class="text-[11px] uppercase tracking-widest font-bold text-sky-400">Credencial Oficial</p>
                        <h2 class="text-xl font-extrabold text-white mt-0.5">{data['code']}</h2>
                        <p class="text-xs text-slate-300 font-medium">{data['name']}</p>
                    </div>
                    <span class="text-xs font-semibold bg-sky-400/20 text-sky-300 border border-sky-400/30 px-2.5 py-1 rounded-xl">
                        {data['affiliation_type']} {f'(-{disc_pct}%)' if disc_pct > 0 else ''}
                    </span>
                </div>

                <!-- SALDO CASH -->
                <div class="mt-4 flex justify-between items-end">
                    <div>
                        <p class="text-xs text-slate-400 font-medium">Saldo Prepago (Cash)</p>
                        <div class="text-3xl font-extrabold text-white font-mono tracking-tight mt-0.5">
                            ${data['cash_balance']:.2f} <span class="text-xs font-normal text-sky-400">MXN</span>
                        </div>
                    </div>
                    <!-- SELLOS -->
                    <div class="text-right">
                        <p class="text-xs text-slate-400 font-medium">Sellos Acumulados</p>
                        <div class="text-3xl font-extrabold text-amber-400 font-mono tracking-tight mt-0.5">
                            {data['stamps']:.0f} <span class="text-xs font-normal text-amber-200">🏷️</span>
                        </div>
                    </div>
                </div>

                <div class="mt-5 pt-3 border-t border-slate-800/80 flex justify-between items-center text-[11px] text-slate-400">
                    <span>Mecánica: 8% en consumo</span>
                    <span>6 sellos = 1 Café gratis</span>
                </div>
            </div>

            <!-- SIMULADOR OPERATIVO EN CAJA -->
            <div class="bg-slate-900 rounded-2xl p-4 border border-slate-800">
                <p class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2.5 text-center">Acciones Rápidas de Operador</p>
                <div class="grid grid-cols-2 gap-2">
                    <form action="/api/v1/simular-recarga" method="POST">
                        <input type="hidden" name="member_code" value="{data['code']}">
                        <input type="hidden" name="amount" value="100.0">
                        <button type="submit" class="w-full py-2.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded-xl text-xs font-bold transition">
                            + Recargar $100 Cash
                        </button>
                    </form>
                    <form action="/api/v1/simular-consumo" method="POST">
                        <input type="hidden" name="member_code" value="{data['code']}">
                        <input type="hidden" name="amount" value="50.0">
                        <button type="submit" class="w-full py-2.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 rounded-xl text-xs font-bold transition">
                            - Consumo $50 (Suma sellos)
                        </button>
                    </form>
                </div>
            </div>

            <!-- GALERÍA DE RECOMPENSAS POR SELLOS -->
            <div class="bg-slate-900 rounded-3xl p-5 border border-slate-800 shadow-lg space-y-3">
                <div class="flex items-center justify-between">
                    <h3 class="text-sm font-bold text-white flex items-center gap-1.5">
                        <span>🎁 Catálogo de Premios</span>
                    </h3>
                    <span class="text-xs text-amber-400 font-mono font-semibold">Tus sellos: {data['stamps']:.0f}</span>
                </div>
                <div class="space-y-2">
                    {rewards_cards}
                </div>
            </div>

            <!-- HISTORIAL -->
            <div class="bg-slate-900 rounded-3xl p-5 border border-slate-800 shadow-lg">
                <h3 class="text-sm font-bold text-white mb-3 flex items-center justify-between">
                    <span>Últimos Movimientos</span>
                    <span class="text-xs text-slate-500">Samwise Ledger</span>
                </h3>
                <div class="space-y-1">
                    {history_rows}
                </div>
            </div>

            <p class="text-center text-[11px] text-slate-500">
                Samwise Engine · Comunidad Argos · Cuernavaca
            </p>
        </div>
    </body>
    </html>
    """

# -----------------
# API REST (JSON)
# -----------------

@app.get("/api/v1/balance/{member_code}")
def api_get_balance(member_code: str):
    res = get_member_balance(member_code)
    if not res:
        raise HTTPException(status_code=404, detail="Argonauta no encontrado")
    return res

@app.post("/api/v1/transaction")
def api_create_transaction(tx: TransactionCreate):
    m = get_member(tx.member_code)
    if not m:
        raise HTTPException(status_code=404, detail="Argonauta no registrado")
    
    updated = record_transaction(
        member_code=tx.member_code,
        tx_type=tx.tx_type,
        amount=tx.amount,
        payment_method=tx.payment_method,
        receipt_id=tx.receipt_id,
        description=tx.description
    )
    return {"status": "success", "data": updated}

@app.post("/api/v1/simular-recarga")
def simular_recarga(member_code: str = Form(...), amount: float = Form(...)):
    record_transaction(
        member_code=member_code,
        tx_type="RECARGA",
        amount=amount,
        payment_method="Efectivo en Barra",
        description="Recarga Prepago Cash"
    )
    return RedirectResponse(url=f"/saldo/{member_code}", status_code=303)

@app.post("/api/v1/simular-consumo")
def simular_consumo(member_code: str = Form(...), amount: float = Form(...)):
    record_transaction(
        member_code=member_code,
        tx_type="CONSUMO",
        amount=amount,
        payment_method="Monedero Argonauta",
        description="Consumo en Cafetería"
    )
    return RedirectResponse(url=f"/saldo/{member_code}", status_code=303)

@app.post("/api/v1/canjear-premio")
def canjear_premio(member_code: str = Form(...), reward_name: str = Form(...), stamps_cost: float = Form(...)):
    data = get_member_balance(member_code)
    if not data or data["stamps"] < stamps_cost:
        raise HTTPException(status_code=400, detail="Sellos insuficientes")
        
    record_transaction(
        member_code=member_code,
        tx_type="CANJE_SELLOS",
        amount=stamps_cost,
        payment_method="Sellos Argos",
        description=f"¡Canjeaste: {reward_name}!"
    )
    return RedirectResponse(url=f"/saldo/{member_code}", status_code=303)
