# DOCUMENTO TÉCNICO: JOB MONITOR v2.0
## Arquitectura de Scraping + Análisis con OpenAI

---

## DIAGRAMA DE FLUJO - EXTRACCIÓN DE VACANTES (RESUMIDO)

```
🌐 URL Carrera (entrada)
       ↓
📡 SCRAPING (httpx/Playwright)
       ↓
📄 raw_text (HTML limpio)
       ↓
🔐 MD5 Hash (detección de cambios)
       ├─→ Sin cambios → ⏭️ SKIP
       └─→ Con cambios ↓
             ✅ Procesar
               ↓
            📄 html_to_json (BeautifulSoup)
               ↓
            📦 JSON DOM (estructura limpia)
               ↓
            🤖 OpenAI gpt-4o-mini
               ↓
            💬 PROMPT: "Extrae vacantes TECH"
              - title
              - description
              - requirements
              - salary
              - location
               ↓
            ✅ JSON Array (vacantes extraídas)
               ↓
            💾 vacantes.csv (guardar resultados)
               ↓
            📸 snapshots.csv (guardar hash)
               ↓
            ✅ RESULTADO: N vacantes extraídas
```

---

## 1. RESUMEN EJECUTIVO

**Job Monitor v2.0** es un sistema de scraping inteligente que monitorea portales de carreras de empresas tech, extrae vacantes de empleo y las estructura automáticamente usando inteligencia artificial.

| Aspecto | Valor |
|---------|-------|
| **Lenguaje** | Python 3.11+ |
| **Paradigma** | Async/Await concurrente |
| **Almacenamiento** | CSV (snapshots.csv + vacantes.csv) |
| **IA** | OpenAI gpt-4o-mini |
| **Tiempo x 7 URLs** | ~60 seg (primera ejecución) |
| **Costo x 7 URLs** | ~$0.035 (OpenAI) |

---

## 2. STACK TECNOLÓGICO

### 2.1 Dependencias Principales

```
httpx[http2]>=0.27.0          # Cliente HTTP asíncrono (scraping estático)
beautifulsoup4>=4.12.0        # Parser HTML para DOM
lxml>=4.9.0                   # Engine de parsing (rápido)
playwright>=1.40.0            # Navegador headless para JavaScript (scraping dinámico)
openai>=1.3.0                 # Cliente OpenAI official
python-dotenv>=1.0.0          # Gestión de variables de entorno
```

### 2.2 Diagrama de Dependencias

```
main.py (orquestador)
├── scraper.detector         → httpx (detecta tipo página)
├── scraper.static_scraper   → httpx, BeautifulSoup4
├── scraper.dynamic_scraper  → Playwright, Chromium
├── storage.csv_loader       → CSV built-in
├── storage.snapshots        → CSV built-in
├── storage.vacantes         → CSV built-in
├── utils.html_to_json       → BeautifulSoup4
├── utils.hasher             → hashlib built-in
├── utils.logger             → logging built-in
└── ai.analyzer              → OpenAI, asyncio
```

---

## 3. MAPEO DE LIBRERÍAS POR MÓDULO

### 3.1 scraper/static_scraper.py

```
Librería    | Propósito
──────────────────────────────────────────
httpx       | Cliente HTTP asíncrono
            | ✓ Soporta http/2
            | ✓ Timeouts configurables (25 seg)
            | ✓ Headers customizados (User-Agent)
            
BeautifulSoup4 | Parser HTML
            | ✓ Extrae texto visible
            | ✓ Elimina <script>, <style>
            | ✓ Get_text() limpio
```

**Flujo:**
```python
URL → httpx.get(url, timeout=25) → response.text
    → BeautifulSoup(html, 'lxml')
    → remove_tags([script, style, nav...])
    → .get_text(separator='\n')
    → raw_text: str
```

**Performance:** 2-3 seg por página

---

### 3.2 scraper/dynamic_scraper.py

