# Despliegue

Backend en **Fly.io** (FastAPI/Docker) y frontend en **Streamlit Community Cloud**.

## 1. Backend en Fly.io

Pre-requisitos: cuenta en https://fly.io y `flyctl` instalado
(`iwr https://fly.io/install.ps1 -useb | iex` en PowerShell).

```powershell
# 1) Login
flyctl auth login

# 2) Desde la raíz del repo
cd backend

# 3) Crear la app (si el nombre 'preauth-backend' está tomado, Fly te ofrecerá otro;
#    si lo cambias, actualiza también el campo `app` en backend/fly.toml).
flyctl apps create preauth-backend

# 4) Cargar los secretos (no se loguean ni se muestran en el dashboard)
flyctl secrets set `
  ANTHROPIC_API_KEY="sk-ant-..." `
  NOTION_TOKEN="ntn_..." `
  NOTION_DB_ASEGURADOS="..." `
  NOTION_DB_POLIZAS="..." `
  NOTION_DB_PLANES="..." `
  NOTION_DB_COBERTURAS="..." `
  NOTION_DB_INFORMES="..." `
  NOTION_DB_DECISIONES="..."

# 5) Build + deploy
flyctl deploy

# 6) Verifica
flyctl status
flyctl logs
curl https://preauth-backend.fly.dev/health
```

Notas:

- `fly.toml` declara `internal_port = 8080`, `auto_stop_machines = "stop"` y
  `min_machines_running = 0`: la máquina se duerme cuando no hay tráfico y se
  despierta en la primera petición. El cliente del frontend ya tolera ese
  cold-start (`GET_TIMEOUT = 45s`, `PROCESAR_TIMEOUT = 150s` en
  `frontend/api.py`).
- El healthcheck pega a `/health`, que existe en `backend/app/main.py`.
- Si necesitas la app siempre encendida, sube `min_machines_running` a `1`.

## 2. Frontend en Streamlit Community Cloud

1. Ve a https://share.streamlit.io y conecta el repo de GitHub.
2. **New app** → selecciona el repo y la rama `main`.
3. Configura:
   - **Main file path**: `frontend/app.py`
   - **Python version**: 3.12 (la que coincide con el backend)
4. En **Advanced settings → Secrets** pega:
   ```toml
   BACKEND_URL = "https://preauth-backend.fly.dev"
   ```
   (Reemplaza el host por el que te dio Fly si renombraste la app.)
5. **Deploy**. Streamlit detecta `frontend/requirements.txt` automáticamente.

`frontend/.streamlit/config.toml` ya está versionado (tema claro + headless).
`frontend/.streamlit/secrets.toml` está en `.gitignore`; en Community Cloud
los secretos se gestionan desde la UI, no desde el archivo.

## 3. Higiene

- `backend/.env` y la `.env` de la raíz contienen claves reales en este
  momento. Después del despliegue, **rota** `ANTHROPIC_API_KEY` y
  `NOTION_TOKEN` y verifica con `git log -- .env backend/.env` que nunca se
  commitearon (el `.gitignore` los excluye, pero conviene confirmarlo).
- Si Streamlit no logra conectar al backend, abre el panel de error que el
  frontend muestra: distingue `network`, `timeout`, `http` y `decode`.
