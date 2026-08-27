# Blockchain-Based Identity, Access Control & Digital Asset Management

A functional prototype demonstrating a complete blockchain-backed workflow:

**Register User → Verify Identity → Assign Role → Register Asset → Transfer Ownership → Transaction History**

All blockchain operations produce real transactions on a local Hardhat node. Nothing is faked.

## Tech Stack

- **Blockchain**: Solidity 0.8.20, Hardhat, OpenZeppelin (Ownable)
- **Backend**: Python, Flask, Web3.py, SQLite
- **Network**: Local Hardhat node (localhost:8545)

## Project Structure

```
blockchain-identity-platform/
├── blockchain/
│   ├── contracts/
│   │   ├── IdentityAndAccess.sol   # Identity lifecycle + role management
│   │   └── AssetRegistry.sol       # Asset registration + ownership transfer
│   ├── test/
│   │   └── test-contracts.js       # Smart contract tests (11 tests)
│   ├── scripts/
│   │   └── deploy.js               # Deployment script
│   └── hardhat.config.js
├── backend/
│   ├── app.py                      # Flask REST API (8 endpoints)
│   ├── blockchain_service.py       # Web3.py contract interactions
│   ├── database.py                 # SQLite database layer
│   └── .env.example                # Environment variables template
├── .gitignore
└── README.md
```

## Prerequisites

- Node.js 18+
- Python 3.9+
- npm

## How to Run

### 1. Install blockchain dependencies

```bash
cd blockchain
npm install
```

### 2. Start local Hardhat blockchain

```bash
cd blockchain
npx hardhat node
```

Keep this terminal open. The node runs on http://127.0.0.1:8545.

### 3. Deploy smart contracts (new terminal)

```bash
cd blockchain
npx hardhat run scripts/deploy.js --network localhost
```

Note the deployed contract addresses printed in the output.

### 4. Setup and start backend (new terminal)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Update `.env` with the contract addresses from step 3 (if different from defaults).

```bash
python app.py
```

The API runs on http://127.0.0.1:5000.

### 5. Run smart contract tests

```bash
cd blockchain
npx hardhat test
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users` | Register user `{"name": "Alice"}` |
| GET | `/api/users/<id>` | Get user info |
| POST | `/api/users/<id>/verify` | Admin verifies identity |
| POST | `/api/users/<id>/role` | Assign role `{"role": "AssetManager"}` |
| POST | `/api/assets` | Register asset `{"name": "Doc", "owner_id": 1}` |
| GET | `/api/assets/<id>` | Get asset + blockchain owner |
| POST | `/api/assets/<id>/transfer` | Transfer `{"to_user_id": 2}` |
| GET | `/api/assets/<id>/history` | Transaction history |

Roles: `User`, `AssetManager`, `Admin`

## Demo Flow

```bash
# 1. Register user
curl -X POST http://localhost:5000/api/users -H "Content-Type: application/json" -d "{\"name\": \"Alice\"}"

# 2. Verify user (returns tx_hash)
curl -X POST http://localhost:5000/api/users/1/verify

# 3. Assign role
curl -X POST http://localhost:5000/api/users/1/role -H "Content-Type: application/json" -d "{\"role\": \"AssetManager\"}"

# 4. Register asset
curl -X POST http://localhost:5000/api/assets -H "Content-Type: application/json" -d "{\"name\": \"Certificate\", \"metadata\": \"BSc CS\", \"owner_id\": 1}"

# 5. Create second user, verify, assign User role
curl -X POST http://localhost:5000/api/users -H "Content-Type: application/json" -d "{\"name\": \"Bob\"}"
curl -X POST http://localhost:5000/api/users/2/verify
curl -X POST http://localhost:5000/api/users/2/role -H "Content-Type: application/json" -d "{\"role\": \"User\"}"

# 6. Transfer asset (use asset_id from step 4 response)
curl -X POST http://localhost:5000/api/assets/<asset_id>/transfer -H "Content-Type: application/json" -d "{\"to_user_id\": 2}"

# 7. Verify new owner on blockchain
curl http://localhost:5000/api/assets/<asset_id>

# 8. Check history
curl http://localhost:5000/api/assets/<asset_id>/history
```

## What's Stored Where

| On-Chain (Blockchain) | Off-Chain (SQLite) |
|-----------------------|--------------------|
| Identity state (pending/verified) | User name, metadata |
| Role assignments | Wallet-to-user mapping |
| Asset ownership | Asset name, description |
| Transfer events | Transaction history index |

## Security Notes

- This is a **PROTOTYPE** for demonstration purposes only
- All private keys are Hardhat default test keys (publicly known)
- The deployer account signs all transactions as the admin operator
- **Never use these keys or this configuration in production**
- Private keys are loaded from `.env` only, never logged or returned via API
