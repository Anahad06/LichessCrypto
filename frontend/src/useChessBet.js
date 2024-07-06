import { useState, useEffect } from 'react';
import Web3 from 'web3';
import ChessBet from './contracts/ChessBet.json';

const useChessBet = () => {
  const [account, setAccount] = useState(null);
  const [contract, setContract] = useState(null);
  const [web3, setWeb3] = useState(null);

  useEffect(() => {
    const init = async () => {
      if (window.ethereum) {
        const web3 = new Web3(window.ethereum);
        setWeb3(web3);
        const accounts = await web3.eth.requestAccounts();
        setAccount(accounts[0]);
        const networkId = await web3.eth.net.getId();
        const deployedNetwork = ChessBet.networks[networkId];
        if (deployedNetwork) {
          const contract = new web3.eth.Contract(
            ChessBet.abi,
            deployedNetwork && deployedNetwork.address,
          );
          setContract(contract);
        } else {
          console.error('Smart contract not deployed to the detected network.');
        }
      } else {
        console.error('MetaMask not detected');
      }
    };
    init();
  }, []);

  const connectWallet = async () => {
    if (window.ethereum) {
      try {
        await window.ethereum.request({ method: 'eth_requestAccounts' });
        const accounts = await web3.eth.getAccounts();
        setAccount(accounts[0]);
        return accounts[0];
      } catch (error) {
        console.error('User denied account access:', error);
      }
    } else {
      console.error('MetaMask not detected');
    }
  };

  const placeBet = async (gameId, opponentAddress, betAmount) => {
    if (!contract || !account) return;
    try {
      await contract.methods.placeBet(gameId, opponentAddress).send({
        from: account,
        value: web3.utils.toWei(betAmount, 'ether')
      });
    } catch (error) {
      console.error('Error placing bet:', error);
      throw error;  // Rethrow the error to be caught in App.js
    }
  };

  const declareWinner = async (gameId, winnerAddress, opponentWallet) => {
    if (!contract || !account) return;
    try {
      await contract.methods.declareWinner(gameId, winnerAddress).send({
        from: account,
        to: opponentWallet,
      });
    } catch (error) {
      console.error('Error declaring winner:', error);
      throw error;  // Rethrow the error to be caught in App.js
    }
  };

  return {
    account,
    connectWallet,
    placeBet,
    declareWinner
  };
};

export default useChessBet;

