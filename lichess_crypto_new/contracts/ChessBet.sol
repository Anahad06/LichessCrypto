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
        if (bets[gameId].isActive) {
            // Second player is placing their bet
            require(bets[gameId].player2 == address(0), "Opponent has already placed a bet");
            require(msg.value == bets[gameId].amount, "Bet amount must match opponent's bet");

            bets[gameId].player2 = payable(msg.sender);
        } else {
            // First player is placing their bet
            bets[gameId] = Bet({
                player1: payable(msg.sender),
                player2: opponent,
                amount: msg.value,
                isActive: true
            });
        }
    }

    function declareWinner(bytes32 gameId, address winner) external {
        require(bets[gameId].isActive, "No active bet for this game");
        require(bets[gameId].player2 != address(0), "Opponent has not placed a bet yet");

        Bet memory bet = bets[gameId];
        uint256 totalAmount = bet.amount * 2; // Total amount is the sum of both bets

        if (winner == bet.player1) {
            bet.player1.transfer(totalAmount);
        } else if (winner == bet.player2) {
            bet.player2.transfer(totalAmount);
        }
        bets[gameId].isActive = false;
    }
}
