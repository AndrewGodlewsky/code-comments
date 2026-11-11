# Notes for agents

- Run `python -m unittest discover -s tests -t .` before you finish.
- Money is always `Decimal`, never `float`.
- Invoice totals round half-up, never half-even: the e-invoice validator rejects half-even totals (FIN-88).
- Keep changes small and match the existing style.
