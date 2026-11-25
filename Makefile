up:
	docker compose up --build

up-ollama:
	docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build

down:
	docker compose down

logs:
	docker compose logs -f backend

dev:
	cd backend && uvicorn app:app --reload

check:
	cd backend && python check_retrieval.py

.PHONY: up up-ollama down logs dev check
