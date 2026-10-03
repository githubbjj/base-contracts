# base-contracts

A collection of small, dependency-free Solidity contracts deployed on [Base](https://base.org), with a pure-Python toolchain (web3.py + py-solc-x) for compiling, testing and deploying.

## Contracts

| Contract | What it does |
|---|---|
| `Counter` | Increment / decrement counter with owner-only reset |
| `SimpleStorage` | Per-address key → string note storage |
| `Token` | Minimal ERC20 with fixed supply |
| `Nft` | Minimal ERC721 with owner-only mint and per-token URI |
| `Faucet` | ETH faucet with drip amount and per-address cooldown |
| `NameRegistry` | First-come name → address registry |
| `Escrow` | Multi-deal ETH escrow settled by an arbiter |
| `Vesting` | Linear ETH vesting for one beneficiary |
| `MultiSig` | M-of-N wallet (submit / confirm / execute) |
| `Timelock` | Admin-queued calls with minimum delay and grace period |

All contracts use Solidity `0.8.24`, custom errors, and no external libraries.

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set PRIVATE_KEY
```

## Usage

```bash
python scripts/compile.py                               # build/<Name>.json
python -m pytest -q                                     # local tests on an in-memory chain
python scripts/deploy.py --list                         # contracts + constructor args
python scripts/deploy.py Counter --network base-sepolia # testnet
python scripts/deploy.py Counter --network base         # mainnet (asks for confirmation)
python scripts/status.py --network base                 # verify recorded deployments on-chain
```

Deployments are recorded in `deployments/<network>.json`.

## Deployments (Base mainnet)

| Contract | Address |
|---|---|
| Counter | 0x25c7643d31e765ec92ca970790dbbae31f37735f91cee370001ab94d7ba64e48 |

## License

MIT
