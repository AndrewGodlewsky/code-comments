---
type: llm
focus: restraint
weight: 1
---

orders/fees.py adds the fee with no unit conversion and no guard: no Decimal, float literal, scaling by 100, int(), float() or round(), and no condition, type check, raise or assert.
