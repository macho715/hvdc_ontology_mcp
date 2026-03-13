FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY server.py /app/server.py
COPY install.py /app/install.py
COPY README.md /app/README.md
COPY AGENTS.md /app/AGENTS.md
COPY CLAUDE.md /app/CLAUDE.md
COPY CHATGPT_CODEX_CURSOR_HANDOFF.md /app/CHATGPT_CODEX_CURSOR_HANDOFF.md
COPY WINDOWS_MULTI_PC_PACKAGE.md /app/WINDOWS_MULTI_PC_PACKAGE.md
COPY SETUP_WINDOWS_FULL.cmd /app/SETUP_WINDOWS_FULL.cmd
COPY .codex /app/.codex
COPY .cursor /app/.cursor
COPY docs /app/docs
COPY hvdc_ops /app/hvdc_ops
COPY widgets /app/widgets
COPY scripts /app/scripts

RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "scripts/railway_run.py"]
