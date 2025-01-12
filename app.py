from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import ecdsa
import pyodbc
from datetime import datetime


app = Flask(__name__) 

CORS(app)

def get_db_connection():
    connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS01;DATABASE=blockchain_app;Trusted_Connection=yes'
    conn = pyodbc.connect(connection_string)
    return conn

def generate_private_key(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_public_key(private_key):
    private_key_bytes = bytes.fromhex(private_key)
    signing_key = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
    verifying_key = signing_key.verifying_key
    return verifying_key.to_string("compressed").hex()
    
@app.route('/get_users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, last_name, public_key, user_type FROM Users")
        rows = cursor.fetchall()
        conn.close()

        users = []
        for row in rows:
            users.append({
                'id': row[0],
                'name': row[1],
                'last_name': row[2],
                'public_key': row[3],
                'user_type': row[4]
            })

        return jsonify({'users': users}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/create_user', methods=['POST'])
def create_user():
    data = request.json
    name = data['name']
    last_name = data['last_name']
    password = data['password']

    private_key = generate_private_key(password)
    public_key = generate_public_key(private_key)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO Users (name, last_name, public_key, private_key, password_hash,wallet_id, user_type)
            VALUES (?, ?, ?, ?, ?,99999999,'regular')
            """,
            (name, last_name, public_key, private_key, password)
        )

        cursor.execute("SELECT id FROM Users WHERE public_key = ?", (public_key,))
        user_id = cursor.fetchone()[0]  # Fetch the user ID

        cursor.execute(
            """
            INSERT INTO Wallet (user_id, balance, stake)
            VALUES (?, ?, ?)
            """,
            (user_id, 1000, 0)  # Default balance and stake
        )

        cursor.execute("SELECT id FROM Wallet WHERE user_id = ?", (user_id,))
        wallet_id = cursor.fetchone()[0]  # Fetch the wallet ID

        cursor.execute(
            """
            UPDATE Users
            SET wallet_id = ?
            WHERE id = ?
            """,
            (wallet_id, user_id)
        )
        conn.commit()
        conn.close()

        return jsonify({
            'message': 'User and wallet created successfully!',
            'public_key': public_key,
            'wallet_id': wallet_id
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/delete_wallet', methods=['POST'])
def delete_wallet():
    data = request.json  
    public_key = data.get('public_key') 

    if not public_key:
        return jsonify({'error': 'Public key is required!'}), 400

    try:
        
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT w.id
            FROM Wallet w
            JOIN Users u ON w.user_id = u.id
            WHERE u.public_key = ?
            """,
            (public_key,)
        )
        wallet = cursor.fetchone()

        if not wallet:
            return jsonify({'error': 'Wallet not found for the given public key!'}), 404

        cursor.execute(
            """
            DELETE FROM Wallet
            WHERE user_id = (SELECT id FROM Users WHERE public_key = ?)
            """,
            (public_key,)
        )
        conn.commit()  
        conn.close() 

        return jsonify({'message': 'Wallet deleted successfully!'}), 200

    except Exception as e:
        app.logger.error(f"Error deleting wallet: {e}")
        return jsonify({'error': 'An error occurred while deleting the wallet.'}), 500

@app.route('/read_wallet', methods=['POST'])
def read_wallet():
    data = request.json  
    public_key = data.get('public_key')

    if not public_key:
        return jsonify({'error': 'Public key is required!'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT w.id AS wallet_id, w.balance, w.stake
            FROM Wallet w
            JOIN Users u ON w.user_id = u.id
            WHERE u.public_key = ?
            """,
            (public_key,)  
        )
        wallet = cursor.fetchone()  
        if not wallet:
            return jsonify({'error': 'Wallet not found for the given public key!'}), 404
        wallet_data = {
            'wallet_id': wallet[0], 
            'balance': wallet[1],    
            'stake': wallet[2]       
        }
        conn.close()
        return jsonify({'wallet': wallet_data}), 200

    except Exception as e:
        app.logger.error(f"Error reading wallet: {e}")
        return jsonify({'error': 'An error occurred while reading the wallet.'}), 500

def create_first_block():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM Blocks WHERE is_locked = 0")
    open_block = cursor.fetchone()

    if not open_block:
        cursor.execute(
            """
            INSERT INTO Blocks (creator_public_key)
            VALUES (?)
            """,
            ('system_public_key',)  
        )
        conn.commit()

    conn.close()


@app.route('/create_transaction', methods=['POST'])
def create_transaction():
    data = request.json
    source_public_key = data.get('source_public_key')
    destination_public_key = data.get('destination_public_key')
    amount = data.get('amount')
    transaction_type = data.get('transaction_type')

    if not source_public_key or not destination_public_key or not amount or not transaction_type:
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM Blocks WHERE is_locked = 0 ORDER BY creation_date DESC")
        open_block = cursor.fetchone()

        if not open_block:
            cursor.execute(
                """
                INSERT INTO Blocks (creator_public_key)
                VALUES (?)
                """,
                ('system_public_key',)  
            )
            conn.commit()
            cursor.execute("SELECT id FROM Blocks WHERE is_locked = 0 ORDER BY creation_date DESC")
            open_block = cursor.fetchone()

        block_id = open_block[0]

        transaction_data = f"{source_public_key}{destination_public_key}{amount}{transaction_type}{datetime.now()}"
        transaction_hash = hashlib.sha256(transaction_data.encode()).hexdigest()

        cursor.execute(
            """
            INSERT INTO Transactions (block_id, source_public_key, destination_public_key, amount, type, hash, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (block_id, source_public_key, destination_public_key, amount, transaction_type, transaction_hash, 'signature_placeholder')
        )
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM Transactions WHERE block_id = ?", (block_id,))
        transaction_count = cursor.fetchone()[0]

        if transaction_count >= 5:
            cursor.execute(
                """
                UPDATE Blocks
                SET is_locked = 1
                WHERE id = ?
                """,
                (block_id,)
            )
            conn.commit()
            cursor.execute(
                """
                INSERT INTO Blocks (creator_public_key)
                VALUES (?)
                """,
                ('system_public_key',) 
            )
            conn.commit()

        conn.close()
        return jsonify({'message': 'Transaction added successfully!'}), 201
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/get_blocks', methods=['GET'])
def get_blocks_with_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            b.id AS block_id,
            b.creation_date,
            b.is_locked,
            b.creator_public_key,
            t.id AS transaction_id,
            t.source_public_key,
            t.destination_public_key,
            t.amount,
            t.type,
            t.timestamp,
            t.hash
        FROM Blocks b
        LEFT JOIN Transactions t ON b.id = t.block_id
        ORDER BY b.id, t.timestamp
        """
    )

    blocks = {}
    for row in cursor.fetchall():
        block_id = row.block_id
        if block_id not in blocks:
            blocks[block_id] = {
                "block_id": block_id,
                "creation_date": row.creation_date,
                "is_locked": row.is_locked,
                "creator_public_key": row.creator_public_key,
                "transactions": []
            }

        if row.transaction_id:
            blocks[block_id]["transactions"].append({
                "transaction_id": row.transaction_id,
                "source_public_key": row.source_public_key,
                "destination_public_key": row.destination_public_key,
                "amount": row.amount,
                "type": row.type,
                "timestamp": row.timestamp,
                "hash": row.hash
            })

    conn.close()
    return jsonify(list(blocks.values()))

if __name__ == '__main__':
    create_first_block()
    app.run(debug=True)