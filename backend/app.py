import os
import berserk
from datetime import datetime, timezone, timedelta
import pymongo
from bson.objectid import ObjectId
import logging
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
import time
from web3 import Web3

app = Flask(__name__)
CORS(app)

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# MongoDB setup
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["chess_betting"]
collection = db["matches"]

# Web3 setup
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))  
contract_address = '0xBc126411fc406418373ed8EABff363fA826F3fc6' 

with open('contracts/ChessBet.json', 'r') as file:
    contract_abi = json.load(file)['abi']

contract = w3.eth.contract(address=contract_address, abi=contract_abi)

def create_transaction(function_call, account_address, private_key):
    nonce = w3.eth.getTransactionCount(account_address)
    txn = function_call.buildTransaction({
        'chainId': 5777,
        'gas': 2000000,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce,
    })
    signed_txn = w3.eth.account.signTransaction(txn, private_key=private_key)
    tx_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    return tx_hash.hex()

def place_bet_on_blockchain(game_id, opponent_wallet, bet_amount, account_address, private_key):
    function_call = contract.functions.placeBet(game_id, opponent_wallet)
    tx_hash = create_transaction(function_call, account_address, private_key)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    return receipt

def declare_winner_on_blockchain(game_id, winner_wallet, account_address, private_key):
    function_call = contract.functions.declareWinner(game_id, winner_wallet)
    tx_hash = create_transaction(function_call, account_address, private_key)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    return receipt

def check_game_result(api_token, game_id):
    session = berserk.TokenSession(api_token)
    client = berserk.Client(session=session)

    try:
        game_data = client.games.export(game_id)
        logging.debug(f"Game data: {game_data}")
       
        if 'status' in game_data:
            logging.debug(f"Game status: {game_data['status']}")
            if game_data['status'] == 'finished':
                winner_username = get_winner_username(client, game_id)
                collection.update_one(
                    {'match_id': game_id},
                    {'$set': {'winner': winner_username}}
                )
                return winner_username
            else:
                return 'pending'
        else:
            logging.error("No status field in game data")
            return 'error'
    except berserk.exceptions.ApiError as e:
        logging.error("ApiError occurred: %s", e)
        return 'error'
    except Exception as e:
        logging.error("Exception occurred: %s", e)
        logging.error(traceback.format_exc())
        return 'error'

def wait_for_game_start(client, challenge_id):
    try:
        incoming_events = client.board.stream_incoming_events()
        for event in incoming_events:
            if event['type'] == 'gameStart':
                return event['game']['id']
            time.sleep(1)
    except Exception as e:
        logging.error("Exception in wait_for_game_start: %s", e, exc_info=True)
        return None

