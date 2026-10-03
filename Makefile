.PHONY: preflight config up demo-up down migrate backend-test e2e load-smoke reset-demo

preflight:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/preflight.ps1

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
	python -m unittest discover -s backend/tests/lab -p "test_*.py" -v

e2e:
	npx playwright test

load-smoke:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/preflight.ps1 -RequireLoadTools

reset-demo:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/demo_reset.ps1 -IUnderstandThisDeletesDemoData
