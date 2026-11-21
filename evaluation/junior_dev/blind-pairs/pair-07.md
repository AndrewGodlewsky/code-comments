# Pair 07

Which document would a smart engineer who does not know this project understand faster and more correctly?

---

# Document A

## shop-api release pipeline

Today a person runs `deploy.sh` from a laptop, and the script records the live tags in SSM Parameter Store. The pipeline makes CI run the same `deploy.sh` calls, so SSM stays the one record of what is live. Every merge to `main` builds one image, tests it, deploys it to staging, waits for one human approval, and rolls it out to production behind a 15-minute canary (a small second deployment that takes 10% of traffic). The gates run in this order so production only gets a build that passed the tests, ran on staging and was approved. Any failure ends the run and is posted to #deploys.

## Terms

- **CI**: the automation service that runs builds, tests and jobs. It holds the credentials for the registry, the clusters and SSM.
- **Merge commit**: the commit on `main` that a merged pull request creates. Its full SHA is the image tag.
- **Run**: one pipeline execution, started by one merge and keyed by its merge commit SHA.
- **Image**: the packaged shop-api container, stored at `registry.internal/shop-api`. Its tag is the full commit SHA.
- **Migration**: a change to the database schema. Migrations only go forward, with no undo step, and each must also work with the previous image.
- **deploy.sh**: the existing script. Modes: `staging`, `production`, `canary`, `canary-off`, `rollback`. The `staging`, `production` and `canary` modes run the migrations first.
- **Kubernetes**: the system that runs containers in clusters. A **deployment** keeps identical pods (running copies of the container) on the image it is told to run. A **rollout** replaces its pods with the new image. A **context** names the cluster a command targets. All deploys use namespace `shop`.
- **Staging**: Kubernetes context `staging`, with its own Postgres. Internal only.
- **Stable deployment**: `shop-api` on the `production` context. It serves production traffic.
- **Canary**: `shop-api-canary`, a second production deployment that normally has 0 pods. With 2 ready pods, the load balancer (the component that spreads requests across pods) sends it 10% of traffic. Stable and canary share the production Postgres.
- **SSM tags**: two values per environment in AWS Parameter Store, a key-value store. `current_tag` names what runs. `previous_tag` names what ran before. `deploy.sh` writes them only after a rollout succeeds. The canary is never recorded.
- **kubectl rollout undo**: returns a Kubernetes deployment to its previous revision. It does not change SSM tags.
- **Named lock**: a CI lock that only one run can hold at a time. The pipeline uses `staging-deploy` and `production-deploy`.
- **Manual approval job**: a CI job that pauses a run until a person approves it. CI records who approved and when.
- **release-approvers**: the CI group allowed to approve production.
- **Deployment window**: a production deploy may start Monday to Thursday, 09:00 to 15:00 UTC.
- **Unit tests**: `make test-unit`, about 4 minutes.
- **Integration tests**: `make test-integration`, about 12 minutes, with a Postgres service container. One test is known to be flaky.
- **Smoke tests**: `make smoke ENV=staging`, about 3 minutes, against the staging URL.
- **5xx rate**: the share of requests answered with a server error (HTTP 500 to 599). Prometheus, the metrics store, records it.
- **Superseded**: cancelled because a newer run took `staging-deploy`.
- **HOLD**: a run that stopped while it still holds a lock.

## Flow

