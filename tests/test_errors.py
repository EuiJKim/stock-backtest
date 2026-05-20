import pytest
from live.errors import (TraderError, SafetyError, BrokerError,
                          CredentialsError, StateError)


def test_all_inherit_trader_error():
    assert issubclass(SafetyError, TraderError)
    assert issubclass(BrokerError, TraderError)
    assert issubclass(CredentialsError, TraderError)
    assert issubclass(StateError, TraderError)


def test_can_raise_and_catch_as_trader_error():
    with pytest.raises(TraderError):
        raise SafetyError("test")
