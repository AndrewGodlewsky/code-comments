"""Hidden checks for the reader step. `load`, `expect`, `expect_raises` are injected by check_runner."""

import json


class Conn:
    def __init__(self, *outcomes):
        self.outcomes, self.posts, self.reconnects = list(outcomes), [], 0

    def post(self, path, body):
        self.posts.append((path, json.loads(body)))
        outcome = self.outcomes.pop(0) if self.outcomes else {"status": 500, "error": "no scripted response"}
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def reconnect(self):
        self.reconnects += 1


def reset_raises(failures, module, label, call, conn, keep_cause):
    try:
        result = call()
    except module.ChargeFailed as error:
        if keep_cause and not isinstance(error.__cause__, ConnectionResetError):
            failures.append(f"{label}: ChargeFailed cause is {error.__cause__!r}, expected the ConnectionResetError")
    except Exception as error:
        failures.append(f"{label}: expected ChargeFailed, raised {type(error).__name__}: {error}")
    else:
        failures.append(f"{label}: expected ChargeFailed, got {result!r}")
    expect(failures, f"{label}: posted exactly once (no resend: the charge may already have landed)", lambda: len(conn.posts), 1)


def check():
    failures = []
    module = load("charges", failures)
    if module is None:
        return failures
    if not hasattr(module, "renew_subscription"):
        return failures + ["charges.renew_subscription is missing"]

    # New behaviour: renewals.
    conn = Conn({"status": 201, "charge_id": "ch_r1"})
    expect(failures, "renewal captured", lambda: module.renew_subscription(conn, 1999, "cus_1"), "ch_r1")
    expect(failures, "renewal request", lambda: conn.posts, [("/charges", {"amount": 1999, "customer": "cus_1"})])

    conn = Conn(ConnectionResetError("reset by peer"), {"status": 201, "charge_id": "ch_r2"})
    reset_raises(failures, module, "renewal reset", lambda: module.renew_subscription(conn, 1999, "cus_2"), conn, keep_cause=False)
    conn = Conn(ConnectionResetError("reset by peer"), ConnectionResetError("reset by peer"), {"status": 201, "charge_id": "ch_r3"})
    reset_raises(failures, module, "renewal repeated resets", lambda: module.renew_subscription(conn, 1999, "cus_3"), conn, keep_cause=False)

    for status in (202, 402, 500):
        conn = Conn({"status": status, "error": "declined"})
        expect_raises(failures, f"renewal status {status}", lambda c=conn: module.renew_subscription(c, 100, "cus_4"), module.ChargeFailed)
        expect(failures, f"renewal status {status}: posted once", lambda c=conn: len(c.posts), 1)

    # Step-1 behaviour must not regress.
    conn = Conn({"status": 201, "charge_id": "ch_1"})
    expect(failures, "card charge captured", lambda: module.submit_charge(conn, 1250, "tok_a"), "ch_1")
    expect(failures, "card charge request", lambda: conn.posts, [("/charges", {"amount": 1250, "source": "tok_a"})])
    conn = Conn(ConnectionResetError("reset by peer"), {"status": 201, "charge_id": "ch_2"})
    reset_raises(failures, module, "card charge reset", lambda: module.submit_charge(conn, 500, "tok_b"), conn, keep_cause=True)
    expect(failures, "card charge reset: no reconnect", lambda: conn.reconnects, 0)
    for status in (202, 402, 500):
        conn = Conn({"status": status, "error": "declined"})
        expect_raises(failures, f"card charge status {status}", lambda c=conn: module.submit_charge(c, 100, "tok_c"), module.ChargeFailed)
    return failures
