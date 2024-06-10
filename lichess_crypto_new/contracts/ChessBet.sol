// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ChessBetting {
    address public owner;
    mapping(bytes32 => Match) public matches;

    struct Match {
        address player1;
        address player2;
        uint256 betAmount;
        address winner;
        bool paid;
    }

    constructor() {
        owner = msg.sender;
    }

    function createMatch(bytes32 matchId, address player2) public payable {
        require(matches[matchId].player1 == address(0), "Match already exists");
        require(msg.value > 0, "Bet amount must be greater than zero");

        matches[matchId] = Match({
            player1: msg.sender,
            player2: player2,
            betAmount: msg.value,
            winner: address(0),
            paid: false
        });
    }

    function setWinner(bytes32 matchId, address winner) public {
        require(msg.sender == owner, "Only owner can set the winner");
        Match storage chessMatch = matches[matchId];
        require(chessMatch.winner == address(0), "Winner already set");

        chessMatch.winner = winner;
    }

    function payWinner(bytes32 matchId) public {
        Match storage chessMatch = matches[matchId];
        require(chessMatch.winner != address(0), "Winner not set");
        require(!chessMatch.paid, "Winner already paid");

        uint256 amount = chessMatch.betAmount;
        chessMatch.paid = true;
        payable(chessMatch.winner).transfer(amount);
    }
}
