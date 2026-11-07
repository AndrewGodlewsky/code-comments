# Signup crashed for every new user (fixed in signup.py)

**From:** Ana
**Date:** 2026-10-28

I wrote the new signup handler against the `find_by_email` docstring:

```python
if store.find_by_email(form.email) is None:
    store.add(new_id(), form.email)
```

In staging every brand-new user got a 500. The traceback ended in
`users.UserNotFound`, raised from `find_by_email`. I've changed `signup.py` to
catch the exception, so production is fine, but the docstring sent me the wrong
way and the next person will hit the same thing.
