"""
Simple SQLite database layer for the prototype.
3 tables: users, assets, transactions.
Plain sqlite3, no ORM.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "prototype.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            wallet_address TEXT NOT NULL UNIQUE,
            role TEXT DEFAULT 'none',
            status TEXT DEFAULT 'pending',
            blockchain_tx_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            metadata TEXT,
            owner_wallet TEXT NOT NULL,
            blockchain_tx_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            transaction_hash TEXT NOT NULL,
            from_address TEXT,
            to_address TEXT,
            transaction_type TEXT NOT NULL,
            status TEXT DEFAULT 'confirmed',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.close()


# --- User functions ---

def create_user(name, wallet_address, tx_hash):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO users (name, wallet_address, blockchain_tx_hash) VALUES (?, ?, ?)",
        (name, wallet_address, tx_hash)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_wallet(wallet_address):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE wallet_address = ?", (wallet_address,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_status(user_id, status, tx_hash=None):
    conn = get_connection()
    if tx_hash:
        conn.execute(
            "UPDATE users SET status = ?, blockchain_tx_hash = ? WHERE id = ?",
            (status, tx_hash, user_id)
        )
    else:
        conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    conn.close()


def update_user_role(user_id, role, tx_hash=None):
    conn = get_connection()
    if tx_hash:
        conn.execute(
            "UPDATE users SET role = ?, blockchain_tx_hash = ? WHERE id = ?",
            (role, tx_hash, user_id)
        )
    else:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
    conn.close()


# --- Asset functions ---

def create_asset(asset_id, name, metadata, owner_wallet, tx_hash):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO assets (asset_id, name, metadata, owner_wallet, blockchain_tx_hash) VALUES (?, ?, ?, ?, ?)",
        (asset_id, name, metadata, owner_wallet, tx_hash)
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_asset(asset_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_asset_owner(asset_id, new_owner_wallet):
    conn = get_connection()
    conn.execute(
        "UPDATE assets SET owner_wallet = ? WHERE asset_id = ?",
        (new_owner_wallet, asset_id)
    )
    conn.commit()
    conn.close()


# --- Transaction functions ---

def create_transaction(asset_id, tx_hash, from_address, to_address, tx_type):
    conn = get_connection()
    conn.execute(
        "INSERT INTO transactions (asset_id, transaction_hash, from_address, to_address, transaction_type) VALUES (?, ?, ?, ?, ?)",
        (asset_id, tx_hash, from_address, to_address, tx_type)
    )
    conn.commit()
    conn.close()


def get_asset_history(asset_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE asset_id = ? ORDER BY timestamp DESC",
        (asset_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
