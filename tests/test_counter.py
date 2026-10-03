import pytest  # noqa: F401
from web3 import Web3  # noqa: F401
from conftest import ETH, REVERT, ROOT, advance, deploy_local  # noqa: F401


def test_counter(w3, accts):
    c = deploy_local(w3, "Counter")
    c.functions.increment().transact({"from": accts[1]})
    c.functions.increment().transact({"from": accts[1]})
    c.functions.decrement().transact({"from": accts[1]})
    assert c.functions.count().call() == 1
    with pytest.raises(REVERT):
        c.functions.reset().transact({"from": accts[1]})
    c.functions.reset().transact({"from": accts[0]})
    assert c.functions.count().call() == 0
