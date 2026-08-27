"""
Flask REST API for the blockchain identity & asset management prototype.
Simple single-file application. No authentication framework — the backend
deployer account acts as the admin/operator for this prototype.
"""

from flask import Flask, request, jsonify
from web3 import Web3
import database as db
import blockchain_service as bc

app = Flask(__name__)

# Hardhat test accounts (addresses only — keys are never exposed)
# Account #0 is the deployer/admin, accounts #1-#19 are assignable to users
HARDHAT_ACCOUNTS = [
    "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
    "0x90F79bf6EB2c4f870365E785982E1f101E93b906",
    "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
    "0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc",
    "0x976EA74026E726554dB657fA54763abd0C3a0aa9",
    "0x14dC79964da2C08b23698B3D3cc7Ca32193d9955",
    "0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f",
    "0xa0Ee7A142d267C1f36714E4a8F75612F20a79720",
]

# Track which account index to assign next (skip #0 = admin)
next_account_index = 1


def get_next_wallet():
    """Assign the next available Hardhat test wallet address."""
    global next_account_index
    if next_account_index >= len(HARDHAT_ACCOUNTS):
        return None
    addr = HARDHAT_ACCOUNTS[next_account_index]
    next_account_index += 1
    return addr


# --- Identity Endpoints ---

@app.route("/api/users", methods=["POST"])
def create_user():
    """Register a new user with a Hardhat test wallet and on-chain identity."""
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Name is required"}), 400

    name = data["name"].strip()
    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400

    # Assign next Hardhat wallet
    wallet = get_next_wallet()
    if not wallet:
        return jsonify({"error": "No more test wallets available"}), 500

    # Register identity on blockchain
    try:
        tx_hash = bc.register_identity(wallet, name)
    except Exception as e:
        return jsonify({"error": f"Blockchain error: {str(e)}"}), 500

    # Store in database
    user_id = db.create_user(name, wallet, tx_hash)

    return jsonify({
        "id": user_id,
        "name": name,
        "wallet_address": wallet,
        "status": "pending",
        "role": "none",
        "blockchain_tx_hash": tx_hash
    }), 201


@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get user information from database."""
    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "wallet_address": user["wallet_address"],
        "status": user["status"],
        "role": user["role"],
        "blockchain_tx_hash": user["blockchain_tx_hash"],
        "created_at": user["created_at"]
    })


@app.route("/api/users/<int:user_id>/verify", methods=["POST"])
def verify_user(user_id):
    """Admin verifies a user's identity on-chain."""
    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user["status"] != "pending":
        return jsonify({"error": f"User status is '{user['status']}', must be 'pending'"}), 400

    # Verify on blockchain
    try:
        tx_hash = bc.verify_identity(user["wallet_address"])
    except Exception as e:
        return jsonify({"error": f"Blockchain error: {str(e)}"}), 500

    # Update database
    db.update_user_status(user_id, "verified", tx_hash)

    return jsonify({
        "id": user_id,
        "status": "verified",
        "blockchain_tx_hash": tx_hash
    })


@app.route("/api/users/<int:user_id>/role", methods=["POST"])
def assign_role(user_id):
    """Assign a role to a verified user."""
    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user["status"] != "verified":
        return jsonify({"error": "User must be verified before assigning a role"}), 400

    data = request.get_json()
    if not data or not data.get("role"):
        return jsonify({"error": "Role is required"}), 400

    role = data["role"].lower().strip()
    valid_roles = ["user", "assetmanager", "admin"]
    if role not in valid_roles:
        return jsonify({"error": f"Invalid role. Must be one of: {valid_roles}"}), 400

    # Assign role on blockchain
    try:
        tx_hash = bc.assign_role(user["wallet_address"], role)
    except Exception as e:
        return jsonify({"error": f"Blockchain error: {str(e)}"}), 500

    # Update database
    db.update_user_role(user_id, role, tx_hash)

    return jsonify({
        "id": user_id,
        "role": role,
        "blockchain_tx_hash": tx_hash
    })


# --- Asset Endpoints ---

