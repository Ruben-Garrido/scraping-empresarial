# Job Monitor v2.0 — Scraper + OpenAI

Monitor automatizado de vacantes tecnológicas con análisis inteligente.

**Flujo**: Scraping (HTML) → Conversión a JSON → Análisis OpenAI → Extracción de vacantes

---

## 🆕 Cambios en v2.0

✅ **CSV en lugar de SQLite** — Snapshots guardados en `snapshots.csv` (más simple, portátil)  
✅ **Integración OpenAI** — Análisis automático de vacantes con `gpt-4o-mini`  
✅ **Conversión HTML→JSON** — Estructura DOM preserva contexto, reduce tokens  
✅ **Salida de vacantes** — Todos los datos en `vacantes.csv` (título, descripción, requisitos, salario, ubicación)  

---

## Configuración OpenAI

### 1. Crear `.env` en la raíz del proyecto

```bash
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini
RESEND_API_KEY=re_your_resend_api_key
RESEND_SENDER_EMAIL=onboarding@resend.dev
RESEND_RECIPIENT_EMAIL=tu_correo@ejemplo.com
```

### 2. Obtener API Key

1. Ve a https://platform.openai.com/account/api-keys
2. Crea nueva API key
3. Pégala en `.env`

⚠️ **Importante**: `.env` está en `.gitignore` (nunca commitear)

---

## Estructura de carpetas

```
job-monitor/
├── ai/
│   ├── __init__.py
│   └── analyzer.py          ← Integración OpenAI
├── storage/
│   ├── snapshots.py         ← NUEVO: CSV de snapshots
│   └── vacantes.py          ← NUEVO: CSV de vacantes
├── utils/
│   └── html_to_json.py      ← NUEVO: HTML → JSON
├── snapshots.csv            ← Auto-generado
├── vacantes.csv             ← Auto-generado
├── .env                     ← CREAR (tu API key)
└── main.py                  ← REFACTORIZADO
```

---

## Uso

```powershell
# Instalación de deps
pip install -r requirements.txt

# Ejecutar
python main.py --csv organizations.csv

# Con filtro
python main.py --csv organizations.csv --tier tier2

# Dry-run
python main.py --csv organizations.csv --dry-run
```

---

## Resultados

- **snapshots.csv**: Control de cambios
- **vacantes.csv**: Vacantes extraídas (título, descripción, requisitos, salario, ubicación)
- **logs/**: Detalles de ejecución

---

## Modelo OpenAI

- **Modelo**: `gpt-4o-mini` (rápido, económico)
- **Análisis en 2 pasos**:
  1. Identifica div/sección con job listings
  2. Extrae todas las vacantes de tech/dev

---

## Costos

Con 6 empresas (1 vez/semana):
- ~$0.004 por ejecución
- ~$0.20/mes

---

## Nota importante

⚠️ Antes de ejecutar, **asegúrate que `.env` tiene tu `OPENAI_API_KEY`** de lo contrario el programa fallará.
