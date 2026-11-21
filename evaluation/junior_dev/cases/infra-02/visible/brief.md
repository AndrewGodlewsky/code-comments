# Release pipeline for shop-api

Today shop-api reaches staging and production when someone runs `existing/deploy.sh` from a laptop. CI only builds and unit-tests pull requests. Read `existing/deploy.sh` and `existing/environments.md` before you start. The pipeline must call that script and keep the state it already keeps, not replace them.

**Goal:** every merge to `main` can reach production through automated gates plus one human approval, with no laptop deploys.

**Fixed requirements**

- Pull requests keep today's behaviour: build and unit tests, never a deploy.
- A merge to `main` starts the full pipeline. The image is built once per run, tagged with the commit SHA and pushed to the registry. Staging and production deploy that same image. Nothing is rebuilt after the tests.
- Unit and integration tests run in parallel after the build, and both must pass. Integration tests get one automatic retry because of a known flaky test. Unit tests get none. A test failure ends the run.
- Staging deploys automatically with `deploy.sh staging <tag>`, then smoke tests run against it. If smoke tests fail, run `deploy.sh rollback staging` and end the run.
- Next comes a manual approval. Only the `release-approvers` group may approve, and never the author of the merged commit. If nobody approves within 72 hours, the run expires and nothing goes to production.
- A production deploy may only start inside the deployment window defined in `existing/environments.md`, and only one production deploy may be in progress at a time.
- Production is canary first: `deploy.sh canary <tag>`, then watch the canary for 15 minutes. If its 5xx rate goes above 1% at any point, run `deploy.sh canary-off` and fail the run. Otherwise roll the stable deployment with `deploy.sh production <tag>`, then remove the canary.
- Failures, expiries and finished production deploys are announced in #deploys.

Everything not fixed above is yours to decide, including how runs behave when several merges are in flight and how the canary is measured. Whatever you choose, show it.

**Deliverable:** a Mermaid flowchart of the pipeline, from pull request and merge through to production, with short notes before or after it. Your readers have never seen this repo or the script. Make each step's trigger, what it reads or writes, and its failure path visible, and carry over anything from the existing files that readers need.
