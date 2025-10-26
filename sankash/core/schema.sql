-- Sankash Database Schema

-- Accounts table
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    bank VARCHAR NOT NULL,
    account_number VARCHAR NOT NULL,
    currency VARCHAR NOT NULL DEFAULT 'EUR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    parent_category VARCHAR,
    color VARCHAR NOT NULL DEFAULT '#6366f1',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    date DATE NOT NULL,
    payee VARCHAR NOT NULL,
    notes TEXT,
    amount DECIMAL(12, 2) NOT NULL,
    category VARCHAR,
    is_categorized BOOLEAN NOT NULL DEFAULT FALSE,
    is_transfer BOOLEAN NOT NULL DEFAULT FALSE,
    transfer_account_id INTEGER,
    imported_id VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (transfer_account_id) REFERENCES accounts(id)
);

-- Rules table
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    conditions JSON NOT NULL,
    actions JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_transactions_is_categorized ON transactions(is_categorized);
CREATE INDEX IF NOT EXISTS idx_transactions_imported_id ON transactions(imported_id);
CREATE INDEX IF NOT EXISTS idx_rules_priority ON rules(priority);
