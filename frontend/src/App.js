import React, { useState } from 'react';
import axios from 'axios';
import './App.css';  // Import the CSS file
import useChessBet from './useChessBet';

function App() {
  const [post, setPost] = useState({
    title: '',
    body: '',
    opponentWallet: '',
    accountAddress: '',
    privateKey: '',
    betAmount: '0.1'  // Default bet amount
  });

  const [message, setMessage] = useState('');
  const [rematchPrompt, setRematchPrompt] = useState(false);
  const [existingMatch, setExistingMatch] = useState(null);
  const [recentMatchData, setRecentMatchData] = useState({
    username: '',
    api_token: '',
    opponentWallet: '',
    accountAddress: '',
    privateKey: ''
  });
  const [recentMatchMessage, setRecentMatchMessage] = useState('');
  const [transactionStatus, setTransactionStatus] = useState('');

  const { account, connectWallet, placeBet, declareWinner } = useChessBet();

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
        setPost({ title: '', body: '', opponentWallet: '', accountAddress: '', privateKey: '', betAmount: '0.1' });
      }
    } catch (err) {
      console.error('Error during handleSubmit:', err);
      setTransactionStatus(`Error placing bet on blockchain: ${err.message}`);
      setMessage(`Error: ${err.response ? err.response.data.error : err.message}`);
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
      setPost({ title: '', body: '', opponentWallet: '', accountAddress: '', privateKey: '', betAmount: '0.1' });
    } catch (err) {
      console.error('Error during handleRematch:', err);
      setTransactionStatus(`Error placing bet on blockchain: ${err.message}`);
      setMessage(`Error: ${err.response ? err.response.data.error : err.message}`);
    }
  };

  const handleGetRecentMatchWinner = async (event) => {
    event.preventDefault();
    try {
      const response = await axios.post('http://localhost:5000/recent_match_winner', recentMatchData);
      const data = response.data;
      if (data.status === 'success') {
        setRecentMatchMessage(`Match ID: ${data.game_id}, Created At: ${new Date(data.created_at).toLocaleString()}, Winner: ${data.winner}`);
        setTransactionStatus('Winner declared successfully!');
      } else {
        setRecentMatchMessage(`Error: ${data.error}`);
        setTransactionStatus('Error declaring winner on blockchain');
      }
      setRecentMatchData({ username: '', api_token: '', opponentWallet: '', accountAddress: '', privateKey: '' });
    } catch (err) {
      console.error('Error during handleGetRecentMatchWinner:', err);
      setTransactionStatus(`Error declaring winner on blockchain: ${err.message}`);
      setRecentMatchMessage(`Error: ${err.response ? err.response.data.error : err.message}`);
    }
  };

  const handleConnectWallet = async () => {
    const account = await connectWallet();
    setTransactionStatus(`Connected to account: ${account}`);
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
        <input
          type="text"
          placeholder="Opponent Wallet Address"
          value={post.opponentWallet}
          onChange={handleInput}
          name="opponentWallet"
        />
        <input
          type="text"
          placeholder="Your Account Address"
          value={post.accountAddress}
          onChange={handleInput}
          name="accountAddress"
        />
        <input
          type="password"
          placeholder="Your Private Key"
          value={post.privateKey}
          onChange={handleInput}
          name="privateKey"
        />
        <input
          type="text"
          placeholder="Bet Amount (ETH)"
          value={post.betAmount}
          onChange={handleInput}
          name="betAmount"
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
        <input
          type="text"
          placeholder="Opponent Wallet Address"
          value={recentMatchData.opponentWallet}
          onChange={handleRecentMatchInput}
          name="opponentWallet"
        />
        <input
          type="text"
          placeholder="Your Account Address"
          value={recentMatchData.accountAddress}
          onChange={handleRecentMatchInput}
          name="accountAddress"
        />
        <input
          type="password"
          placeholder="Your Private Key"
          value={recentMatchData.privateKey}
          onChange={handleRecentMatchInput}
          name="privateKey"
        />
        <button onClick={handleGetRecentMatchWinner} className="btn">Get Winner</button>
      </div>
      {recentMatchMessage && <p>{recentMatchMessage}</p>}
      {transactionStatus && <p>{transactionStatus}</p>}
    </div>
  );
}

export default App;
