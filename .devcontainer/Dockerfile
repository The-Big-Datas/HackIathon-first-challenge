# mcr.microsoft.com/devcontainers/python:3.11 is maintained, patched, and
# includes a non-root `vscode` user — required by the claude-code feature.
FROM mcr.microsoft.com/devcontainers/python:3.11

# Install project dependencies as root, then drop to vscode
USER root

COPY requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

COPY frontend/requirements.txt /tmp/frontend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/frontend-requirements.txt

# Ownership so vscode can write pip cache etc.
RUN chown -R vscode:vscode /usr/local/lib/python3.11 2>/dev/null || true

# Pre-create .claude dir owned by vscode so Docker initializes the named
# volume with correct ownership on first mount (empty volume copies from image).
RUN mkdir -p /home/vscode/.claude && chown -R vscode:vscode /home/vscode/.claude

USER vscode