@app.route('/create_post', methods=['POST'])
def create_post():
    data = request.json
    logging.debug("Received data: %s", data)  # Debugging statement

    opponent_username = data.get('title')
    api_token = data.get('body')
    opponent_wallet = data.get('opponentWallet')
    account_address = data.get('accountAddress')
    private_key = data.get('privateKey')
    bet_amount = data.get('betAmount', 0.1)  # Default bet amount to 0.1 ETH

    if not opponent_username or not api_token or not opponent_wallet or not account_address or not private_key:
        logging.error("Missing title, body, opponentWallet, accountAddress, or privateKey")
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        existing_match = collection.find_one({
            'opponent_username': opponent_username,
            'api_token': api_token,
            'match_id': {'$exists': True}
        })
        logging.debug("Existing match: %s", existing_match)

        if existing_match:
            existing_match['_id'] = str(existing_match['_id'])  # Convert ObjectId to string
            return jsonify({
                'status': 'exists',
                'message': 'A match with this opponent already exists.',
                'existing_match': existing_match,
                'prompt': 'Do you want to play again?'
            }), 200

        # Create a new match
        session = berserk.TokenSession(api_token)
        client = berserk.Client(session=session)

        challenge = client.challenges.create(
            username=opponent_username,
            clock_limit=60,
            clock_increment=0,
            rated=False
        )
        logging.debug("Challenge created: %s", challenge)

        if 'challenge' not in challenge:
            logging.error("Challenge creation failed: %s", challenge)
            return jsonify({'error': 'Challenge creation failed', 'details': challenge}), 400

        challenge_id = challenge['challenge']['id']
        game_id = wait_for_game_start(client, challenge_id)

        if not game_id:
            logging.error("Challenge not accepted")
            return jsonify({'error': 'Challenge not accepted'}), 400

        # Place bet on blockchain
        bet_receipt = place_bet_on_blockchain(game_id, opponent_wallet, bet_amount, account_address, private_key)
        logging.debug("Bet placed on blockchain: %s", bet_receipt)

        match_data = {
            'opponent_username': opponent_username,
            'api_token': api_token,
            'match_id': game_id,
            'winner': 'pending',
            'timestamp': time.time()
        }
        result = collection.insert_one(match_data)
        match_data['_id'] = str(result.inserted_id)  # Convert ObjectId to string

        response = {
            'status': 'success',
            'title': opponent_username,
            'body': api_token,
            'match_id': game_id,
            'winner': 'pending',
            'match_data_id': match_data['_id']
        }

        logging.debug("Response: %s", response)
        return jsonify(response)
    except berserk.exceptions.ApiError as e:
        logging.error("Berserk ApiError occurred: %s", e)
        return jsonify({'error': f'Berserk ApiError: {str(e)}'}), 500
    except Exception as e:
        logging.error("Exception occurred: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/replay_match', methods=['POST'])
def replay_match():
    data = request.json
    opponent_username = data.get('title')
    api_token = data.get('body')
    opponent_wallet = data.get('opponentWallet')
    account_address = data.get('accountAddress')
    private_key = data.get('privateKey')
    bet_amount = data.get('betAmount', 0.1)  # Default bet amount to 0.1 ETH

    if not opponent_username or not api_token or not opponent_wallet or not account_address or not private_key:
        return jsonify({'error': 'Missing required fields'}), 400

    session = berserk.TokenSession(api_token)
    client = berserk.Client(session=session)

    try:
        challenge = client.challenges.create(
            username=opponent_username,
            clock_limit=60,
            clock_increment=0,
            rated=False
        )
        logging.debug("Challenge response: %s", challenge)  # Log the full challenge response

        if 'challenge' not in challenge:
            logging.error("Challenge creation failed: %s", challenge)
            return jsonify({'error': 'Challenge creation failed', 'details': challenge}), 400

        challenge_id = challenge['challenge']['id']
        game_id = wait_for_game_start(client, challenge_id)

        if not game_id:
            return jsonify({'error': 'Challenge not accepted'}), 400

        # Place bet on blockchain
        bet_receipt = place_bet_on_blockchain(game_id, opponent_wallet, bet_amount, account_address, private_key)
        logging.debug("Bet placed on blockchain: %s", bet_receipt)

        # Save match details to MongoDB
        match_data = {
            'opponent_username': opponent_username,
            'api_token': api_token,
            'match_id': game_id,
            'winner': 'pending',
            'timestamp': time.time(),
            'replay': True
        }
        result = collection.insert_one(match_data)
        match_data['_id'] = str(result.inserted_id)  # Convert ObjectId to string

        response = {
            'status': 'success',
            'title': opponent_username,
            'body': api_token,
            'match_id': game_id,
            'winner': 'pending',
            'match_data_id': match_data['_id']
        }
        return jsonify(response)
    except berserk.exceptions.ApiError as e:
        logging.error("Berserk ApiError occurred: %s", e)
        return jsonify({'error': f'Berserk ApiError: {str(e)}'}), 500
    except Exception as e:
        logging.error("Exception occurred: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/recent_match_winner', methods=['POST'])
def recent_match_winner():
    data = request.json
    username = data.get('username')
    api_token = data.get('api_token')
    opponent_wallet = data.get('opponentWallet')
    account_address = data.get('accountAddress')
    private_key = data.get('privateKey')

    if not username or not api_token or not opponent_wallet or not account_address or not private_key:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        session = berserk.TokenSession(api_token)
        client = berserk.Client(session=session)

        # Get the current time
        end = berserk.utils.to_millis(datetime.now(timezone.utc))
        # Set a start time (e.g., 24 hours ago)
        start = berserk.utils.to_millis(datetime.now(timezone.utc) - timedelta(days=1))

        # Fetch recent games played by the player
        games = list(client.games.export_by_player(username, since=start, until=end, max=300))

        # Check if any games were found
        if games:
            # Get the most recent game
            recent_game = games[0]

            # Export the most recent game using its ID
            game_id = recent_game['id']
            recent_game_data = client.games.export(game_id)

            # Determine the result of the game
            winner = recent_game_data['winner'] if 'winner' in recent_game_data else 'None'
            players = recent_game_data['players']

            # Get the usernames of the players
            white_player = players['white']['user']['name']
            black_player = players['black']['user']['name']

            # Determine the winner's username
            if winner == 'white':
                winner_username = white_player
            elif winner == 'black':
                winner_username = black_player
            else:
                winner_username = "The game was a draw"

            # Declare winner on blockchain
            declare_receipt = declare_winner_on_blockchain(game_id, winner_username, account_address, private_key)
            logging.debug("Winner declared on blockchain: %s", declare_receipt)

            response = {
                'status': 'success',
                'game_id': game_id,
                'created_at': recent_game['createdAt'],
                'winner': winner_username
            }
            return jsonify(response), 200
        else:
            return jsonify({'error': 'No recent games found.'}), 404
    except berserk.exceptions.ApiError as e:
        logging.error("Berserk ApiError occurred: %s", e)
        return jsonify({'error': f'Berserk ApiError: {str(e)}'}), 500
    except Exception as e:
        logging.error("Exception occurred: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
