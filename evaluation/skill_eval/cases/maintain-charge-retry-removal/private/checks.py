"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""

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


def check():
    failures = []
    module = load("charges", failures)
    if module is None:
        return failures
    conn = Conn({"status": 201, "charge_id": "ch_1"})
    expect(failures, "captured charge", lambda: module.submit_charge(conn, 1250, "tok_a"), "ch_1")
    expect(failures, "request sent", lambda: conn.posts, [("/charges", {"amount": 1250, "source": "tok_a"})])

    conn = Conn(ConnectionResetError("reset by peer"), {"status": 201, "charge_id": "ch_2"})
    try:
        result = module.submit_charge(conn, 500, "tok_b")
    except module.ChargeFailed as error:
        if not isinstance(error.__cause__, ConnectionResetError):
            failures.append(f"reset: ChargeFailed cause is {error.__cause__!r}, expected the ConnectionResetError")
    except Exception as error:
        failures.append(f"reset: expected ChargeFailed, raised {type(error).__name__}: {error}")
    else:
        failures.append(f"reset: expected ChargeFailed, got {result!r}")
    expect(failures, "reset: posted exactly once", lambda: len(conn.posts), 1)
    expect(failures, "reset: no reconnect", lambda: conn.reconnects, 0)

    for status in (202, 402, 500):
        conn = Conn({"status": status, "error": "declined"})
        expect_raises(failures, f"status {status}", lambda c=conn: module.submit_charge(c, 100, "tok_c"), module.ChargeFailed)
        expect(failures, f"status {status}: posted once", lambda c=conn: len(c.posts), 1)
    return failures
