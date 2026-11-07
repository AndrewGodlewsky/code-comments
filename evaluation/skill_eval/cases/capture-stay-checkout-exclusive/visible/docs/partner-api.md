# Partner booking API: availability (excerpt)

`POST /availability`

| field | type | meaning |
| --- | --- | --- |
| `hotel_id` | string | Partner hotel identifier |
| `checkin` | ISO date, `YYYY-MM-DD` | Arrival date. The guest sleeps there that night. |
| `checkout` | ISO date, `YYYY-MM-DD` | Departure date. The guest leaves that morning; that night is not part of the stay and is not charged. |

Example: a single night on 1 March 2026 is `checkin=2026-03-01`,
`checkout=2026-03-02`.

Stays longer than 30 nights are rejected with `422 Unprocessable Entity`.

## Integration Q&A

**Priya (us):** Our hotels span several time zones. Should we convert the dates
to UTC before sending them?

**Partner support:** No. `checkin` and `checkout` are calendar dates in the
hotel's own calendar. Send them exactly as the guest chose them, with no time
or zone attached. Converting them would shift some stays by a day.
