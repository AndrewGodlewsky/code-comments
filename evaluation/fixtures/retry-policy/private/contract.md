# Retry-policy fixture contract

This is an original synthetic development fixture. The backend story is an
authored requirement, not a historical incident or a measured user need. All
reference answers are public development material; do not reuse this fixture
as a secret or held-out confirmation task.

## Initial contract

`resolve_retries(settings)` receives a dictionary. Missing or None `retries`
means three retries. Explicit zero disables retries. Only actual integers from
zero through five are valid; reject booleans, floats, strings and out-of-range
values with ValueError. The legacy backend's maximum is five. Retries count
additional operations after the initial operation. Invalid argument containers
are outside this fixture's contract.

The agent initially receives only the implementation, first edit request and
condition-specific facts. The absence of some explanatory facts in the baseline
is intentional. No condition gets later requirements before their step. The
same hand-derived behavioral checks apply to every condition.

## Evolution

The step requests own newly available information. Step 1 adds override precedence
while preserving explicit zero and None fallback. Step 2 retires the five-retry
limit in favor of eight; no prior zero/default/type requirement is retired.
Step 3 adds bounded delays and retains the step 2 upper bound. `valid_until` is
exclusive: a fact with value 2 is obsolete when step 2's request arrives.

This fixture checks evaluator plumbing. Much of its knowledge is recoverable
from code or task requests, so it is not a representative test of historical
rationale, global architecture, model capability, or documentation replacement.
