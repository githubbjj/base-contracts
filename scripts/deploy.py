"""Deploy compiled contracts to Base (or Base Sepolia).

Examples:
    python scripts/deploy.py Counter --network base-sepolia     # testnet rehearsal
    python scripts/deploy.py Counter --network base             # mainnet (asks to confirm)
    python scripts/deploy.py --all --network base               # every contract not yet deployed
    python scripts/deploy.py --list                             # show contracts and constructor args

Every successful deployment is appended to deployments/<network>.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from eth_account import Account
from web3 import Web3

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
DEPLOY_DIR = ROOT / "deployments"

NETWORKS = {
    "base": {"chain_id": 8453, "rpc": "https://mainnet.base.org", "explorer": "https://basescan.org"},
    "base-sepolia": {"chain_id": 84532, "rpc": "https://sepolia.base.org", "explorer": "https://sepolia.basescan.org"},
}

# Deployment order and constructor args. Each entry takes the deployer address.
CONTRACTS = {
    "Counter": lambda me: [],
    "SimpleStorage": lambda me: [],
    "Token": lambda me: ["Builder Token", "BLDR", 1_000_000 * 10**18],
    "Nft": lambda me: ["Builder Pass", "BPASS"],
    "Faucet": lambda me: [Web3.to_wei(0.0001, "ether"), 24 * 60 * 60],
    "NameRegistry": lambda me: [],
    "Escrow": lambda me: [],
    "Vesting": lambda me: [me, int(time.time()), 365 * 24 * 60 * 60],
    "MultiSig": lambda me: [[me], 1],
    "Timelock": lambda me: [2 * 24 * 60 * 60],
}


def load_env(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines) so no extra dependency is needed."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_artifact(name: str) -> dict:
    path = BUILD_DIR / f"{name}.json"
    if not path.exists():
        sys.exit(f"build/{name}.json not found. Run: python scripts/compile.py")
    return json.loads(path.read_text(encoding="utf-8"))


def load_records(network: str) -> list[dict]:
    path = DEPLOY_DIR / f"{network}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def save_record(network: str, record: dict) -> None:
    DEPLOY_DIR.mkdir(exist_ok=True)
    records = load_records(network)
    records.append(record)
    (DEPLOY_DIR / f"{network}.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def build_deploy_tx(w3: Web3, sender: str, name: str, args: list) -> dict:
    art = load_artifact(name)
    factory = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
    tx = factory.constructor(*args).build_transaction(
        {"from": sender, "nonce": w3.eth.get_transaction_count(sender, "pending"), "chainId": w3.eth.chain_id}
    )
    # 20% headroom on the gas estimate.
    tx["gas"] = int(tx["gas"] * 1.2)
    return tx


def send_deploy(w3: Web3, account, name: str, args: list) -> dict:
    tx = build_deploy_tx(w3, account.address, name, args)
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt["status"] != 1:
        raise RuntimeError(f"{name} deployment reverted: {tx_hash.hex()}")
    return {
        "contract": name,
        "address": receipt["contractAddress"],
        "tx": "0x" + tx_hash.hex().removeprefix("0x"),
        "block": receipt["blockNumber"],
        "deployer": account.address,
        "args": [str(a) if isinstance(a, int) else a for a in args],
        "timestamp": int(time.time()),
    }


def estimate_cost_eth(w3: Web3, tx: dict) -> float:
    fee = tx.get("maxFeePerGas") or tx.get("gasPrice") or w3.eth.gas_price
    return float(Web3.from_wei(tx["gas"] * fee, "ether"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("contract", nargs="?", help="Contract name, e.g. Counter")
    parser.add_argument("--network", choices=NETWORKS, default="base-sepolia")
    parser.add_argument("--all", action="store_true", help="Deploy every contract not yet deployed on this network")
    parser.add_argument("--force", action="store_true", help="Deploy even if already recorded for this network")
    parser.add_argument("--yes", action="store_true", help="Skip the mainnet confirmation prompt")
    parser.add_argument("--list", action="store_true", help="List deployable contracts and exit")
    opts = parser.parse_args()

    if opts.list:
        for name, fn in CONTRACTS.items():
            print(f"{name:14} args={fn('0xDEPLOYER')}")
        return

    if not opts.contract and not opts.all:
        parser.error("give a contract name or --all")
    if opts.contract and opts.contract not in CONTRACTS:
        parser.error(f"unknown contract {opts.contract!r}; choose from {', '.join(CONTRACTS)}")

    load_env()
    key = os.environ.get("PRIVATE_KEY")
    if not key:
        sys.exit("PRIVATE_KEY missing. Copy .env.example to .env and fill it in.")

    net = NETWORKS[opts.network]
    rpc = os.environ.get("BASE_SEPOLIA_RPC" if opts.network == "base-sepolia" else "BASE_RPC") or net["rpc"]
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 60}))
    if w3.eth.chain_id != net["chain_id"]:
        sys.exit(f"RPC chain id {w3.eth.chain_id} != expected {net['chain_id']} for {opts.network}")

    account = Account.from_key(key)
    balance = Web3.from_wei(w3.eth.get_balance(account.address), "ether")
    print(f"Network : {opts.network} (chain {net['chain_id']})")
    print(f"Deployer: {account.address}  balance {balance:.6f} ETH")

    done = {r["contract"] for r in load_records(opts.network)}
    targets = list(CONTRACTS) if opts.all else [opts.contract]
    if not opts.force:
        skipped = [t for t in targets if t in done]
        targets = [t for t in targets if t not in done]
        if skipped:
            print(f"Already deployed (skip, use --force to redeploy): {', '.join(skipped)}")
    if not targets:
        print("Nothing to deploy.")
        return

    plan = []
    total = 0.0
    for name in targets:
        args = CONTRACTS[name](account.address)
        cost = estimate_cost_eth(w3, build_deploy_tx(w3, account.address, name, args))
        total += cost
        plan.append((name, args))
        print(f"  {name:14} est. max cost {cost:.8f} ETH")
    print(f"  {'TOTAL':14} est. max cost {total:.8f} ETH")

    if total > float(balance):
        sys.exit("Balance too low for the estimated cost.")
    if opts.network == "base" and not opts.yes:
        if input("Deploy to Base MAINNET? type 'yes' to continue: ").strip().lower() != "yes":
            sys.exit("Aborted.")

    for name, args in plan:
        print(f"Deploying {name}...", end=" ", flush=True)
        record = send_deploy(w3, account, name, args)
        save_record(opts.network, record)
        print(f"{record['address']}  {net['explorer']}/tx/{record['tx']}")

    count = len(load_records(opts.network))
    print(f"Done. {count} deployment(s) recorded in deployments/{opts.network}.json")


if __name__ == "__main__":
    main()
