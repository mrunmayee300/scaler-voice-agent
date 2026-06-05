.PHONY: dev ingest test eval docker-up docker-down

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

ingest:
	python ingestion/build_index.py

test:
	cd backend && pytest ../tests -v

eval:
	python evals/run_evals.py

docker-up:
	docker compose up -d

docker-down:
	docker compose down
