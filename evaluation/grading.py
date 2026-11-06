"""Keep expected outcomes on the host; execute candidate functions only in Docker."""

import json
import time

from evaluation.sandbox import DockerSandbox, IMAGE


CALL_SCRIPT = """import contextlib,json,os,runpy,sys
requests=json.load(sys.stdin)
required_error=ValueError
is_expected=isinstance
value_type=type
integer_type=int
list_type=list
results=[]
with open(os.devnull,'w') as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
 try:
  namespace=runpy.run_path('/workspace/policy.py')
  for request in requests:
   try:
    value=namespace[request['function']](**request['arguments'])
    valid=(value_type(value) is integer_type if request['function']=='resolve_retries' else value_type(value) is list_type and all(value_type(item) is integer_type for item in value))
    results.append({'value':value} if valid else {'invalid_return_type':value_type(value).__name__})
   except BaseException as error:
    results.append({'exception':'ValueError' if is_expected(error,required_error) else 'unexpected:'+value_type(error).__name__})
 except BaseException as error: results={'load_error':type(error).__name__}
print(json.dumps(results,allow_nan=False))
"""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate result key")
        result[key] = value
    return result


def compare_results(output: str, expected: list[dict]) -> list[str]:
    try:
        actual = json.loads(output, object_pairs_hook=_unique_object)
        if not isinstance(actual, list) or len(actual) != len(expected):
            return ["missing, extra or malformed call results"]
        failures = []
        for index, (observed, wanted) in enumerate(zip(actual, expected)):
            if json.dumps(observed, sort_keys=True, allow_nan=False) != json.dumps(wanted, sort_keys=True):
                failures.append(f"call {index}: expected {wanted!r}, got {observed!r}")
        return failures
    except (ValueError, TypeError):
        return ["invalid result protocol"]


def _cases(step: int) -> list[tuple[dict, dict]]:
    if type(step) is not int or step not in (0, 1, 2, 3):
        raise ValueError("step must be 0, 1, 2 or 3")
    cases = []

    def add(function, arguments, value=None, invalid=False):
        expected = {"exception": "ValueError"} if invalid else {"value": value}
        cases.append(({"function": function, "arguments": arguments}, expected))

    maximum = 5 if step < 2 else 8
    for settings in ({}, {"retries": None}):
        add("resolve_retries", {"settings": settings}, 3)
    for value in range(maximum + 1):
        add("resolve_retries", {"settings": {"retries": value}}, value)
        if step:
            add("resolve_retries", {"settings": {"retries": "unused"}, "override": value}, value)
    for value in (True, False, -1, maximum + 1, "2", 1.5, 3.0):
        add("resolve_retries", {"settings": {"retries": value}}, invalid=True)
        if step:
            add("resolve_retries", {"settings": {"retries": 2}, "override": value}, invalid=True)
    if step:
        add("resolve_retries", {"settings": {}, "override": None}, 3)
        add("resolve_retries", {"settings": {"retries": 0}, "override": None}, 0)
    if step == 3:
        for value, delays in ((0, []), (1, [1]), (2, [1, 2]), (3, [1, 2, 4]), (5, [1, 2, 4, 4, 4]), (8, [1, 2, 4, 4, 4, 4, 4, 4])):
            add("retry_delays", {"settings": {"retries": value}}, delays)
            add("retry_delays", {"settings": {"retries": 5}, "override": value}, delays)
        add("retry_delays", {"settings": {}, "override": None}, [1, 2, 4])
        for value in (True, False, -1, 9, "2", 1.5, 3.0):
            add("retry_delays", {"settings": {"retries": value}}, invalid=True)
            add("retry_delays", {"settings": {}, "override": value}, invalid=True)
    return cases


def grade(files: dict[str, str], step: int, *, image: str = IMAGE, timeout: float = 10) -> dict:
    cases = _cases(step)
    started = time.monotonic()
    with DockerSandbox(files, image=image, timeout=timeout) as sandbox:
        result = sandbox.run(["python", "-I", "-B", "-c", CALL_SCRIPT], json.dumps([request for request, _ in cases]))
    failures = compare_results(result.output, [expected for _, expected in cases])
    if result.returncode or result.timed_out or result.output_limited:
        failures.append("candidate execution failed, timed out or exceeded output limit")
    return {
        "passed": not failures,
        "checked_cases": len(cases),
        "failures": failures,
        "candidate_output": result.output,
        "timed_out": result.timed_out,
        "output_limited": result.output_limited,
        "wall_seconds": time.monotonic() - started,
    }
