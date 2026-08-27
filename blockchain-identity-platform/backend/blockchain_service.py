"""
Blockchain service layer for the prototype.
Connects to local Hardhat node via Web3.py.
Signs all transactions with the deployer (admin) private key from .env.

IMPORTANT: The private key is loaded into memory only.
Never logged, stored in DB, or returned via API.
This is a DEVELOPMENT/TEST prototype only.
"""

import os
import json
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---

BLOCKCHAIN_URL = os.getenv("BLOCKCHAIN_URL", "http://127.0.0.1:8545")
DEPLOYER_PRIVATE_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")
IDENTITY_CONTRACT_ADDRESS = os.getenv("IDENTITY_CONTRACT_ADDRESS")
ASSET_CONTRACT_ADDRESS = os.getenv("ASSET_CONTRACT_ADDRESS")

# --- Web3 Setup ---

w3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_URL))

# Derive deployer address from private key (never expose the key itself)
deployer_account = w3.eth.account.from_key(DEPLOYER_PRIVATE_KEY)
DEPLOYER_ADDRESS = deployer_account.address


def _load_abi(contract_name):
    """Load ABI from Hardhat artifacts."""
    artifact_path = os.path.join(
        os.path.dirname(__file__), "..", "blockchain", "artifacts", "contracts",
        f"{contract_name}.sol", f"{contract_name}.json"
    )
    with open(artifact_path, "r") as f:
        artifact = json.load(f)
    return artifact["abi"]


# Load contract instances
identity_abi = _load_abi("IdentityAndAccess")
asset_abi = _load_abi("AssetRegistry")

identity_contract = w3.eth.contract(
    address=Web3.to_checksum_address(IDENTITY_CONTRACT_ADDRESS),
    abi=identity_abi
)
asset_contract = w3.eth.contract(
    address=Web3.to_checksum_address(ASSET_CONTRACT_ADDRESS),
    abi=asset_abi
)


def _send_transaction(tx):
    """Build, sign, send a transaction and wait for receipt. Returns tx hash hex."""
    tx["from"] = DEPLOYER_ADDRESS
    tx["nonce"] = w3.eth.get_transaction_count(DEPLOYER_ADDRESS)
    tx["gas"] = tx.get("gas", 500000)

    # Remove gasPrice if present — use EIP-1559 fields for Web3.py 7.x
    tx.pop("gasPrice", None)
    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas", 0)
    tx["maxFeePerGas"] = base_fee * 2 + w3.to_wei(1, "gwei")
    tx["maxPriorityFeePerGas"] = w3.to_wei(1, "gwei")

    signed = w3.eth.account.sign_transaction(tx, DEPLOYER_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt["status"] != 1:
        raise Exception(f"Transaction reverted: {tx_hash.hex()}")

    return tx_hash.hex()


# --- Identity Functions ---

def register_identity(wallet_address, name):
    """Register an identity on-chain. Returns tx hash."""
    name_hash = Web3.keccak(text=name)
    tx = identity_contract.functions.registerIdentity(
        Web3.to_checksum_address(wallet_address),
        name_hash
    ).build_transaction({"from": DEPLOYER_ADDRESS})
    return _send_transaction(tx)


def verify_identity(wallet_address):
    """Admin verifies a pending identity. Returns tx hash."""
    tx = identity_contract.functions.verifyIdentity(
        Web3.to_checksum_address(wallet_address)
    ).build_transaction({"from": DEPLOYER_ADDRESS})
    return _send_transaction(tx)


def assign_role(wallet_address, role):
    """Assign a role to a verified identity. Returns tx hash.
    Roles: 1=User, 2=AssetManager, 3=Admin
    """
    role_map = {"user": 1, "assetmanager": 2, "admin": 3}
    role_int = role_map.get(role.lower())
    if role_int is None:
        raise ValueError(f"Invalid role: {role}. Must be user, assetmanager, or admin.")

    tx = identity_contract.functions.assignRole(
        Web3.to_checksum_address(wallet_address),
        role_int
    ).build_transaction({"from": DEPLOYER_ADDRESS})
    return _send_transaction(tx)


def get_identity(wallet_address):
    """Read identity from blockchain. Returns (nameHash, status, role)."""
    result = identity_contract.functions.getIdentity(
        Web3.to_checksum_address(wallet_address)
    ).call()
    status_map = {0: "not_registered", 1: "pending", 2: "verified", 3: "revoked"}
    role_map = {0: "none", 1: "user", 2: "assetmanager", 3: "admin"}
    return {
        "name_hash": result[0].hex(),
        "status": status_map.get(result[1], "unknown"),
        "role": role_map.get(result[2], "unknown")
    }


def check_role(wallet_address, role):
    """Check if address has a specific role on-chain."""
    role_map = {"user": 1, "assetmanager": 2, "admin": 3}
    role_int = role_map.get(role.lower(), 0)
    return identity_contract.functions.hasRole(
        Web3.to_checksum_address(wallet_address),
        role_int
    ).call()


# --- Asset Functions ---

def register_asset(asset_id_hex, owner_wallet):
    """Register a digital asset on-chain. Returns tx hash.
    asset_id_hex should be a bytes32 hex string.
    """
    asset_id_bytes = bytes.fromhex(asset_id_hex.replace("0x", ""))
    tx = asset_contract.functions.registerAsset(
        asset_id_bytes,
        Web3.to_checksum_address(owner_wallet)
    ).build_transaction({"from": DEPLOYER_ADDRESS})
    return _send_transaction(tx)


def transfer_asset(asset_id_hex, new_owner_wallet):
    """Transfer asset ownership on-chain. Returns tx hash."""
    asset_id_bytes = bytes.fromhex(asset_id_hex.replace("0x", ""))
    tx = asset_contract.functions.transferAsset(
        asset_id_bytes,
        Web3.to_checksum_address(new_owner_wallet)
    ).build_transaction({"from": DEPLOYER_ADDRESS})
    return _send_transaction(tx)


def get_asset_owner(asset_id_hex):
    """Get current owner of an asset from blockchain."""
    asset_id_bytes = bytes.fromhex(asset_id_hex.replace("0x", ""))
    return asset_contract.functions.getAssetOwner(asset_id_bytes).call()


def is_connected():
    """Check if Web3 is connected to the node."""
    return w3.is_connected()
