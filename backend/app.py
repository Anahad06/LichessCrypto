import berserk
from datetime import datetime, timezone, timedelta
import pymongo
from bson.objectid import ObjectId
import logging
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
import time


app = Flask(__name__)
CORS(app)


# Setup logging
logging.basicConfig(level=logging.DEBUG)


# MongoDB setup
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["chess_betting"]
collection = db["matches"]


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


    if not opponent_username or not api_token:
        logging.error("Missing title or body")
        return jsonify({'error': 'Missing title or body'}), 400


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


        challenge_id = challenge['challenge']['id']
        game_id = wait_for_game_start(client, challenge_id)


        if not game_id:
            logging.error("Challenge not accepted")
            return jsonify({'error': 'Challenge not accepted'}), 400


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
    except Exception as e:
        logging.error("Exception occurred: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/replay_match', methods=['POST'])
def replay_match():
    data = request.json
    opponent_username = data.get('title')
    api_token = data.get('body')


    if not opponent_username or not api_token:
        return jsonify({'error': 'Missing title or body'}), 400


    session = berserk.TokenSession(api_token)
    client = berserk.Client(session=session)


    try:
        challenge = client.challenges.create(
            username=opponent_username,
            clock_limit=60,
            clock_increment=0,
            rated=False
        )
        challenge_id = challenge['challenge']['id']
        game_id = wait_for_game_start(client, challenge_id)


        if not game_id:
            return jsonify({'error': 'Challenge not accepted'}), 400


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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/recent_match_winner', methods=['POST'])
def recent_match_winner():
    data = request.json
    username = data.get('username')
    api_token = data.get('api_token')


    if not username or not api_token:
        return jsonify({'error': 'Missing username or api_token'}), 400


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


            response = {
                'status': 'success',
                'game_id': game_id,
                'created_at': recent_game['createdAt'],
                'winner': winner_username
            }
            return jsonify(response), 200
        else:
            return jsonify({'error': 'No recent games found.'}), 404
    except Exception as e:
        logging.error("Exception occurred: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)