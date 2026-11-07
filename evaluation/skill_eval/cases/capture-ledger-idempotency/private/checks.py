"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""


def check():
    failures = []
    module = load("ledger", failures)
    if module is None:
        return failures
    ledger = module.Ledger()
    first = {"event_id": "evt-1", "account": "acct-a", "amount_cents": 500}
    expect(failures, "first delivery credits", lambda: ledger.apply(first), 500)
    expect(failures, "redelivery is ignored", lambda: ledger.apply(dict(first)), 500)
    repeat = {"event_id": "evt-2", "account": "acct-a", "amount_cents": 500}
    expect(failures, "same amount, new event_id still credits", lambda: ledger.apply(repeat), 1000)
    other = {"event_id": "evt-3", "account": "acct-b", "amount_cents": 125}
    expect(failures, "other account independent", lambda: ledger.apply(other), 125)
    expect(failures, "balances recorded", lambda: dict(ledger.balances), {"acct-a": 1000, "acct-b": 125})
    return failures