@app.route("/api/assets", methods=["POST"])
def create_asset():
    """Register a new digital asset on the blockchain."""
    data = request.get_json()
    if not data or not data.get("name") or not data.get("owner_id"):
        return jsonify({"error": "name and owner_id are required"}), 400

    name = data["name"].strip()
    metadata = data.get("metadata", "")
    owner_id = data["owner_id"]

    # Get owner user
    owner = db.get_user(owner_id)
    if not owner:
        return jsonify({"error": "Owner user not found"}), 404

    # Check authorization: owner must have AssetManager or Admin role
    if owner["role"] not in ["assetmanager", "admin"]:
        return jsonify({"error": "Owner must have AssetManager or Admin role to register assets"}), 403

    # Generate asset ID (keccak hash of name + timestamp for uniqueness)
    import time
    asset_id_source = f"{name}-{owner['wallet_address']}-{time.time()}"
    asset_id_hex = Web3.keccak(text=asset_id_source).hex()

    # Register on blockchain
    try:
        tx_hash = bc.register_asset(asset_id_hex, owner["wallet_address"])
    except Exception as e:
        return jsonify({"error": f"Blockchain error: {str(e)}"}), 500

    # Store in database
    db.create_asset(asset_id_hex, name, metadata, owner["wallet_address"], tx_hash)

    # Record transaction
    db.create_transaction(asset_id_hex, tx_hash, "0x0", owner["wallet_address"], "registration")

    return jsonify({
        "asset_id": asset_id_hex,
        "name": name,
        "metadata": metadata,
        "owner_wallet": owner["wallet_address"],
        "owner_id": owner_id,
        "blockchain_tx_hash": tx_hash
    }), 201


@app.route("/api/assets/<asset_id>", methods=["GET"])
def get_asset(asset_id):
    """Get asset info from database and verify on-chain owner."""
    asset = db.get_asset(asset_id)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    # Read current owner from blockchain for verification
    try:
        blockchain_owner = bc.get_asset_owner(asset_id)
    except Exception:
        blockchain_owner = "unable to read from blockchain"

    return jsonify({
        "asset_id": asset["asset_id"],
        "name": asset["name"],
        "metadata": asset["metadata"],
        "owner_wallet": asset["owner_wallet"],
        "blockchain_owner": blockchain_owner,
        "blockchain_tx_hash": asset["blockchain_tx_hash"],
        "created_at": asset["created_at"]
    })


@app.route("/api/assets/<asset_id>/transfer", methods=["POST"])
def transfer_asset(asset_id):
    """Transfer asset ownership to another user via blockchain."""
    asset = db.get_asset(asset_id)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    data = request.get_json()
    if not data or not data.get("to_user_id"):
        return jsonify({"error": "to_user_id is required"}), 400

    to_user_id = data["to_user_id"]
    to_user = db.get_user(to_user_id)
    if not to_user:
        return jsonify({"error": "Destination user not found"}), 404

    new_owner_wallet = to_user["wallet_address"]
    previous_owner_wallet = asset["owner_wallet"]

    if new_owner_wallet == previous_owner_wallet:
        return jsonify({"error": "Cannot transfer to current owner"}), 400

    # Transfer on blockchain (contract enforces permission rules)
    try:
        tx_hash = bc.transfer_asset(asset_id, new_owner_wallet)
    except Exception as e:
        return jsonify({"error": f"Blockchain error: {str(e)}"}), 500

    # Update database
    db.update_asset_owner(asset_id, new_owner_wallet)

    # Record transaction
    db.create_transaction(asset_id, tx_hash, previous_owner_wallet, new_owner_wallet, "transfer")

    return jsonify({
        "asset_id": asset_id,
        "from_wallet": previous_owner_wallet,
        "to_wallet": new_owner_wallet,
        "blockchain_tx_hash": tx_hash
    })


@app.route("/api/assets/<asset_id>/history", methods=["GET"])
def get_asset_history(asset_id):
    """Get transaction history for an asset."""
    asset = db.get_asset(asset_id)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    history = db.get_asset_history(asset_id)

    return jsonify({
        "asset_id": asset_id,
        "transactions": history
    })


# --- App startup ---

def setup_deployer_as_admin():
    """Register the deployer account as Admin in the identity contract.
    The deployer signs all transactions, so it needs Admin role for
    the AssetRegistry contract to authorize its calls.
    """
    identity = bc.get_identity(bc.DEPLOYER_ADDRESS)
    if identity["status"] == "not_registered":
        print("Setting up deployer as Admin on-chain...")
        bc.register_identity(bc.DEPLOYER_ADDRESS, "Admin")
        bc.verify_identity(bc.DEPLOYER_ADDRESS)
        bc.assign_role(bc.DEPLOYER_ADDRESS, "admin")
        print("Deployer registered as Admin.")
    else:
        print("Deployer already registered on-chain.")


if __name__ == "__main__":
    db.init_db()
    print("Database initialized.")
    print(f"Connected to blockchain: {bc.is_connected()}")
    print(f"Deployer: {bc.DEPLOYER_ADDRESS}")
    setup_deployer_as_admin()
    app.run(host="0.0.0.0", port=5000, debug=True)
