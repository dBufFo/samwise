# ⛵ Samwise — Backend & API de la Comunidad Argos

Backend en Python (FastAPI + SQLite) para el sistema de **Monedero Prepago, Fidelización por Sellos y Reconocimiento de Breakage (NIF D-1 / IFRS 15)** para la **Comunidad Argos** (Cafetería & Espacio Cultural en Cuernavaca), integrado con **Loyverse POS** y pases digitales de **Google Wallet / Apple Wallet**.

---

## 🏛️ Conceptos y Branding
* **Proyecto Técnico:** `samwise`
* **Comunidad:** `Argos` (o `Comunidad Argos`)
* **Identificador de Miembro:** `Argonauta 01`, `Argonauta 02`, `Argonauta 03`, etc.
* **Mecánica de Sellos:** Acumulación del 8% sobre el gasto en consumo (no sobre recargas). 6 sellos = 1 café de cortesía.

---

## 🚀 Despliegue en la Nube (Render.com)

1. Crear un repositorio en GitHub llamado `samwise`.
2. En Render.com: **New +** > **Web Service** > Conectar `samwise`.
3. Render detectará automáticamente `render.yaml`:
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Tu URL en la nube quedará lista: `https://samwise-backend.onrender.com`.

---

## 💻 Ejecución Local

```bash
cd /Users/macbook/samwise
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

* Consultar credencial: `http://localhost:8000/consulta`
* Ver Argonauta 01: `http://localhost:8000/saldo/Argonauta 01`
* Documentación Swagger: `http://localhost:8000/docs`