```mermaid
flowchart TD
    subgraph PR["Pull request (unchanged)"]
        PR1["PR opened or updated"] --> PR2["Build image, not pushed"]
        PR2 --> PR3["Unit tests: make test-unit"]
        PR3 --> PR4["Result on the PR, nothing deployed"]
    end

    M["Merge to main starts a run"] --> B["Build image once<br/>tag = merge commit SHA"]
    B -->|build fails| FAIL["Run ends<br/>post to deploys channel"]
    B --> PUSH["Push to registry.internal/shop-api:SHA"]
    PUSH --> UT["Unit tests<br/>no retry"]
    PUSH --> IT["Integration tests<br/>one automatic retry"]
    UT -->|fails| FAIL
    IT -->|fails after retry| FAIL
    UT -->|pass| BOTH["Both suites passed<br/>join waits for both"]
    IT -->|pass| BOTH
    BOTH --> SL["Take staging-deploy lock<br/>waits while held"]
    SL -->|lock taken| STG["deploy.sh staging SHA<br/>migrate, set image, rollout, write staging tags"]
    STG -->|migrate fails| FAIL
    STG -->|rollout fails| UNDO_S["kubectl rollout undo on staging"]
    UNDO_S -->|ok| FAIL
    UNDO_S -->|fails| HOLD
    STG -->|ok| SMOKE["Smoke tests: make smoke ENV=staging"]
    SMOKE -->|fail| RB_S["deploy.sh rollback staging<br/>image and current_tag back to previous_tag"]
    RB_S -->|ok| FAIL
    RB_S -->|fails| HOLD
    SMOKE -->|pass, staging-deploy released| APP{"Approval by release-approvers<br/>not the commit author, 72 h"}
    APP -->|rejected| FAIL
    APP -->|no answer in 72 h| EXP["Run expires<br/>nothing reaches production<br/>post to deploys channel"]
    APP -->|approved| WIN{"Inside window?<br/>Mon to Thu, 09:00 to 15:00 UTC"}
    WIN -->|no| WAITW["Wait for next window<br/>holds no lock"]
    WAITW --> WIN
    WIN -->|yes| PL["Take production-deploy lock<br/>waits while held"]
    PL --> CAN["deploy.sh canary SHA<br/>migrate, canary 2 pods, 10 percent of traffic, rollout wait 300 s"]
    CAN -->|migrate or rollout fails| COFF1["deploy.sh canary-off"]
    COFF1 -->|ok| FAIL
    COFF1 -->|fails| HOLD
    CAN -->|ok| WATCH{"15 min watch<br/>5xx ratio checked every 30 s from minute 1"}
    WATCH -->|above 1% or no data or query error| COFF2["deploy.sh canary-off"]
    COFF2 -->|ok| FAIL
    COFF2 -->|fails| HOLD
    WATCH -->|15 min clean| PROD["deploy.sh production SHA<br/>migrate no-op, stable rollout, write production tags"]
    PROD -->|rollout fails, tags not written| UNDO_P["kubectl rollout undo on production"]
    UNDO_P -->|ok| COFF3["deploy.sh canary-off"]
    UNDO_P -->|fails| HOLD
    COFF3 -->|ok| FAIL
    COFF3 -->|fails| HOLD
    PROD -->|ok| COFF_OK["deploy.sh canary-off<br/>remove canary"]
    COFF_OK -->|ok| DONE["Production deploy finished<br/>post to deploys channel"]
    COFF_OK -->|fails| HOLD
    HOLD["Run stops, lock kept<br/>a person checks the cluster<br/>post to deploys channel"]
    APP -. "newer run takes staging-deploy" .-> SUP["Cancelled as superseded<br/>no post"]
    WIN -. "newer run takes staging-deploy" .-> SUP
    PL -. "newer run takes staging-deploy" .-> SUP
```

A run that ends normally releases the locks it holds. Only HOLD keeps them. Dotted lines are waiting runs being cancelled as superseded.

## Steps

1. **Pull request (unchanged).** Trigger: a PR is opened or updated. CI builds the image without pushing it and runs `make test-unit`. Results appear on the PR. Nothing is pushed or deployed.
2. **Merge starts a run.** Trigger: a merge to `main`. Each merge gets its own run, keyed by its merge commit SHA. "Older" and "newer" mean merge order.
3. **Build and push.** Trigger: the run starts. CI builds one image from the merge commit, tags it with the full SHA and pushes it to `registry.internal/shop-api`. Nothing is rebuilt later. The push happens before the tests, so a failed run can leave an unused tag, which nothing deploys. If the build fails, the run ends and is posted.
4. **Tests in parallel.** Trigger: the push succeeded. Both suites start at once, and both must pass.
   - Unit tests get no retry.
   - Integration tests get one automatic retry, two attempts at most, because of the known flaky test.
   - Any failure ends the run and cancels the other suite if it is still running. If unit tests pass while integration is still retrying, the run waits for integration. Staging does not start until both pass.
