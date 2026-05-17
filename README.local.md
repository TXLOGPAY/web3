# TxLogPay Web3 — Plataforma de Comércio Exterior na Blockchain Stellar

Sistema full-stack de escrow e rastreamento logístico de comércio exterior, com smart contracts Soroban, RAG LlamaIndex, Merkle Tree e ancoragem Etherfuse.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14)                    │
│  /platform  /importer  /exporter  /operations/new               │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST API
┌─────────────────────────▼───────────────────────────────────────┐
│                    BACKEND (FastAPI)                             │
│  /stellar  /flags  /escrow  /rag  /etherfuse  /operations       │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Stellar SDK │  │  LlamaIndex  │  │    Etherfuse Ramp     │  │
│  │  (accounts,  │  │  RAG + PDF   │  │  (onramp/offramp)    │  │
│  │   Soroban)   │  │  extraction  │  │                      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘  │
│         │                 │                                      │
│         │          ┌──────▼───────┐                             │
│         │          │  Merkle Tree │                             │
│         │          │  (32-byte    │                             │
│         │          │   root hash) │                             │
│         │          └──────┬───────┘                             │
└─────────┼────────────────┼────────────────────────────────────-─┘
          │                │ (anchor root)
┌─────────▼────────────────▼───────────────────────────────────────┐
│                   STELLAR BLOCKCHAIN (Testnet)                    │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  FlagsReceptor   │  │     Escrow       │  │   TradeInfo   │  │
│  │                  │  │                  │  │               │  │
│  │  set_inco()      │◄─┤  release() verif │  │  register_    │  │
│  │  set_emba()      │  │  2% fee TxLogPay │  │  trade()      │  │
│  │  set_modal()     │  │  importer→escrow │  │               │  │
│  │  set_dese()      │  │  escrow→exporter │  │  Merkle root  │  │
│  │  set_libera()    │  │                  │  │  stored       │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Fluxo Logístico (Flags Soroban)

| Flag | Código | Descrição |
|------|--------|-----------|
| Acordo Incoterm | `inco` | Termos comerciais confirmados entre as partes |
| Embarque | `emba` | Carga embarcada na origem |
| Modal | `modal` | Em trânsito pelo modal de transporte acordado |
| Desembarque | `dese` | Chegada no porto/aeroporto de destino |
| Liberação | `libera` | Liberação alfandegária concluída |

Cada flag é setada on-chain no contrato `FlagsReceptor`. O contrato `Escrow` verifica a flag acordada antes de liberar o pagamento.

---

## Smart Contracts (Soroban / Rust)

### 1. FlagsReceptor (`contracts/flags-receptor/`)
- Receptor das bandeiras logísticas
- Fluxo sequencial: `inco → emba → modal → dese → libera`
- Apenas setter autorizado pode avançar flags
- Emite eventos on-chain para cada flag

### 2. Escrow (`contracts/escrow/`)
- Pagamento entre importador e exportador
- **Taxa 2% TxLogPay** calculada automaticamente (200 bps)
- Liberação somente quando a flag acordada está confirmada no FlagsReceptor
- Proteção contra reentrância por operação
- Funções: `create_escrow → fund → release → refund/dispute`

### 3. TradeInfo (`contracts/trade-info/`)
- Armazena dados de comércio exterior minerados via RAG
- Campos: invoice, BL, incoterm, produto, quantidade, valor, países, Siscomex ID
- Armazena hash Merkle root (32 bytes) para integridade dos dados

---

## RAG + Merkle Tree

1. Upload de fatura (PDF/DOCX/TXT) via `POST /api/v1/rag/extract`
2. **LlamaIndex** processa o documento com `claude-sonnet-4-6`
3. Extrai: invoice, BL, incoterm, produto, HS code, quantidades, valores, países
4. Os dados são inseridos em um **Merkle Tree binário**
5. O root hash (32 bytes) é armazenado on-chain via `TradeInfo.register_trade()`
6. Qualquer dado pode ser verificado com prova Merkle sem expor todo o documento

---

## Ancoragem Etherfuse

