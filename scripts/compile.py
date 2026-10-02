"""Compile every contract in contracts/ into build/<Name>.json (abi + bytecode).

Usage:
    python scripts/compile.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = ROOT / "contracts"
BUILD_DIR = ROOT / "build"

SOLC_VERSION = "0.8.24"
EVM_VERSION = "shanghai"
OPTIMIZER_RUNS = 200


def standard_input() -> dict:
    """Solidity standard-JSON input covering every .sol file in contracts/."""
    sources = {
        f"contracts/{p.name}": {"content": p.read_text(encoding="utf-8")}
        for p in sorted(CONTRACTS_DIR.glob("*.sol"))
    }
    if not sources:
        sys.exit("No .sol files found in contracts/")
    return {
        "language": "Solidity",
        "sources": sources,
        "settings": {
            "optimizer": {"enabled": True, "runs": OPTIMIZER_RUNS},
            "evmVersion": EVM_VERSION,
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}},
        },
    }


def write_artifacts(output: dict) -> list[str]:
    errors = [e for e in output.get("errors", []) if e.get("severity") == "error"]
    for e in output.get("errors", []):
        print(e.get("formattedMessage", e.get("message")), file=sys.stderr)
    if errors:
        sys.exit("Compilation failed.")

    BUILD_DIR.mkdir(exist_ok=True)
    written = []
    for file_contracts in output["contracts"].values():
        for name, data in file_contracts.items():
            artifact = {
                "contractName": name,
                "abi": data["abi"],
                "bytecode": "0x" + data["evm"]["bytecode"]["object"],
                "compiler": {"solc": SOLC_VERSION, "evmVersion": EVM_VERSION, "runs": OPTIMIZER_RUNS},
            }
            (BUILD_DIR / f"{name}.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")
            written.append(name)
    return written


def main() -> None:
    import solcx

    if SOLC_VERSION not in [str(v) for v in solcx.get_installed_solc_versions()]:
        print(f"Installing solc {SOLC_VERSION} (one-time download)...")
        solcx.install_solc(SOLC_VERSION)

    output = solcx.compile_standard(standard_input(), solc_version=SOLC_VERSION)
    names = write_artifacts(output)
    print(f"Compiled {len(names)} contracts -> build/: {', '.join(sorted(names))}")


if __name__ == "__main__":
    main()