```
Librería    | Propósito
──────────────────────────────────────────
playwright  | Navegador headless automatizado
            | ✓ Carga JavaScript completo
            | ✓ Espera networkidle (sin requests)
            | ✓ User-Agent real
            | ✓ Viewport 1280x800
            
chromium    | Engine de navegación
            | ✓ Headless (sin interfaz)
            | ✓ Sandbox seguro
```

**Flujo:**
```python
URL → browser.new_page()
    → page.goto(url, wait_until='networkidle', timeout=40s)
    → page.wait_for_timeout(3s)  # extra para SPAs lentas
    → page.inner_text('body')
    → raw_text: str
```

**Performance:** 40-50 seg por página (incluye renders JS)

---

### 3.3 utils/html_to_json.py

```
Librería    | Propósito
──────────────────────────────────────────
BeautifulSoup4 | Conversión recursiva HTML → JSON
            | ✓ Preserva estructura jerárquica
            | ✓ Extrae class/id attributes
            | ✓ Limita profundidad (max 10 niveles)
            | ✓ Max 8,000 caracteres JSON
```

**Entrada (HTML crude):**
```html
<div class="careers" id="jobs">
    <h2>Senior Developer</h2>
    <p>React, Node.js, 5+ años</p>
</div>
```

**Salida (JSON DOM):**
```json
{
    "tag": "div",
    "attributes": {"class": "careers", "id": "jobs"},
    "children": [
        {
            "tag": "h2",
            "text": "Senior Developer"
        },
        {
            "tag": "p",
            "text": "React, Node.js, 5+ años"
        }
    ]
}
```

**Propósito:** Estructura limpia y contextuada para OpenAI (reduce tokens)

---

### 3.4 ai/analyzer.py

```
Librería    | Propósito
──────────────────────────────────────────
openai      | Cliente oficial de OpenAI
            | ✓ AsyncOpenAI para calls concurrentes
            | ✓ chat.completions.create()
            | ✓ Manejo de errores integrado
            
asyncio     | Concurrencia Python
            | ✓ await de operaciones I/O
            | ✓ Gestión de event loop
            
json        | Parseo de responses
            | ✓ Parse JSON de OpenAI
            | ✓ Validación de estructura
```

---

## 4. EL PROMPT DE OPENAI (NÚCLEO DE LA IA)

### 4.1 Estructura Completa del Prompt

```python
prompt = f"""Del siguiente JSON (estructura DOM de HTML de una página de carreras/empleos), 
extrae TODAS las vacantes o PUESTOS DE TRABAJO disponibles que sean de TECH/SOFTWARE/DESARROLLO/INGENIERIA DE SISTEMAS/INFRAESTRUCTURA/DEVOPS.

Para cada vacante encontrada, extrae:
- title: Título del puesto (ej: "Senior Developer", "Full-stack Engineer")
- description: Descripción breve del trabajo (máximo 200 caracteres)
- requirements: Requisitos técnicos principales separados por comas
- salary: Rango salarial o moneda (si está disponible, si no disponible dejar vacío)
- location: Ubicación geográfica (país, ciudad, remoto, etc.)

Retorna un JSON array válido con SOLO objeto vacío [] si no hay vacantes:
[
  {{"title": "...", "description": "...", "requirements": "...", "salary": "...", "location": "..."}},
  ...
]

IMPORTANTE:
- Si NO HAY VACANTES o TODAS son de áreas NO TECH (HR, Sales, Marketing, etc.), retorna: []
- SOLO vacantes relacionadas con tech/dev/software/engineering
- Si el JSON no contiene texto claro de vacantes, retorna: []

DOM JSON:
{json_str}
"""
```

### 4.2 Parámetros OpenAI

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| **model** | gpt-4o-mini | Rápido + económico (~$0.00000150/token input) |
| **temperature** | 0.3 | Bajo = respuestas consistentes (vs. creative) |
| **max_tokens** | 2500 | ~40 vacantes máximo por página |

### 4.3 Flujo de Extracción

