"""Check deployments on-chain: confirms each recorded address really holds code.

Usage:
    python scripts/status.py --network base
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from web3 import Web3

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import NETWORKS, load_env, load_records  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", choices=NETWORKS, default="base")
    opts = parser.parse_args()

    load_env()
    net = NETWORKS[opts.network]
    rpc = os.environ.get("BASE_SEPOLIA_RPC" if opts.network == "base-sepolia" else "BASE_RPC") or net["rpc"]
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 60}))

    records = load_records(opts.network)
    if not records:
        print(f"No deployments recorded for {opts.network}.")
        return

    live = 0
    for r in records:
        has_code = len(w3.eth.get_code(Web3.to_checksum_address(r["address"]))) > 0
        live += has_code
        mark = "OK " if has_code else "MISSING"
        print(f"[{mark}] {r['contract']:14} {r['address']}  deployer {r['deployer']}")

    deployers = {r["deployer"] for r in records}
    print(f"\n{live}/{len(records)} contracts live on {opts.network}")
    for d in deployers:
        n = sum(1 for r in records if r["deployer"] == d)
        print(f"  deployer {d}: {n} contract(s)")
    milestones = [m for m in (1, 5, 10) if live >= m]
    print(f"Guild milestones reached: {milestones or 'none yet'}")


if __name__ == "__main__":
    main()