5. **Staging deploy.** Trigger: both suites pass. The run takes `staging-deploy`, waiting if it is held. The CI job holding the lock runs `deploy.sh staging <SHA>` with CI's credentials. The script migrates the staging database, sets the image, waits up to 300 seconds for the rollout, and writes the staging SSM tags.
   - Migration fails: the run ends. The migration may be partly applied, but it still works with the old image, and the tags are unchanged. The lock is released.
   - Rollout fails: run `kubectl rollout undo` on staging, then end the run. The tags were not written, so SSM still names the old tag, which undo returns to. The lock is released. If undo fails, the run goes to HOLD.
6. **Staging smoke tests.** Trigger: step 5 succeeded. Run `make smoke ENV=staging`.
   - Pass: the run releases `staging-deploy` and moves to approval.
   - Fail: run `deploy.sh rollback staging`. It sets the image back to `previous_tag` and writes `current_tag` back to it. The tags were already written in step 5, so rollback is the right tool. The run ends and is posted. The lock is released when rollback finishes. If rollback fails, the run goes to HOLD.
7. **Approval.** Trigger: step 6 passed. A manual approval job restricted to `release-approvers` pauses the run. CI records who approved and when. The author of the merge commit may not approve. The 72-hour timer starts here.
   - Approved: go to step 8.
   - Rejected: the run ends and is posted. Staging keeps its tag.
   - No answer within 72 hours: the run expires, nothing goes to production, and it is posted.
8. **Deployment window.** Trigger: approval. The run checks the window, Monday to Thursday, 09:00 to 15:00 UTC. Outside it, the run waits and holds no lock. Inside it, the run goes to step 9. The canary must start inside the window. Once started, the deploy may finish after 15:00 UTC.
9. **Canary deploy.** Trigger: the window is open. The run takes `production-deploy`, waiting if it is held, and keeps it until step 11 ends. It runs `deploy.sh canary <SHA>`. The script migrates the production database, which stable and canary share. It sets `shop-api-canary` to the image, scales it to 2 pods (10% of traffic), and waits up to 300 seconds for the rollout.
   - Migration or rollout fails: run `deploy.sh canary-off`, end the run and post it. Stable is unchanged. The lock is released. If canary-off fails, the run goes to HOLD.
10. **Canary watch.** Trigger: the canary rollout is ready. For 15 minutes, from minute 1 to minute 15, the run checks the canary 5xx rate every 30 seconds. The first check waits one minute, because the query covers the last minute of traffic and a new canary has none yet. The query is in Notes.
    - Any check above 1%, with no data, or where the query fails (for example, Prometheus is unreachable): run `deploy.sh canary-off`, end the run and post it. Stable is unchanged. A failed query counts as a failed check, because the canary cannot be shown to be under 1%.
    - This step never touches the stable deployment.
11. **Promotion.** Trigger: 15 clean minutes. The run runs `deploy.sh production <SHA>`. Its migration is a no-op, because step 9 already applied it. The script sets the stable image, waits up to 300 seconds for the rollout, and writes the production tags. The canary keeps its 2 pods and its 10% share for the whole rollout, because this step changes only stable. Both run the same tag.
    - Stable rollout fails: run `kubectl rollout undo` on production, then `deploy.sh canary-off`. The tags were not written, so undo returns to the running tag. The run ends and is posted. The lock is released. If either command fails, the run goes to HOLD.
    - Success: run `deploy.sh canary-off` to remove the canary, release `production-deploy`, and post the result to #deploys. If canary-off fails, the run goes to HOLD.

## What happens when things fail

| When | What the run does | What is left behind | Lock | Who is told |
|---|---|---|---|---|
| Build fails | Run ends | Nothing deployed | None held | #deploys |
| Unit tests fail | Run ends; integration tests cancelled if running | Nothing deployed | None held | #deploys |
| Integration tests fail twice | Run ends; unit tests cancelled if running | Nothing deployed | None held | #deploys |
| Staging migration fails | Run ends | Migration may be partly applied; still works with the old image; tags unchanged | Released | #deploys |
| Staging rollout fails | `kubectl rollout undo` on staging; run ends | SSM still names the old tag | Released | #deploys |
| Staging smoke tests fail | `deploy.sh rollback staging`; run ends | Staging on `previous_tag` | Released after rollback | #deploys |
| Approval rejected | Run ends | Staging keeps its tag | None held | #deploys |
| No approval within 72 hours | Run expires | Staging keeps its tag; production unchanged | None held | #deploys |
| Canary migration or rollout fails | `deploy.sh canary-off`; run ends | Stable unchanged | Released | #deploys |
| Canary 5xx above 1%, no data, or query error | `deploy.sh canary-off`; run ends | Stable unchanged | Released | #deploys |
| Production stable rollout fails | `kubectl rollout undo` on production, then `canary-off`; run ends | SSM still names the old tag | Released | #deploys |
| Run superseded | Run cancelled | Nothing | None held | Nothing posted |
| `kubectl rollout undo`, `rollback` or `canary-off` command fails | Run stops | Cluster state not known; a canary may still take 10% of traffic | Kept until a person releases it | #deploys; a person checks the cluster |

