.PHONY: preflight config up demo-up down migrate backend-test frontend-check http-smoke reset-demo

preflight:
	python3 scripts/preflight.py

config:
	docker compose --env-file .env config --quiet

up:
	docker compose --env-file .env up --build -d

demo-up:
	docker compose -p fairdrop-demo --env-file .env -f compose.yaml -f infra/compose.demo.yaml --profile lab up --build -d

down:
	docker compose --env-file .env down

migrate:
	docker compose --env-file .env run --rm migrate

backend-test:
	cd backend && uv run pytest -q

frontend-check:
	cd frontend && npm run lint && npm run build

http-smoke:
	python3 scripts/http_smoke.py --credential-file private/organizer.json --output reports/local-smoke.json

reset-demo:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/demo_reset.ps1 -IUnderstandThisDeletesDemoData
