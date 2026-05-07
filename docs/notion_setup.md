# Setup de Notion

Tres pasos: crear integracion, preparar pagina padre, correr el seed.
Tiempo total: ~10 minutos.

---

## 1. Crear la integracion interna

1. Entra a [https://www.notion.so/profile/integrations](https://www.notion.so/profile/integrations).
2. Click **+ New integration**.
3. Datos:
   - **Name**: `HackIAthon PreAuth`
   - **Associated workspace**: el workspace donde vas a trabajar
   - **Type**: Internal
4. Click **Save**.
5. En la pestana **Configuration**, copia el **Internal Integration Secret**
   (empieza con `ntn_`). Es tu `NOTION_TOKEN`.

---

## 2. Preparar la pagina padre

1. En tu workspace de Notion, crea una pagina nueva. Llamala
   **HackIAthon PreAuth** (o como quieras).
2. Abrela y, en la esquina superior derecha, click el menu **`...`** ->
   **Connections** -> **+ Add connections** -> selecciona la integracion
   `HackIAthon PreAuth` que acabas de crear.

   > **Critico:** si no conectas la integracion a la pagina, la API de Notion
   > devuelve 404 al intentar crear las DBs.

3. Copia el ID de la pagina. Esta en la URL:

   ```
   https://www.notion.so/<workspace>/Mi-Pagina-<PAGE_ID>?v=...
   ```

   Los 32 caracteres antes del `?v=` (o al final si no hay query) son tu
   `NOTION_PARENT_PAGE_ID`. Pueden venir con guiones - se aceptan ambas formas.

---

## 3. Configurar `.env` y correr el seed

1. Copia el ejemplo:

   ```bash
   cp backend/.env.example backend/.env
   ```

2. Edita `backend/.env` y rellena solamente estas dos variables por ahora:

   ```
   NOTION_TOKEN=ntn_TU_TOKEN
   NOTION_PARENT_PAGE_ID=TU_PAGE_ID
   ```

   (`ANTHROPIC_API_KEY` y los `NOTION_DB_*` los rellenamos despues.)

3. Instala dependencias y corre el seed:

   ```bash
   pip install -r backend/requirements.txt
   python seed/populate_notion.py
   ```

4. El script imprime al final algo como:

   ```
   ============================================================
   LISTO. Pega esto en backend/.env y guarda:
   ============================================================
   NOTION_DB_ASEGURADOS=abcd1234...
   NOTION_DB_POLIZAS=efgh5678...
   NOTION_DB_PLANES=...
   NOTION_DB_COBERTURAS=...
   NOTION_DB_INFORMES=...
   NOTION_DB_DECISIONES=...
   ============================================================
   ```

   Pega esos 6 valores en `backend/.env` reemplazando las lineas vacias.

---

## 4. Verificar en Notion

Abre tu pagina padre en Notion. Deberias ver 6 sub-pages con icono de DB:

- **Planes** (3 filas: Basico, Estandar, Premium)
- **Asegurados** (3 filas: Juan Perez, Maria Gonzalez, Carlos Bermeo)
- **Polizas** (3 filas: POL-001, POL-002, POL-003)
- **Coberturas** (8 filas: combinaciones plan x procedimiento)
- **Informes_Medicos** (3 filas: INF-001, INF-002, INF-003)
- **Decisiones** (vacia, la llena el agente)

---

## Si algo falla

- **`Could not find page with ID`**: olvidaste conectar la integracion a la
  pagina padre. Repite el paso 2.
- **`Validation error: title is required`**: estas usando una version vieja
  de `notion-client`. Asegura `notion-client>=2.2.1`.
- **DBs creadas a medias**: el script no es idempotente. Borra (archiva) la
  pagina padre, crea una nueva, conectala con la integracion, y vuelve a
  correr. No olvides actualizar `NOTION_PARENT_PAGE_ID`.
- **Quieres re-sembrar con datos frescos**: borra (archiva) las 6 DBs en
  Notion, vacia los `NOTION_DB_*` en `.env`, vuelve a correr el seed.
