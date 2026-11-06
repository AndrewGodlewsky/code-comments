# Add a request override

Extend `resolve_retries(settings, override=None)` so that a non-None override
takes precedence over the settings value. None means use settings as before.
Validate the selected value, not the unused settings value. Preserve the existing
default, type/range rules and zero behavior. Keep the function in `policy.py`.