## Rules when several merges are in flight

- Build and tests run for every merge at the same time.
- Each named lock is held by one run at a time. Other runs wait for it and are not failed.
- When a run takes `staging-deploy`, every older run that has not started its canary is cancelled. This covers runs still testing, waiting for `staging-deploy`, waiting for approval, waiting for the window, or waiting for `production-deploy`. Production should receive only the newest approved build, because an older approval would be stale.
- A run holding `staging-deploy` is never cancelled. A newer run can take that lock only after the holder releases it, so the holder finishes its smoke tests or rollback first.
- A run in canary or production is never cancelled. It finishes. Finishing a canary or production run cancels nothing.
- A run waiting for `production-deploy` keeps waiting. It is cancelled only when a newer run takes `staging-deploy`.
- Only a run that passed both suites can take `staging-deploy`, so only it can cancel older runs. A newer run that fails its tests, or never reaches `staging-deploy`, cancels nothing, and an older approved run stays valid.
- A cancelled run is not posted to #deploys, because a cancel is not a failure. It holds no lock at that moment.
- At most one run waits for approval at a time.

## Notes

- Migrations are forward-only, and nothing undoes them. Rollback changes the image and `current_tag`, not the schema.
- Choosing the undo: before the SSM tags are written, `current_tag` still names the running tag, so `kubectl rollout undo` returns the deployment to it. After they are written, `deploy.sh rollback` is correct. Rollback before the tags are written would go to `previous_tag`, one step too far back. A failed migration needs no undo, because the image did not change. A canary failure only calls `canary-off`, because the canary never changes stable.
- `deploy.sh rollback` does not change `previous_tag`, so a second rollback goes to the same tag again.
- After a staging rollback, staging runs `previous_tag`, the build it ran before this run. That build was cancelled for approval but stays on staging until the next deploy. The next deploy reads `current_tag`, which now names that build, and writes it to `previous_tag`, so the tags stay correct. The cancelled build can be restored to staging but cannot be approved.
- A run stopped in HOLD does not resume. Its later steps assume a cluster state nobody has checked, so a person decides the next step. Other runs wait while the lock is held. Starting again needs a new run.
- No data means the query returns no value for the last minute, which happens when the canary served no requests in that minute. That check fails the run, because a canary with no traffic cannot be shown healthy.
- The canary 5xx ratio, measured over the last minute:

```
sum(rate(http_requests_total{app="shop-api-canary",code=~"5.."}[1m]))
/ sum(rate(http_requests_total{app="shop-api-canary"}[1m]))
```

## Setup (outside a run)

- CI needs a manual approval job restricted to `release-approvers`, which records the approver and time.
- CI needs the named locks `staging-deploy` and `production-deploy`.
- Integration tests need a Postgres service container.
- CI needs push access to `registry.internal/shop-api`, and credentials to run `deploy.sh` against both clusters.

## Open questions

- The order in which runs get a named lock is not stated. We assume first come, first served.
- It is not stated whether CI can stop the commit author from approving. If it cannot, the approval job needs a manual check.
- The window rule says a production deploy may start in the window. This plan treats the canary start as the start, so promotion may finish after 15:00. The team should confirm this.
- An approval given outside the window waits with no time limit, and stays valid until the run is superseded. The team should confirm this.
- `deploy.sh rollback` does not change `previous_tag` (see Notes).
- After production is promoted, the pipeline has no automatic path back. How to roll back a bad production build is not defined.
- No data fails the run. At low canary traffic, one quiet minute fails a healthy canary. The team may want a minimum request count.
- Who checks the cluster after a HOLD, who releases a held lock, and how a stopped run is started again are not defined. A manual re-run is not defined either.
- No time limit is set for a held lock, or for runs waiting on it.
- Which CI credentials or roles run `deploy.sh` and read SSM for each cluster is not stated.

