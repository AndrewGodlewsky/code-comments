# shop-api release pipeline

**What starts a run.** A pull request runs build and unit tests only and never deploys. A merge to `main` starts the full pipeline below.

**Where state lives**
- **Image.** Built once per run and pushed as `registry.internal/shop-api:<commit SHA>`. The tag becomes the run output `IMAGE_TAG`, which every later job reads. Staging and production deploy exactly this image. Nothing is rebuilt.
- **What each environment runs.** This is kept in SSM Parameter Store, outside the pipeline, under `/deploy/<env>/current_tag` and `/deploy/<env>/previous_tag`. Only `deploy.sh` writes them: `deploy.sh <env> <tag>` after a successful stable rollout, and `deploy.sh rollback <env>` when it sets current_tag back to previous_tag. The canary is never recorded.
- **Schema.** Migrations are forward-only. `deploy.sh` runs `migrate up` before the new image starts, and nothing reverts it, so every rollback swaps the image only. Each migration must work with the previous image.
- **Approval.** The CI run record keeps who approved and when.
- **Locks.** There are two CI named locks, `staging` and `production`. Each is held by one run at a time.

```mermaid
flowchart TD
    FAIL(["Run failed: post the failing step to the deploys channel"])

    subgraph PRS["Pull request opened or updated"]
        P1["Build image, not pushed"] --> P2["Unit tests"] --> P3(["Status on the PR. Never deploys."])
    end

    subgraph BT["Build and test: merge to main"]
        M(["Merge to main"]) --> B["Build once, push shop-api:SHA<br/>IMAGE_TAG = SHA"]
        B --> UT["Unit tests<br/>no retry"]
        B --> IT["Integration tests"]
        IT -->|fail| IR["Integration tests<br/>automatic retry, once"]
        UT -->|pass| J["Wait until both pass"]
        IT -->|pass| J
        IR -->|pass| J
    end

    subgraph ST["Staging: holds the staging lock"]
        SL["Take staging lock"] --> SD["deploy.sh staging IMAGE_TAG<br/>migrate up, roll stable, write SSM tags"]
        SD -->|rollout ok| SM["Smoke tests against staging"]
        SD -->|rollout fails| SU["kubectl rollout undo<br/>SSM still names the old image"]
        SM -->|fail| SR["deploy.sh rollback staging<br/>back to SSM previous_tag"]
    end

    subgraph AG["Approval and production gate"]
        SUP["Release staging lock<br/>cancel older runs not yet in production: superseded"]
        SUP --> AN["Post to deploys channel: tag, smoke results,<br/>commits since production current_tag"]
        AN --> AP{"Approved within 72 h?<br/>release-approvers only, not the commit author"}
        AP -->|"no approval in 72 h"| EXP(["Expired: post to deploys channel<br/>nothing reaches production"])
        AP -->|approved| PG{"Inside start window Mon-Thu 09:00-15:00 UTC<br/>and production lock free?"}
        PG -->|"no: re-check in 5 min"| PG
        PG -->|yes| PL["Take production lock"]
    end

    subgraph PD["Production: holds the production lock"]
        C["deploy.sh canary IMAGE_TAG<br/>migrate up, then 2 canary pods get 10% of traffic"]
        C -->|rollout ok| CW["Canary watch for 15 min<br/>Prometheus canary 5xx ratio every 60 s"]
        CW -->|"every reading at or below 1%"| PS["deploy.sh production IMAGE_TAG<br/>migrate is a no-op, roll stable, write SSM tags"]
        PS -->|rollout ok| CO["deploy.sh canary-off"]
        C -->|rollout fails| COFF["deploy.sh canary-off<br/>stable untouched, SSM unchanged, schema stays"]
        CW -->|"a reading above 1%, or no data"| COFF
        PS -->|rollout fails| PU["kubectl rollout undo, then canary-off"]
    end

    DONE(["Release production lock<br/>post success and approver to deploys channel"])
    RL["Release production lock"]

    UT -->|fail| FAIL
    IR -->|fail| FAIL
    J --> SL
    SU --> FAIL
    SR --> FAIL
    SM -->|pass| SUP
    PL --> C
    CO --> DONE
    COFF --> RL
    PU --> RL
    RL --> FAIL
```

**Step notes**

1. **Tests.** Unit and integration tests start together after the build. Integration tests get one automatic retry. Unit tests get none. Any final failure ends the run, and nothing reaches staging.
2. **Staging.** The run holds the `staging` lock from the deploy until the smoke result, pass or fail. `deploy.sh staging IMAGE_TAG` migrates, rolls the stable deployment and writes the SSM tags.
   - If the rollout fails, `kubectl rollout undo` returns staging to the pods that were running. SSM was not written, so it still names them. `rollback` is not used here because previous_tag would go one version too far back.
   - If the smoke tests fail, `deploy.sh rollback staging` restores previous_tag, which is the image staging ran before this run.
3. **Supersede.** When a run passes the staging smoke tests, every older run that has not started its production deploy is cancelled as *superseded* and posts a notice. That includes runs waiting for approval, for the window or for the lock. Approvers only ever see the newest build verified on staging.
4. **Approval.** The run posts to #deploys with IMAGE_TAG, a link to the smoke results, and the commits between production `current_tag` and IMAGE_TAG. A `release-approvers` member who is not the commit author approves in the CI UI. The 72-hour clock starts when the run reaches the gate. If it runs out, the run ends as *expired*: nothing goes to production, and staging keeps the image.
5. **Production gate.** An approved run starts only when two things are true: the time is inside the start window (Mon-Thu 09:00-15:00 UTC), and the `production` lock is free. Otherwise it waits and re-checks every 5 minutes, so an approval given on Thursday evening starts at Monday 09:00. A given approval does not expire. Once started, the deploy may run past 15:00.
6. **Canary.** `deploy.sh canary IMAGE_TAG` runs the migrations, then puts 2 canary pods on the new image. Those pods take 10% of traffic. The canary-watch step queries Prometheus for the canary's 5xx ratio every 60 seconds for 15 minutes. One reading above 1%, or a query with no data, fails it at once and triggers `deploy.sh canary-off`. The stable deployment was never touched, SSM is unchanged, and the schema stays migrated.
7. **Stable.** `deploy.sh production IMAGE_TAG` rolls stable and writes SSM. The migrate step is a no-op by now. If the rollout fails, the pipeline runs `kubectl rollout undo` and then `canary-off`. On success it runs `canary-off`, releases the lock and posts to #deploys with the approver's name.
8. **Notices.** All of these go to #deploys: waiting for approval, superseded, expired, failed (with the failing step), and production done.

## General considerations

This design follows common good practice. Each part should be implemented carefully, tested thoroughly and monitored in production. The team should review the design as it evolves, keep documentation up to date, and make sure that changes are communicated clearly to everyone involved. Performance, security and reliability matter throughout, and trade-offs should be discussed openly when they arise.
