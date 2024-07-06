// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ChessBet {
    struct Bet {
        address payable player1;
        address payable player2;
        uint256 amount;
        bool isActive;
    }

    mapping(bytes32 => Bet) public bets;

    function placeBet(bytes32 gameId, address payable opponent) external payable {
        require(msg.value > 0, "Bet amount must be greater than zero");
        require(!bets[gameId].isActive, "Bet already active for this game");

        bets[gameId] = Bet({
            player1: payable(msg.sender),
            player2: opponent,
            amount: msg.value,
            isActive: true
        });
    }

    function declareWinner(bytes32 gameId, address winner) external {
        require(bets[gameId].isActive, "No active bet for this game");

        Bet memory bet = bets[gameId];
        if (winner == bet.player1) {
            bet.player1.transfer(bet.amount * 2);
        } else if (winner == bet.player2) {
            bet.player2.transfer(bet.amount * 2);
        }
        bets[gameId].isActive = false;
    }
}
