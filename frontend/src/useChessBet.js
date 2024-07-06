import Web3 from 'web3';
import ChessBet from './contracts/ChessBet.json';

const useChessBet = () => {
  const web3 = new Web3(Web3.givenProvider || "http://localhost:7545");
  const contractAddress = '0x7af1F6Aec33976271048Cb1FB15910b52a15B463'; 
  const contract = new web3.eth.Contract(ChessBet.abi, contractAddress);

  const connectWallet = async () => {
    if (window.ethereum) {
      try {
        await window.ethereum.request({ method: 'eth_requestAccounts' });
        const accounts = await web3.eth.getAccounts();
        return accounts[0];
      } catch (error) {
        console.error('User denied account access');
      }
    } else {
      console.error('MetaMask not detected');
    }
  };

  const placeBet = async (gameId, opponentAddress, betAmount) => {
    const accounts = await web3.eth.getAccounts();
    await contract.methods.placeBet(gameId, opponentAddress).send({
      from: accounts[0],
      value: web3.utils.toWei(betAmount, 'ether')
    });
  };

  const declareWinner = async (gameId, winnerAddress) => {
    const accounts = await web3.eth.getAccounts();
    await contract.methods.declareWinner(gameId, winnerAddress).send({
      from: accounts[0]
    });
  };

  return {
    connectWallet,
    placeBet,
    declareWinner
  };
};

export default useChessBet;
