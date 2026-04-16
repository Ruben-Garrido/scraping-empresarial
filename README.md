# Job Monitor v1.0 — CSV Scraper

Monitor automatizado de vacantes tecnológicas — **v1.0 (CSV Scraper)**.

## Estructura del proyecto

```
job-monitor/
├── organizations.csv        ← TU LISTA DE URLs (editar aquí)
├── main.py                  ← Punto de entrada
├── scraper/
│   ├── detector.py          ← Auto-detección static vs dynamic
│   ├── static_scraper.py    ← httpx + BeautifulSoup
│   └── dynamic_scraper.py   ← Playwright (SPAs)
├── storage/
│   ├── csv_loader.py        ← Lee y valida el CSV
│   └── database.py          ← SQLite (jobs.db)
├── utils/
│   ├── logger.py            ← Logger con archivo diario
│   └── hasher.py            ← Hash MD5 para detectar cambios
├── logs/                    ← Creada automáticamente
├── jobs.db                  ← Creada automáticamente
└── requirements.txt
```

---

## Instalación (primera vez)

```powershell
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar entorno
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Instalar browser de Playwright
playwright install chromium
```

---

## Uso

### 1. Editar el CSV con tus URLs

Abre `organizations.csv` y agrega tus organizaciones:

```csv
organization_name,careers_url,tier,scrape_method,hr_contact,notes
"Empresa Tech","https://empresa.com/careers","tier1","auto","rrhh@empresa.com",""
"Startup ABC","https://jobs.lever.co/startupABC","tier1","dynamic","","ATS Lever"
```

| Columna | Valores válidos | Descripción |
|---|---|---|
| `organization_name` | Texto libre | Nombre de la empresa |
| `careers_url` | URL completa | Página de vacantes |
| `tier` | `tier1` | Crawler directo (esta versión) |
| `scrape_method` | `auto` / `static` / `dynamic` | `auto` detecta automáticamente |
| `hr_contact` | Email (opcional) | Contacto de RRHH |
| `notes` | Texto libre | Notas técnicas |

### 2. Ejecutar el monitor

```powershell
# Ejecución normal
python main.py --csv organizations.csv

# Solo procesar tier1
python main.py --csv organizations.csv --tier tier1

# Modo prueba (no guarda en BD)
python main.py --csv organizations.csv --dry-run
```

### 3. Interpretar el output

```
2026-04-15 10:00:01  INFO      📡  Empresa Tech
2026-04-15 10:00:01  INFO           URL : https://empresa.com/careers
2026-04-15 10:00:03  INFO           Tipo detectado → static
2026-04-15 10:00:04  INFO           🆕  Primera ejecución — guardando snapshot base

2026-04-15 10:00:06  INFO      📡  Startup ABC
2026-04-15 10:00:06  INFO           URL : https://jobs.lever.co/startupABC
2026-04-15 10:00:12  INFO           ⏭️  Sin cambios detectados

============================================================
📊  RESUMEN DE EJECUCIÓN
     Total procesadas : 2
     Primera vez      : 1
     Con cambios  🔔  : 0
     Sin cambios      : 1
     Errores      ❌  : 0
============================================================
```

| Icono | Significado |
|---|---|
| 🆕 Primera vez | Primera ejecución, se guarda el snapshot base |
| 🔔 Cambio detectado | El contenido cambió → en v1.1 pasará al IA Scorer |
| ⏭️ Sin cambios | La página no cambió desde el último run |
| ❌ Error | Problema con la URL (rota, timeout, bloqueada) |

---

## Requisitos

- Python 3.11+
- Windows / Linux / macOS

---

## Versiones

| Versión | Estado | Descripción |
|---|---|---|
| **v1.0** | ✅ Actual | Scraping desde CSV |
| v1.1 | Próxima | IA Scoring (GPT-4o-mini) |
| v1.2 | Futura | Matching con ATS |
| v1.3 | Futura | Notificaciones |