```
1. JSON DOM (8KB max) → OpenAI
2. OpenAI procesa con instrucción "extrae TODAS las vacantes TECH"
3. temperature=0.3 → OpenAI responde conservadoramente
4. Response limitada a 2500 tokens → ~40-50 vacantes
5. Parseo JSON → Validación de estructura
6. Limpieza (trunca campos > límite)
7. Guardar en vacantes.csv
```

### 4.4 Entrada Real vs. Salida

**Entrada a OpenAI:**
```json
{
  "tag": "body",
  "children": [
    {
      "tag": "div",
      "attributes": {"class": "job-listing"},
      "text": "Senior Frontend Developer React TypeScript $120k 2+ años SF"
    }
  ]
}
```

**Salida de OpenAI:**
```json
[
  {
    "title": "Senior Frontend Developer",
    "description": "Develop modern web interfaces",
    "requirements": "React, TypeScript, 2+ years",
    "salary": "$120k",
    "location": "San Francisco"
  }
]
```

---

## 5. ALMACENAMIENTO: SISTEMA CSV

### 5.1 snapshots.csv (Control de cambios)

**Propósito:** Detectar si una URL ha cambiado desde la última ejecución

```csv
org_name,careers_url,content_hash,raw_text_snip,last_checked
Figma,https://figma.com/careers,a3f8e2c9d...,Senior Developer Role Available...,2026-04-15T20:25:41
```

**Campos:**
- `org_name`: Nombre de la empresa
- `careers_url`: URL monitorizada
- `content_hash`: MD5 del contenido (detección de cambios)
- `raw_text_snip`: Primeros 500 chars (verificación manual)
- `last_checked`: ISO timestamp

### 5.2 vacantes.csv (Resultados)

**Propósito:** Almacenar todas las vacantes extraídas

```csv
org_name,title,description,requirements,salary,location,source_url,extracted_date
Figma,AI Applied Scientist,Work on AI applications...,AI machine learning data analysis,,$https://figma.com/careers,2026-04-15T20:25:41
```

**Campos:**
- `org_name`: Empresa origen
- `title`: Título del puesto
- `description`: Descripción (max 300 chars)
- `requirements`: Stack técnico (max 200 chars)
- `salary`: Rango salarial o vacío
- `location`: Ubicación o "Remoto"
- `source_url`: URL donde se encontró
- `extracted_date`: Cuándo se extrajo

**Estado actual:** 49 vacantes (Figma: 29, Notion: 14, FedericoValverde: 9)

---

## 6. FLUJO DETALLADO DE EJECUCIÓN

### 6.1 Fase 1: Carga y Detección

```python
organizations = load_organizations('organizations.csv')
# → Lee columns: organization_name, careers_url, tier, scrape_method ...
# → Crea dataclass Organization(name, careers_url, tier, scrape_method)

for org in organizations:
    method = detect_page_type(org.careers_url)
    # → Hace HEAD request a URL
    # → Si tiene JavaScript → 'dynamic'
    # → Si es HTML puro → 'static'
```

### 6.2 Fase 2: Scraping

```python
if method == 'static':
    result = await scrape_static(url)
    # httpx.get() → 2-3 seg
else:
    result = await scrape_dynamic(url)
    # playwright → 40-50 seg

raw_text = result['raw_text']  # String sin HTML tags
```

### 6.3 Fase 3: Detección de Cambios

```python
new_hash = compute_hash(raw_text)  # MD5(raw_text)
last_hash = get_last_hash(org.name)  # Lee desde snapshots.csv

if last_hash == new_hash:
    return 'SKIP'  # No procesar, ahorrar tokens OpenAI
else:
    continue...
```

### 6.4 Fase 4: Conversión HTML → JSON

```python
json_dom = html_to_json_dom(raw_text)
# BeautifulSoup recursiva → JSON
# Limita: profundidad=10, tamaño=8KB

json_str = json.dumps(json_dom)
if len(json_str) > 8000:
    json_str = json_str[:8000] + "...truncated"
```

### 6.5 Fase 5: Análisis OpenAI

