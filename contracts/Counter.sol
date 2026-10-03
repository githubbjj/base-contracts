// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Counter
/// @notice Minimal counter with owner-only reset.
contract Counter {
    uint256 public count;
    address public immutable owner;

    event Incremented(address indexed by, uint256 newCount);
    event Reset(uint256 previousCount);

    error NotOwner();
    error Underflow();

    constructor() {
        owner = msg.sender;
    }

    function increment() external {
        count += 1;
        emit Incremented(msg.sender, count);
    }

    function decrement() external {
        if (count == 0) revert Underflow();
        count -= 1;
    }

    function reset() external {
        if (msg.sender != owner) revert NotOwner();
        emit Reset(count);
        count = 0;
    }
}
