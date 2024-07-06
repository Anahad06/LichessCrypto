import React, { useState } from 'react';
import axios from 'axios';
import './App.css';  // Import the CSS file
import useChessBet from './useChessBet';

function App() {
    const [post, setPost] = useState({
        title: '',
        body: ''
    });

    const [transactionStatus, setTransactionStatus] = useState('');

    const [message, setMessage] = useState('');
    const [rematchPrompt, setRematchPrompt] = useState(false);
    const [existingMatch, setExistingMatch] = useState(null);
    const [recentMatchData, setRecentMatchData] = useState({
        username: '',
        api_token: ''
    });
    const [recentMatchMessage, setRecentMatchMessage] = useState('');
    const [account, setAccount] = useState(null);

    const { connectWallet, placeBet, declareWinner } = useChessBet();

    const handleInput = (event) => {
        setPost({ ...post, [event.target.name]: event.target.value });
    };

    const handleRecentMatchInput = (event) => {
        setRecentMatchData({ ...recentMatchData, [event.target.name]: event.target.value });
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        try {
            const response = await axios.post('http://localhost:5000/create_post', post);
            const data = response.data;
            if (data.status === 'exists') {
                setMessage(data.message);
                setExistingMatch(data.existing_match);
                setRematchPrompt(true);
            } else {
                setMessage(`Match Created. Match ID: ${data.match_id}`);
                // Place bet on blockchain
                const betAmount = '0.1'; // Example bet amount, you can make this dynamic
                await placeBet(data.match_id, data.opponent_address, betAmount);
                // Reset form after successful submission
                setPost({ title: '', body: '' });
            }
        } catch (err) {
            console.log(err);
            if (err.response) {
                setMessage(`Error: ${err.response.data.error}`);
            } else {
                setMessage("An unknown error occurred");
            }
        }
    };

    const handleRematch = async (event) => {
        event.preventDefault();
        try {
            const response = await axios.post('http://localhost:5000/replay_match', post);
            const data = response.data;
            setMessage(`Rematch Created. Match ID: ${data.match_id}`);
            setRematchPrompt(false);
            setExistingMatch(null);
            setPost({ title: '', body: '' });
            // Place bet on blockchain
            const betAmount = '0.1'; // Example bet amount, you can make this dynamic
            await placeBet(data.match_id, data.opponent_address, betAmount);
        } catch (err) {
            console.log(err);
            if (err.response) {
                setMessage(`Error: ${err.response.data.error}`);
            } else {
                setMessage("An unknown error occurred");
            }
        }
    };

    const handleGetRecentMatchWinner = async (event) => {
        event.preventDefault();
        try {
            const response = await axios.post('http://localhost:5000/recent_match_winner', recentMatchData);
            const data = response.data;
            if (data.status === 'success') {
                setRecentMatchMessage(`Match ID: ${data.game_id}, Created At: ${new Date(data.created_at).toLocaleString()}, Winner: ${data.winner}`);
                // Declare winner on blockchain
                await declareWinner(data.game_id, data.winner_address);
            } else {
                setRecentMatchMessage(`Error: ${data.error}`);
            }
            // Reset form after successful submission
            setRecentMatchData({ username: '', api_token: '' });
        } catch (err) {
            console.log(err);
            if (err.response) {
                setRecentMatchMessage(`Error: ${err.response.data.error}`);
            } else {
                setRecentMatchMessage("An unknown error occurred");
            }
        }
    };

    const handleConnectWallet = async () => {
        const account = await connectWallet();
        setAccount(account);
    };

    return (
        <div className="app">
            <h1>Crypto Chess Betting</h1>
            <button onClick={handleConnectWallet} className="btn">Connect Wallet</button>
            {account && <p>Connected account: {account}</p>}
            <p className="instructions">
                Go to <a href="https://lichess.org" target="_blank" rel="noopener noreferrer">Lichess</a> ➡️
                'Preferences' ➡️ 'API Access Token' ➡️ Create API Token with game permissions ➡️ Insert API Token here.
            </p>
            <div className="form-group">
                <h2>Create Match</h2>
                <input
                    type="text"
                    placeholder="Opponent Username"
                    value={post.title}
                    onChange={handleInput}
                    name="title"
                />
                <input
                    type="text"
                    placeholder="Your API Token"
                    value={post.body}
                    onChange={handleInput}
                    name="body"
                />
                <button onClick={handleSubmit} className="btn">Submit</button>
            </div>
            {message && <p className={rematchPrompt ? "bold-center" : ""}>{message}</p>}
            {rematchPrompt && (
                <div className="rematch-prompt">
                    <p>Do you want to play again with the same opponent?</p>
                    <button onClick={handleRematch} className="btn">Yes</button>
                </div>
            )}

            <h2>Check Winner</h2>
            <div className="form-group">
                <input
                    type="text"
                    placeholder="Username"
                    value={recentMatchData.username}
                    onChange={handleRecentMatchInput}
                    name="username"
                />
                <input
                    type="text"
                    placeholder="API Token"
                    value={recentMatchData.api_token}
                    onChange={handleRecentMatchInput}
                    name="api_token"
                />
                <button onClick={handleGetRecentMatchWinner} className="btn">Get Winner</button>
            </div>
            {recentMatchMessage && <p>{recentMatchMessage}</p>}
        </div>
    );
}

export default App;
