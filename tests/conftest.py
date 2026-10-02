"""Shared fixtures and helpers for local tests (in-memory chain, no real ETH).

Run:  python scripts/compile.py && python -m pytest -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from eth_account import Account
from web3 import EthereumTesterProvider, Web3
from eth_tester.exceptions import TransactionFailed
from web3.exceptions import ContractLogicError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import deploy  # noqa: E402

ETH = 10**18
REVERT = (ContractLogicError, TransactionFailed)


def artifact(name):
    return json.loads((ROOT / "build" / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def w3():
    return Web3(EthereumTesterProvider())


@pytest.fixture
def accts(w3):
    return w3.eth.accounts


def deploy_local(w3, name, *args, sender=None):
    art = artifact(name)
    factory = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
    tx = factory.constructor(*args).transact({"from": sender or w3.eth.accounts[0]})
    addr = w3.eth.wait_for_transaction_receipt(tx)["contractAddress"]
    return w3.eth.contract(address=addr, abi=art["abi"])


def advance(w3, seconds):
    w3.provider.ethereum_tester.time_travel(w3.eth.get_block("latest")["timestamp"] + seconds)
    w3.provider.ethereum_tester.mine_blocks()
