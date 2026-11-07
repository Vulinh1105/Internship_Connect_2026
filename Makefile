PYTHON ?= python
export PYTHONPATH := backend
export DATABASE_URL ?= mysql+pymysql://career:career_local_only@127.0.0.1:3307/careerconnect?charset=utf8mb4
export QDRANT_URL ?= http://127.0.0.1:6335

.PHONY: up services migrate seed sync serve test
up: services
services:
	docker compose up -d --wait
migrate:
	$(PYTHON) -m alembic -c backend/alembic.ini upgrade head
seed:
	$(PYTHON) backend/scripts/seed_db.py
sync:
	$(PYTHON) backend/scripts/sync_vectors.py
serve:
	$(PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8010
test:
	$(PYTHON) -m pytest -q backend/tests