```python
response = await client.chat.completions.create(
    model='gpt-4o-mini',
    messages=[{"role": "user", "content": prompt}],
    temperature=0.3,
    max_tokens=2500
)

content = response.choices[0].message.content
# Parsear JSON → validar → limpiar campos
vacancies = json.loads(content)
```

### 6.6 Fase 6: Persistencia

```python
for vacancy in vacancies:
    save_vacancy(org.name, title, desc, req, salary, loc, url)
    # → Append a vacantes.csv

save_snapshot(org.name, url, new_hash, raw_text)
    # → Insert/update en snapshots.csv
```

---

## 7. CONCEPTOS TÉCNICOS EXPLICADOS

### 7.1 Hash y Detección de Cambios

```
¿Por qué MD5?
├─ Rápido: 1 millisegundo
├─ Determinístico: mismo texto = mismo hash
├─ Pequeño: 32 caracteres hexadecimales
└─ Suficiente para este caso (no es criptografía)

Uso:
  Hash(Página actual) == Hash(Snapshot anterior)
  → No cambió → Skip OpenAI (ahorrar $)
  → Cambió     → Procesar → Nueva extracción
```

### 7.2 Async/Await en Python

```python
# Sin async (secuencial):
for org in orgs:
    html = scrape(org)      # Espera 45 seg
    json = convert(html)    # Espera 1 seg
    vacancies = ai(json)    # Espera 5 seg
    # Total: 51 seg POR CADA ORG

# Con async (actual, pero no paralelo):
await process_org(org)  # Uno a la vez
# Total: 51 seg × N orgs

# Con asyncio.gather() (MEJORA PENDIENTE):
tasks = [process_org(org) for org in orgs]
results = await asyncio.gather(*tasks, return_exceptions=True)
# Total: ~51 seg (TODOS EN PARALELO)
```

### 7.3 Temperature en OpenAI

```
temperature=0.0 → Determinístico
  └─ Siempre responde igual
  └─ Mejor para extracción (consistencia)

temperature=0.3 → ACTUAL (nuestro caso)
  └─ Poco creativo, muy consistente
  └─ Ideal para parsing estructurado

temperature=1.0 → Creativo
  └─ Más variado
  └─ Peor para extracción (inconsistente)
```

### 7.4 Max Tokens

```
max_tokens=2500 en nuestro caso
├─ Prompt: ~150 tokens (instrucciones)
├─ DOM JSON: ~2,000 tokens (contenido)
├─ Output: ~2,500 tokens (respuesta)
└─ Total: ~2,500-5,000 tokens por URL

Estimación de vacantes:
  ~100 tokens por vacante
  2,500 max_tokens ÷ 100 = ~25 vacantes máximo
  (en práctica: 30-40 por página)

Costo:
  $0.00000150/token input × 2,500 tokens = $0.00375 por URL
  7 URLs × $0.00375 = $0.0263 por ejecución semanal
```

### 7.5 Scraping Estático vs. Dinámico

| Aspecto | Estático | Dinámico |
|---------|----------|----------|
| **Librería** | httpx | Playwright |
| **Tiempo** | 2-3 seg | 40-50 seg |
| **CPU** | Bajo | Alto (Chromium) |
| **RAM** | <50MB | ~200MB |
| **Casos** | HTML render-on-load | React, Vue, Angular |
| **Detección** | HEAD request → headers | Análisis de contenido |

---

## 8. ARQUITECTURA ACTUAL vs. ESCALABLE

### 8.1 Limitaciones Actuales

```
Procesamiento: SECUENCIAL
for org in organizations:
    result = await process_org(org)  # Espera uno a uno
    await asyncio.sleep(2)  # Pausa innecesaria

100 URLs × 50 seg = 5,000 seg = 83 minutos ❌
```

### 8.2 Escalado Recomendado (asyncio.gather)

