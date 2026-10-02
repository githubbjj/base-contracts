import deploy
from eth_account import Account

from conftest import ETH, REVERT, ROOT, advance, deploy_local  # noqa: F401

def test_deploy_script_signs_and_records(w3, accts, tmp_path, monkeypatch):
    monkeypatch.setattr(deploy, "DEPLOY_DIR", tmp_path)
    acct = Account.create()
    w3.eth.send_transaction({"from": accts[0], "to": acct.address, "value": ETH})
    built = [n for n in deploy.CONTRACTS if (ROOT / "build" / f"{n}.json").exists()]
    assert built, "run scripts/compile.py first"
    for name in built:
        rec = deploy.send_deploy(w3, acct, name, deploy.CONTRACTS[name](acct.address))
        deploy.save_record("local", rec)
        assert len(w3.eth.get_code(rec["address"])) > 0
        assert rec["deployer"] == acct.address
    assert len(deploy.load_records("local")) == len(built)
