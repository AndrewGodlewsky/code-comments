"""Bounded command tool and observation ledger for trusted offline adapters."""

import hashlib
import json
import time
import uuid


DEFAULT_LIMITS = {'max_calls': 16, 'max_input_bytes': 262144, 'max_output_bytes': 1048576}


def validate_limits(limits):
    if (not isinstance(limits, dict) or set(limits) != set(DEFAULT_LIMITS)
            or any(type(value) is not int or not 0 < value <= (64 if key == 'max_calls' else 1048576)
                   for key, value in limits.items())):
        raise ValueError('invalid tool-session limits')
    return dict(limits)


class ToolSession:
    def __init__(self, sandbox, *, max_calls=16, max_input_bytes=262144, max_output_bytes=1048576):
        self.limits = validate_limits({'max_calls': max_calls, 'max_input_bytes': max_input_bytes,
                                      'max_output_bytes': max_output_bytes})
        self.sandbox = sandbox
        self.session_id = uuid.uuid4().hex
        self.observations = []
        self.input_bytes = 0
        self.output_bytes = 0
        self.terminated = False

    def execute(self, request):
        if self.terminated:
            raise ValueError('tool session terminated')
        started = time.monotonic()
        event = {'call_id': f'{self.session_id}:{len(self.observations) + 1}',
                 'request': None, 'error': None}
        try:
            encoded = json.dumps(request, ensure_ascii=False, allow_nan=False,
                                 separators=(',', ':')).encode('utf-8')
            event['request_bytes'] = len(encoded)
            event['request_sha256'] = hashlib.sha256(encoded).hexdigest()
            if self.input_bytes + len(encoded) > self.limits['max_input_bytes']:
                raise ValueError('tool input byte limit exceeded')
            self.input_bytes += len(encoded)
            event['request'] = json.loads(encoded)
            if len(self.observations) >= self.limits['max_calls']:
                raise ValueError('tool call limit exceeded')
            if (not isinstance(request, dict) or not {'command'} <= set(request) <= {'command', 'stdin'}
                    or not isinstance(request['command'], list) or not request['command']
                    or any(not isinstance(arg, str) or '\x00' in arg for arg in request['command'])
                    or not isinstance(request.get('stdin', ''), str)):
                raise ValueError('invalid command tool request')
            result = self.sandbox.run(event['request']['command'], event['request'].get('stdin', ''))
            self.output_bytes += len(result.raw)
            event.update({'output': result.output, 'output_bytes': len(result.raw),
                          'returncode': result.returncode, 'timed_out': result.timed_out,
                          'output_limited': result.output_limited,
                          'command_wall_seconds': result.elapsed_seconds})
            if self.output_bytes > self.limits['max_output_bytes']:
                raise ValueError('tool output byte limit exceeded')
            if result.timed_out or result.output_limited:
                raise ValueError('tool command timed out or exceeded output limit')
            return result
        except (OSError, RuntimeError, ValueError, TypeError) as error:
            self.terminated = True
            event['error'] = f'{type(error).__name__}: {error}'
            self.sandbox.close()
            raise ValueError(event['error']) from error
        finally:
            event['wall_seconds'] = time.monotonic() - started
            self.observations.append(event)