Integração via [Etherfuse Ramp API](https://github.com/etherfuse/ramp-api-example):

| Endpoint | Uso |
|----------|-----|
| `POST /onboarding-url` | Gerar URL de KYC para importador/exportador |
| `POST /order` | Criar ordem onramp (fiat→Stellar) ou offramp |
| `GET /order/{id}` | Consultar status da ordem |
| `POST /orders` | Listar ordens de uma conta |
| `POST /wallets` | Listar carteiras do cliente |
| `POST /webhook` | Registrar webhook de eventos |

---

## Scrapy — Mineração ModalPay

Spider Playwright para extração de dados do site ModalPay:

```bash
make scrape-local
# Gera: backend/scrapy_spider/modalpay_data.json
```

Extrai: navegação, formulários, campos, tabelas, cards de operação, métricas.

---

## Setup

### Pré-requisitos
- Node.js 20+
- Python 3.12+
- Rust + `wasm32-unknown-unknown` target
- [Stellar CLI](https://developers.stellar.org/docs/tools/stellar-cli)
- Docker + Docker Compose

### 1. Configurar variáveis

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
# Editar com: ANTHROPIC_API_KEY, ETHERFUSE_API_KEY
```

### 2. Criar contas Stellar testnet

```bash
# Com o backend rodando:
curl -X POST http://localhost:8000/api/v1/stellar/accounts/setup-demo
# Salvar as chaves retornadas no .env
```

### 3. Deploy dos contratos

```bash
cd contracts
export STELLAR_DEPLOYER_SECRET=S...  # chave secreta do deployer
export STELLAR_ADMIN_PUBLIC=G...
export STELLAR_PLATFORM_PUBLIC=G...  # conta TxLogPay (recebe 2%)
bash deploy.sh
# Copiar os IDs retornados para backend/.env
```

### 4. Rodar em desenvolvimento

```bash
make dev-docker
# Backend: http://localhost:8000/docs
# Frontend: http://localhost:3000
```

### 5. Scraping ModalPay

```bash
make scrape-local
```

---

## Estrutura do Projeto

```
web3/
├── contracts/                  # Soroban smart contracts (Rust)
│   ├── flags-receptor/         # Bandeiras logísticas
│   ├── escrow/                 # Escrow com fee 2%
│   ├── trade-info/             # Dados de comércio + Merkle
│   ├── Cargo.toml              # Workspace
│   └── deploy.sh               # Script de deploy
│
├── backend/                    # FastAPI (Python)
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── stellar.py      # Contas Stellar
│   │   │   ├── flags.py        # Acionar flags on-chain
│   │   │   ├── escrow.py       # Criar/fundar/liberar escrow
│   │   │   ├── rag.py          # Upload invoice + Merkle
│   │   │   ├── etherfuse.py    # On/off-ramp
│   │   │   └── operations.py   # Gestão de operações
│   │   ├── services/
│   │   │   ├── stellar_service.py
│   │   │   ├── merkle_tree.py
│   │   │   ├── rag_service.py
│   │   │   └── etherfuse_service.py
│   │   └── models/schemas.py
│   ├── scrapy_spider/          # Spider Playwright para ModalPay
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                   # Next.js 14 (TypeScript)
│   ├── app/
│   │   ├── page.tsx            # Landing page
│   │   ├── (dashboard)/
│   │   │   ├── platform/       # Visão plataforma
│   │   │   ├── importer/       # Visão importador
│   │   │   ├── exporter/       # Visão exportador
│   │   │   └── operations/new/ # Criar operação
│   ├── components/logistics/
│   │   ├── LogisticsTimeline.tsx
│   │   ├── OperationCard.tsx
│   │   └── InvoiceUpload.tsx
│   └── lib/api.ts
│
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## API Reference

Documentação interativa disponível em: `http://localhost:8000/docs`

### Principais endpoints

```
POST   /api/v1/stellar/accounts          Criar conta Stellar
POST   /api/v1/stellar/accounts/fund     Financiar via Friendbot (testnet)
POST   /api/v1/stellar/accounts/setup-demo  Criar 3 contas demo

POST   /api/v1/flags/init/{op_id}        Inicializar operação no contrato
POST   /api/v1/flags/set                 Setar flag logística on-chain
GET    /api/v1/flags/{op_id}             Consultar flags

POST   /api/v1/escrow/create             Criar escrow
POST   /api/v1/escrow/fund               Importador deposita tokens
POST   /api/v1/escrow/release            Liberar pagamento (verifica flag)
GET    /api/v1/escrow/fee/{amount}       Calcular taxa 2%

POST   /api/v1/rag/extract               Upload invoice → extração RAG
POST   /api/v1/rag/merkle/compute        Computar Merkle root
POST   /api/v1/rag/anchor                Ancorar na blockchain

POST   /api/v1/etherfuse/onboard         KYC onboarding URL
POST   /api/v1/etherfuse/orders          Criar ordem ramp
GET    /api/v1/etherfuse/orders/{id}     Status da ordem

GET    /api/v1/operations/               Listar operações (plataforma)
POST   /api/v1/operations/               Criar operação
GET    /api/v1/operations/importer/{pk}  Operações do importador
GET    /api/v1/operations/exporter/{pk}  Operações do exportador
```

---

## Escrow e Taxa TxLogPay

```
Valor total: USD 184,500
Taxa 2% (TxLogPay): USD 3,690  → conta plataforma
Exportador recebe: USD 180,810

Liberação: somente quando a flag acordada (ex: dese) é confirmada on-chain
```
