## Recommendations API: serving, model versions and shadow testing

We are putting our recommendation model behind an API that the home page calls. Today, recommendations are precomputed each night into a table. We want them computed for each request so they use the latest features. Please plan how this works end to end, including how we try a new model version in shadow before we switch to it.

**Fixed requirements**

- Endpoint: `GET /recommendations?user_id=...` returns 20 item IDs. The p99 latency budget for the whole call is 150 ms.
- Features come from an online feature store, a key-value store keyed by user ID. A materialization job copies them from the warehouse into the online store every hour.
- The online feature lookup gets 30 ms. If it times out, or the user has no features, we do not call the model. We return the popular-items list instead (recomputed daily) and mark the response as a fallback.
- If materialization fails, keep serving the features already in the store, up to 6 hours old. Features older than 6 hours count as missing.
- Every trained model is registered in the model registry as an immutable, numbered version. Exactly one version is active at a time. Switching the active version must not need a redeploy of the API, and a rollback must take effect within 1 minute.
- A candidate version runs in shadow on a copy of the traffic for 10% of users. Users are chosen by user ID, so a given user is always in or always out. Shadow output is never shown to a user, and nothing that goes wrong in shadow may slow down or break the user's response.
- A candidate can depend on features the active model does not use. It must never run, in shadow or as the active version, against features the online store does not have.
- A candidate can become active only after at least 7 days in shadow, with an error rate under 0.5% and p99 inference latency under 80 ms, and only after the ML lead approves.

**Not decided**

Product has not decided yet whether a live A/B test (showing the candidate's recommendations to a slice of real users) comes between shadow and the full switch, or whether we go straight from shadow to 100%. Don't choose either option. Plan around the gap.

**What I want**

A numbered, step-by-step plan in Markdown. For each step, say what starts it, what data moves, where the state lives and what happens on failure. Cover the request path, feature freshness, model versions and switching, running shadow and comparing results, promotion and rollback.