```python
# MEJORA:
max_concurrent = 10  # Máximo 10 simultáneos

semaphore = asyncio.Semaphore(max_concurrent)
async def bounded_process(org):
    async with semaphore:
        return await process_org(org)

tasks = [bounded_process(org) for org in organizations]
results = await asyncio.gather(*tasks, return_exceptions=True)

100 URLs × 50 seg ÷ 10 = 500 seg = 8 minutos ✅
```

**Mejora:** 10× más rápido mismo costo OpenAI

---

## 9. TABLA DE VARIABLES Y PARÁMETROS

| Variable | Valor | Ubicación | Función |
|----------|-------|-----------|---------|
| `REQUEST_DELAY` | 2 seg | main.py | Pausa entre orgs (rate limit) |
| `AI_DELAY` | 1 seg | main.py | Pausa entre OpenAI calls |
| `TIMEOUT (httpx)` | 25 seg | static_scraper.py | Límite de conexión HTTP |
| `TIMEOUT (playwright)` | 40 seg | dynamic_scraper.py | Límite de carga JS |
| `WAIT (playwright)` | 3 seg | dynamic_scraper.py | Espera extra para SPAs |
| `MAX_DEPTH (json)` | 10 niveles | html_to_json.py | Límite de recursión |
| `MAX_JSON_SIZE` | 8,000 chars | analyzer.py | Límite para OpenAI |
| `temperature` | 0.3 | analyzer.py | Consistencia vs. creatividad |
| `max_tokens` | 2,500 | analyzer.py | Límite de respuesta OpenAI |
| `model` | gpt-4o-mini | analyzer.py | Modelo económico rápido |

---

## 10. FLUJO DE DATOS (EJEMPLO REAL)

**URL entrada:** `https://www.figma.com/careers/#job-openings`

```
PASO 1: SCRAPING ESTÁTICO
├─ httpx.get(url, timeout=25)
├─ response.status = 200
├─ response.text = <html><body>...</body></html> (45 KB)
└─ raw_text = "Senior Developer React TypeScript..." (2,277 chars)

PASO 2: HASH Y COMPARACIÓN
├─ compute_hash(raw_text) = "a3f8e2c9d123..."
├─ get_last_hash('Figma') = "a3f8e2c9d123..." (había snapshot anterior)
├─ Hashes iguales → ❌ SKIP
└─ Retorna sin procesar OpenAI

EJECUCIÓN POSTERIOR (cuando cambia página):
PASO 1-2: Igual, pero hash diferente
├─ compute_hash(raw_text) = "b4g9f3d0e234..." ← DIFERENTE
├─ get_last_hash('Figma') = "a3f8e2c9d123..."
└─ Hashes desiguales → ✅ PROCESAR

PASO 3: CONVERSIÓN HTML → JSON
├─ html_to_json_dom(raw_text)
├─ BeautifulSoup parse → árbol de tags
├─ Recursión: <body> → <div class="careers"> → <h2> → ...
├─ JSON DOM = {
│   "tag": "body",
│   "children": [{
│     "tag": "div",
│     "attributes": {"class": "careers"},
│     "children": [...]
│   }]
│ }
├─ json.dumps() = 1,847 chars (< 8,000 ✓)
└─ json_str listo para OpenAI

PASO 4: ENVÍO A OPENAI
├─ Prompt construido:
│  "Del siguiente JSON (estructura DOM...)
│   extrae TODAS las vacantes de TECH/SOFTWARE...
│   [campos: title, description, requirements, salary, location]
│   DOM JSON: {json_str}"
├─ Tokens estimados:
│  - Instrucciones: 120 tokens
│  - DOM JSON: 1,847 chars ÷ 4 = ~460 tokens
│  - Total input: ~580 tokens
│  - Output max: 2,500 tokens
├─ API call:
│  response = await client.chat.completions.create(
│    model='gpt-4o-mini',
│    messages=[{"role": "user", "content": prompt}],
│    temperature=0.3,
│    max_tokens=2500
│  )
└─ Latencia: 3-5 seg

PASO 5: PARSEO RESPUESTA
├─ content = response.choices[0].message.content
├─ Limpieza markdown:
│  if content.startswith("```json"): content = content[7:]
│  if content.endswith("```"): content = content[:-3]
├─ JSON parse: vacancies = json.loads(content)
└─ vacancies = [
   {
     "title": "AI Applied Scientist",
     "description": "Work on AI applications...",
     "requirements": "AI, machine learning, data analysis",
     "salary": "",
     "location": ""
   },
   ... (29 vacantes totales de Figma)
  ]

