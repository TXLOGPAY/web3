# TxLogPay — Makefile
.PHONY: all setup dev build contracts deploy scrape test clean

# ── Setup ─────────────────────────────────────────────────────────────────────
setup:
	@echo "Setting up TxLogPay..."
	cp backend/.env.example backend/.env
	cp frontend/.env.local.example frontend/.env.local
	cd frontend && npm install
	cd backend && pip install -r requirements.txt
	@echo "Done! Edit backend/.env with your keys."

# ── Dev servers ───────────────────────────────────────────────────────────────
dev:
	docker-compose up -d postgres redis
	@echo "Starting backend and frontend..."
	cd backend && uvicorn app.main:app --reload &
	cd frontend && npm run dev

dev-docker:
	docker-compose up --build

# ── Contracts ─────────────────────────────────────────────────────────────────
contracts-build:
	cd contracts && cargo build --target wasm32-unknown-unknown --release

contracts-test:
	cd contracts && cargo test

contracts-deploy:
	cd contracts && bash deploy.sh

# ── Demo accounts setup ───────────────────────────────────────────────────────
setup-stellar:
	curl -X POST http://localhost:8000/api/v1/stellar/accounts/setup-demo | python -m json.tool

# ── Scraping ──────────────────────────────────────────────────────────────────
scrape:
	docker-compose --profile scrape run scrapy

scrape-local:
	cd backend/scrapy_spider && \
	playwright install chromium && \
	scrapy crawl modalpay -o modalpay_data.json

# ── Build ─────────────────────────────────────────────────────────────────────
build:
	cd frontend && npm run build
	cd contracts && cargo build --target wasm32-unknown-unknown --release

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	cd contracts && cargo test
	cd backend && python -m pytest

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	docker-compose down -v
	cd frontend && rm -rf .next node_modules
	cd contracts && cargo clean
