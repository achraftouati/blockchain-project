--CREATE DATABASE blockchain_app;

USE blockchain_app;

-- Create Users Table
CREATE TABLE Users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    public_key VARCHAR(1024) NOT NULL UNIQUE, -- Public key for the user
    private_key VARCHAR(1024) NOT NULL, -- Store the private key securely
    password_hash VARCHAR(255) NOT NULL, -- Store the hashed password
    wallet_id VARCHAR(255) UNIQUE NULL, -- Unique wallet identifier
    user_type VARCHAR(50) DEFAULT 'regular', -- Default user type
    CONSTRAINT usertype CHECK (user_type IN ('regular', 'miner', 'validator','admin')) -- Enforce valid user types
);

-- Create Wallet Table
CREATE TABLE Wallet (
    id INT IDENTITY(1,1) PRIMARY KEY, -- Unique wallet ID
    user_id INT NOT NULL, -- Foreign key to the Users table
    balance INT DEFAULT 1000, -- Initial balance for the wallet
    stake INT DEFAULT 0, -- Stake amount for the wallet
    FOREIGN KEY (user_id) REFERENCES Users(id) -- Link to the Users table
);

-- Create Blocks Table
CREATE TABLE Blocks (
    id INT IDENTITY(1,1) PRIMARY KEY, -- Unique block ID
    creation_date DATETIME DEFAULT GETDATE(), -- Block creation timestamp
    is_locked BIT DEFAULT 0, -- Indicates whether the block is locked (0 = open, 1 = locked)
    creator_public_key VARCHAR(1024) NOT NULL, -- Public key of the user who created the block
    FOREIGN KEY (creator_public_key) REFERENCES Users(public_key) -- Link to the Users table
);

-- Create Transactions Table
CREATE TABLE Transactions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    block_id INT, -- Foreign key to the Blocks table
    source_public_key VARCHAR(1024) NOT NULL, -- Source public key for the transaction
    destination_public_key VARCHAR(1024) NOT NULL, -- Destination public key for the transaction
    amount INT NOT NULL, -- Amount of the transaction
    type VARCHAR(50) NOT NULL, -- Type of transaction (e.g., 'buy', 'sell')
    timestamp DATETIME DEFAULT GETDATE(), -- Timestamp of the transaction
    hash VARCHAR(255) NOT NULL, -- Hash of the transaction
    signature VARCHAR(1024) NOT NULL, -- Digital signature of the transaction
    validator_public_key VARCHAR(1024) DEFAULT NULL, -- Public key of the validator
    FOREIGN KEY (block_id) REFERENCES Blocks(id), -- Link to the Blocks table
    FOREIGN KEY (source_public_key) REFERENCES Users(public_key),
    FOREIGN KEY (destination_public_key) REFERENCES Users(public_key),
    FOREIGN KEY (validator_public_key) REFERENCES Users(public_key), -- Link to the validator
    CONSTRAINT transactiontype CHECK (type IN ('sell', 'buy')) -- Enforce valid transaction types
);