PASO 6: ALMACENAMIENTO
├─ Para cada vacancy en vacancies:
│  save_vacancy(
│    org_name='Figma',
│    title='AI Applied Scientist',
│    description='Work on AI applications...', # truncate a 300 chars
│    requirements='AI, machine learning, data analysis', # 200 chars max
│    salary='', # vacío si no disponible
│    location='', # vacío si no disponible
│    source_url='https://figma.com/careers'
│  )
│  # → INSERT INTO vacantes.csv (append)
│
└─ save_snapshot(
   org_name='Figma',
   careers_url='https://figma.com/careers',
   content_hash='b4g9f3d0e234...',
   raw_text_snip='Senior Developer React TypeScript...' (500 chars)
  )
  # → UPDATE snapshots.csv

PASO 7: RESULTADO
├─ status: "changed" (había cambios)
├─ vacancies: 29
├─ method: "static"
└─ [Log] ✅ 29 vacantes extraídas de Figma

TIEMPO TOTAL: ~10 segundos
├─ Scraping: 3 seg
├─ JSON conversion: 1 seg
├─ OpenAI: 5 seg
└─ Almacenamiento: 1 seg
```

---

## 11. RESUMEN: PALABRAS CLAVE TÉCNICAS

| Término | Explicación |
|---------|------------|
| **Async/Await** | Operaciones no-bloqueantes en Python; permite I/O concurrente |
| **Hash (MD5)** | Firma única de contenido; detecta cambios en páginas |
| **DOM (Document Object Model)** | Árbol de elementos HTML; estructura jerárquica |
| **BeautifulSoup** | Parser HTML → extrae datos de HTML crudo |
| **Playwright** | Navegador automatizado; ejecuta JavaScript |
| **httpx** | Cliente HTTP asíncrono; rápido y moderno |
| **Temperature** | Parámetro OpenAI; controla variabilidad de respuestas |
| **Max Tokens** | Límite de tokens en respuesta OpenAI |
| **Prompt Engineering** | Diseño de instrucciones para IA; crucial para calidad |
| **JSON DOM** | Conversión de HTML a estructura JSON cleanable |
| **Rate Limiting** | Pausa entre requests para no sobrecargar servidores |
| **Headless Browser** | Navegador sin GUI; para automatización |
| **Change Detection** | Algoritmo que identifica si contenido cambió |
| **Snapshot** | Fotografía del estado anterior; base para comparación |
| **ETL (Extract-Transform-Load)** | Patrón: extraer datos, transformar, almacenar |

---

## 12. COSTO Y PERFORMANCE ESTIMADO

### Monitoreo Semanal (7 URLs, cambios variables)

| Escenario | URLs | Tiempo | Costo OpenAI | Estado |
|-----------|------|--------|-------------|--------|
| **A: Sin cambios** | 7 | 21 seg | $0.00 | Actual |
| **B: Todas nuevas** | 7 | 60 seg | $0.05 | 1ª ejecución |
| **C: Mixto 50/50** | 7 | 35 seg | $0.025 | Típico |

### Escala 100 URLs (proyección con paralelismo max 10)

| Escenario | Tiempo | Costo | Mejora |
|-----------|--------|-------|--------|
| Secuencial (actual) | 83 min | $0.50 | baseline |
| Paralelo 10x | 8 min | $0.50 | 10× rápido |

---

**Documento generado:** 15 de abril 2026  
**Versión:** Job Monitor v2.0  
**Estado:** Producción (7 URLs monitorizadas)
