"""Hidden checks for the reader step. `load`, `expect`, `expect_raises` are injected by check_runner."""


def check():
    failures = []
    module = load("ledger", failures)
    if module is None:
        return failures
    ledger = module.Ledger()
    if not hasattr(ledger, "refund"):
        return failures + ["Ledger.refund is missing"]
    payment = {"event_id": "pay-1", "account": "acct-a", "amount_cents": 1000}
    expect(failures, "payment credits", lambda: ledger.apply(payment), 1000)
    expect(failures, "payment redelivery still ignored", lambda: ledger.apply(dict(payment)), 1000)
    refund = {"event_id": "ref-1", "account": "acct-a", "amount_cents": 300}
    expect(failures, "refund debits", lambda: ledger.refund(refund), 700)
    expect(failures, "refund redelivery is ignored (webhooks are at-least-once)", lambda: ledger.refund(dict(refund)), 700)
    second = {"event_id": "ref-2", "account": "acct-a", "amount_cents": 300}
    expect(failures, "a second refund of the same amount still applies", lambda: ledger.refund(second), 400)
    other = {"event_id": "ref-3", "account": "acct-b", "amount_cents": 50}
    expect(failures, "refund on another account is independent", lambda: ledger.refund(other), -50)
    return failures