---

# Document B

## shop-api CI/CD

Today, a person deploys shop-api by hand from a laptop, running `existing/deploy.sh`. This pipeline runs that same script from CI instead. Every merge to `main` can reach production after automated checks and one human approval. The image is built once and never rebuilt. The live state stays where the script already keeps it, in SSM Parameter Store (AWS's key-value store for settings).

**Terms used below**

- **Run**: one pipeline execution, started by one merge to `main`.
- **SHA**: the commit's unique ID. The pipeline also uses it as the image tag, the label that names one built image.
- **Image**: the packaged shop-api program (a container image) that Kubernetes runs.
- **Kubernetes, cluster, pod, deployment**: Kubernetes runs programs on clusters. Each cluster is named by a context (`staging` or `production`). Inside it, the namespace `shop` holds the shop-api objects. A **pod** is a running copy of the image. A **deployment** is the object that keeps the right number of pods running for one image tag. `kubectl` is the command-line tool that talks to a cluster.
- **Deploy**: telling a deployment to run a given image tag. `deploy.sh` also runs migrations first.
- **Rollout**: Kubernetes replaces old pods with new ones and waits until they are ready. `rollout status` waits up to 300 seconds and fails if the new pods are not ready by then.
- **Rollout undo**: `kubectl rollout undo` switches a deployment back to its previous ReplicaSet (the set of pods that ran before the failed rollout). It does not change any SSM value.
- **Migration**: a change to the database schema, such as a new column. `deploy.sh` runs pending migrations before it changes the image. Migrations only move forward. There is no down step, and nothing in the pipeline undoes one.
- **Stable**: the `shop-api` deployment that serves production traffic.
- **Canary**: `shop-api-canary`, a second production deployment that normally has zero pods. While it has ready pods, the load balancer (the component that spreads incoming traffic across pods) sends it 10 percent of production traffic. It shares the production database with stable.
- **SSM**: AWS Parameter Store. For each environment it holds `/deploy/<env>/current_tag` (the tag stable runs) and `/deploy/<env>/previous_tag` (the tag stable ran before that). The canary is never recorded there.
- **Registry**: `registry.internal/shop-api`, where built images are stored under their tags.
- **Lock**: a named CI lock. Only one run can hold a given lock at a time. A run releases its locks when it ends.
- **Smoke tests**: a short set of checks (`make smoke ENV=staging`, about 3 minutes) that call the staging URL after a deploy.
- **5xx error**: an HTTP response code from 500 to 599, meaning the server failed to handle a request. The canary's 5xx ratio is the share of its requests that failed this way.
- **Prometheus**: the metrics system that records request counts and error counts, and that the canary check queries.
- **Deployment window**: Monday to Thursday, 09:00 to 15:00 UTC. A production deploy may start only inside it. Once started, it may finish after 15:00.
- **Supersede**: cancel an older run that is still waiting, because a newer run has been approved. The cancelled run is announced.
- **Announce**: post a message to the Slack channel #deploys.

**In order, in plain words**

1. A pull request runs the build and unit tests. It never deploys.
2. Merging to `main` starts a run. The run builds the image once, tagged with the SHA.
3. Unit tests and integration tests run in parallel. Both must pass. Integration tests get one automatic retry, because one of them is known to be flaky. Unit tests get no retry. Any final failure ends the run.
4. The image is pushed to the registry.
5. The run deploys the image to staging, then runs smoke tests. If a smoke test fails, the run rolls staging back and ends.
6. A person in the `release-approvers` group (not the author of the merged commit) approves the run. Approval must come within 72 hours.
7. If the approval came outside the deployment window, the run waits for the next window to open.
8. Production receives the image as a canary, which takes 10 percent of traffic. The run checks the canary's 5xx ratio every 30 seconds for 15 minutes. If any reading is above 1 percent, the run turns the canary off and ends.
9. If the canary stays healthy, the stable deployment moves to the same image and the canary is turned off and removed.
10. The result is announced in #deploys.

**How to read the diagram.** Rectangles are steps. Diamonds are decisions. The text on each arrow is the outcome that takes that path. Failures that end a run, expiries, and finished production deploys are announced in #deploys. Pull request failures are reported on the pull request only.

```mermaid
flowchart TD
    pr_start["Pull request opened or updated"] --> pr_build["Build image<br/>not pushed"]
    pr_build --> pr_unit["Unit tests<br/>make test-unit"]
    pr_unit -->|pass| pr_ok["PR check passes<br/>nothing deployed"]
    pr_unit -->|fail| pr_fail["PR check fails<br/>nothing deployed"]

    merge["Merge to main<br/>starts a run"] --> build["Build image once<br/>tag = commit SHA"]
    build --> unit["Unit tests<br/>make test-unit<br/>no retry"]
    build --> integ["Integration tests<br/>make test-integration<br/>Postgres service container"]
    unit -->|fail| fail_test["Run ends<br/>announce"]
    unit -->|pass| both["Both suites passed"]
    integ -->|pass| both
    integ -->|fail, first time| retry["Retry integration tests once"]
    retry -->|pass| both
    retry -->|fail| fail_test
    both --> push["Push image<br/>registry.internal/shop-api:SHA"]

    push --> lock_s["Take staging lock"]
    lock_s --> stg["deploy.sh staging SHA<br/>reads staging current_tag from SSM<br/>migrate, set image, wait for rollout<br/>then write SSM previous_tag and current_tag"]
    stg -->|rollout fails| undo_s["kubectl rollout undo<br/>staging shop-api<br/>SSM not changed"]
    undo_s --> fail_s["Run ends<br/>release staging lock<br/>announce"]
    stg -->|rollout ok| smoke["make smoke ENV=staging<br/>about 3 min"]
    smoke -->|fail| rb_s["deploy.sh rollback staging<br/>image back to previous_tag"]
    rb_s --> fail_s
    smoke -->|pass| unlock_s["Release staging lock"]

    unlock_s --> appr{"Manual approval<br/>release-approvers only<br/>not the commit author<br/>72 hour limit"}
    appr -->|no decision in 72 hours| expire["Run expires<br/>announce<br/>production untouched"]
    appr -->|rejected| reject["Run ends<br/>announce"]
    appr -->|a newer run reached approval| supersede["Run superseded<br/>announce"]
    appr -->|approved| win{"Start inside window?<br/>Mon to Thu, 09:00 to 15:00 UTC"}
    win -->|no| wait["Wait for next window opening"]
    wait -->|a newer run reached approval| supersede
    wait --> win
    win -->|yes| lock_p["Take production lock<br/>one production deploy at a time"]

    lock_p --> canary["deploy.sh canary SHA<br/>migrate production, canary to 2 pods<br/>wait for rollout"]
    canary -->|rollout fails| off_1["deploy.sh canary-off"]
    off_1 --> fail_p["Run ends<br/>release production lock<br/>announce"]
    canary -->|rollout ok| watch["Watch canary for 15 minutes<br/>Prometheus 5xx ratio, sampled every 30 seconds"]
    watch -->|any sample above 1 percent| off_2["deploy.sh canary-off"]
    watch -->|2 empty samples in a row| off_2
    off_2 --> fail_p
    watch -->|15 minutes clean| prod["deploy.sh production SHA<br/>migrate again, a no-op<br/>stable rollout, then write SSM tags"]
    prod -->|rollout fails| undo_p["kubectl rollout undo<br/>production shop-api<br/>SSM not changed"]
    undo_p --> off_3["deploy.sh canary-off"]
    off_3 --> fail_p
    prod -->|rollout ok| off_4["deploy.sh canary-off<br/>remove canary"]
    off_4 -->|ok| finish["Release production lock<br/>announce success"]
    off_4 -->|fails| fail_p
```

## What each step reads and writes

| Step | Trigger | Reads | Writes | If it fails |
|---|---|---|---|---|
| PR check | pull request opened or updated | the PR's source | nothing outside CI | PR check fails, nothing deploys |
| Build | merge to `main` | source | image in the CI workspace | run ends |
| Unit tests | build done | source | test results | run ends, no retry |
| Integration tests | build done | source, Postgres service container | test results | one automatic retry, then run ends |
| Push | both test suites pass | the built image | `registry.internal/shop-api:SHA` | run ends |
| Staging deploy | push done, staging lock taken | SSM staging current_tag, staging cluster | migrations, staging image, then SSM staging previous_tag and current_tag | rollout fails: `kubectl rollout undo`. Smoke fails: `deploy.sh rollback staging` |
| Smoke tests | staging deploy ok | staging URL | nothing | `deploy.sh rollback staging`, run ends |
| Approval | smoke passed, staging lock released | release-approvers membership, commit author | approval record | 72 hours with no decision: run expires. Rejected: run ends. A newer approval: run is superseded |
| Window check | approved | clock | nothing | waits for the next window, and can still be superseded |
| Canary deploy | window open, production lock taken | production cluster | production migrations, canary image and replicas | rollout fails: `deploy.sh canary-off`, run ends |
| Canary watch | canary rollout ok | Prometheus canary 5xx ratio | nothing | any sample above 1 percent, or 2 empty samples in a row: `deploy.sh canary-off`, run ends |
| Production deploy | 15 minutes clean | production cluster | stable image, then SSM production previous_tag and current_tag | rollout fails: `kubectl rollout undo` on stable, then `deploy.sh canary-off`, run ends |
| Canary removal | stable rollout ok | production cluster | canary replicas set to 0 | run fails and is announced. Stable is already on the new tag, so a person checks it |

## Rules chosen where the brief left the choice open

- **Image**: pushed only after both test suites pass. Staging and production deploy that same image. Nothing is rebuilt.
- **Concurrent runs**: each run has its own SHA. The staging lock lets only one run deploy to staging at a time. A run holds it from its staging deploy until smoke tests pass, then releases it before waiting for approval. The production lock is held from the canary deploy until canary removal.
- **Superseding**: when a run is approved, every older run that is still waiting for approval or for the window is superseded. It is cancelled and announced. A run that has started its canary is never superseded. Production therefore receives only the newest approved commit that passed staging, never an older one after a newer one.
- **Approval**: only members of `release-approvers` can approve, and never the author of the commit. A rejection ends the run. If nobody decides within 72 hours, the run expires. The 72 hours covers only the wait for approval. Staging keeps the new tag, and production stays on its current tag.
- **Window**: the window limits when a production deploy starts. A run approved outside it waits for the next Monday to Thursday 09:00 UTC opening. A deploy that starts at 14:55 may finish after 15:00.
- **Canary watch**: the Prometheus expression from `environments.md` is evaluated every 30 seconds for 15 minutes, giving 30 readings. Each reading is the share of canary requests that returned a 5xx error over the last minute. Any reading above 0.01 (1 percent) fails the run. If the canary receives no requests, the division has nothing to divide, so the reading is empty. Two empty readings in a row also fail the run, because a canary with no traffic proves nothing.
- **Rollback versus undo**: smoke failures use `deploy.sh rollback`. The script writes SSM tags only after a successful rollout, so `previous_tag` is the tag that ran before the current one. Rolling back to it is therefore correct. A rollout failure is different. The script stops before it writes any tags, so SSM still names the old tag as current. `deploy.sh rollback` would move stable to `previous_tag`, which is older than the tag that was running, and would leave SSM wrong. `kubectl rollout undo` restores the pods that ran before the failed rollout, which matches SSM. That is why rollout failures use it.

## Carried over from the existing files

- **Migrations are forward-only.** There are no down steps. Every migration must work with the previous image, because a failed rollout or a rollback leaves the old image running on the migrated schema.
- **`rollback` changes only the image.** It sets current_tag from previous_tag but leaves previous_tag unchanged. A second rollback therefore sets the same tag again and does nothing new.
- **The canary is never recorded in SSM.** Only stable state is kept there.
- **Production window and approvers** come from `existing/environments.md` and are applied as written above.

## Known limits

- Laptop deploys still work. They bypass the locks, the approval and the run's state until laptop access is removed.
- Only pipeline runs take the locks. A deploy outside the pipeline is not blocked by them.
- The pipeline needs CI credentials for both clusters, as CI has today.
- Integration tests keep their known flaky test. The single retry covers it. A second failure ends the run.
