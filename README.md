# ☕ Pasaporte Primavera — Backend & API de Monedero

Backend en Python (FastAPI + SQLite) para el sistema de **Monedero Prepago, Fidelización por Sellos y Reconocimiento de Breakage (NIF D-1 / IFRS 15)** para cafetería de especialidad en Cuernavaca (*Pasaporte Primavera*), integrado con **Loyverse POS** y pases digitales de **Google Wallet / Apple Wallet**.

---

## 🏛️ Arquitectura Híbrida

```
┌─────────────────────────────────┐
│     CLIENTE / GOOGLE WALLET     │
│   (Muestra su QR: PASAPORTE-001)│
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐             (Webhook / API)
│          LOYVERSE POS           │ ───────────────────────────────────────┐
│ - Escanea QR y cobra en barra   │                                        │
│ - Maneja efectivo e inventario  │                                        │
└─────────────────────────────────┘                                        ▼
                                                         ┌────────────────────────────────────┐
                                                         │       TU BACKEND PROPIO (Python)    │
                                                         │ - Base de Datos (Ledger FIFO)      │
                                                         │ - Saldo exacto en $ en tiempo real │
                                                         │ - Catálogo de Premios por Sellos   │
                                                         │ - Reconocimiento de Breakage       │
                                                         │ - Vista Web Móvil para el cliente  │
                                                         └────────────────────────────────────┘
```

---

## 🚀 Despliegue en la Nube (Render.com)

Este repositorio incluye el archivo de configuración `render.yaml` listo para despliegue automático:

1. Crea una cuenta gratuita en [Render.com](https://render.com).
2. Haz clic en **New +** > **Web Service**.
3. Conecta este repositorio de GitHub.
4. Render detectará automáticamente la configuración:
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. *(Opcional)* Agrega la variable de entorno `LOYVERSE_TOKEN` con tu token de Loyverse Back Office.
6. Haz clic en **Deploy Web Service**.

Al terminar, obtendrás tu URL pública segura `https://tu-servicio.onrender.com`.

---

## 💻 Ejecución Local

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/TU_USUARIO/pasaporte-backend.git
   cd pasaporte-backend
   ```
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Iniciar el servidor local:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. Abrir en el navegador:
   * Buscador de saldo: `http://localhost:8000/consulta`
   * Tarjeta del cliente de prueba: `http://localhost:8000/saldo/PASAPORTE-001`
   * Documentación interactiva de la API (Swagger): `http://localhost:8000/docs`

---

## 🔌 Endpoints Principales

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/consulta` | Pantalla web para buscar y consultar saldo |
| `GET` | `/saldo/{code}` | Tarjeta digital interactiva móvil del cliente |
| `GET` | `/api/v1/balance/{code}` | Consulta de saldo y movimientos en formato JSON |
| `POST` | `/api/v1/transaction` | Registro atómico de movimientos en el Ledger FIFO |
| `POST` | `/api/v1/loyverse/webhook` | Receptor en tiempo real de recibos de Loyverse POS |

---

## 👥 Tipos de Afiliación y Bonificadores
* **Regular:** 0% descuento, solo sellos (8%) y cortesía de cumpleaños.
* **Estudiante:** 10% de descuento en consumo, vigencia 1 año renovable.
* **Cliente Especial:** 10% de descuento en consumo, indeterminado.
* **Argonáuta:** 5% descuento en librería y restaurante.
* **Escritor:** 5% descuento en librería y restaurante.
* **Grey Creativa:** 5% descuento (55+ años, comunidad cultural/retiro).

---
*Desarrollado para el Proyecto Integrador Citizen Data Scientist (CDS) — Tecnológico de Monterrey.*
