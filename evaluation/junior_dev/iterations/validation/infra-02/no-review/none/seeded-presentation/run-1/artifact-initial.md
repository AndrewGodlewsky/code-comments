## shop-api pipeline notes

Production goes through the pilot first. The pilot is shop-api-canary, which takes 10% of traffic once its 2 pods are ready, and the canary-check job asks Prometheus for the pilot's 5xx share once a minute for a quarter of an hour, and if it is over 1% even once, or Prometheus returns nothing at all, we pull the pilot with canary-off and the run is dead; the main deployment was never touched in that case so the parameter store still says the old tag, and the database keeps whatever the canary step migrated, because `deploy.sh canary` migrates before the pilot starts and nothing in the system migrates down (the old image has to cope with it). Before any of that there is the sign-off, and before that staging, and PRs by the way only do build plus unit tests and never deploy anything, only merges to main run the whole thing. The image is built one time per run and pushed as registry.internal/shop-api:<sha>, and that sha goes around as IMAGE_TAG to the later jobs, so staging and prod get the very same image and nothing gets rebuilt.

```mermaid
flowchart LR
    a["PR"] --> b["bld"] --> c["ut"] --> d["PR status"]
    m["main"] --> e["bld + push"]
    e --> f["ut"]
    e --> g["it"]
    g -.->|x| g2["it again"]
    f --> h{"ok?"}
    g --> h
    g2 --> h
    h -->|no| z(["fail + post"])
    h --> s1["lock S"]
    s1 --> s2["deploy.sh staging"]
    s2 --> s3["smoke"]
    s2 -.->|bad rollout| u1["undo"]
    s3 -.->|red| rb["rollback"]
    rb --> z
    u1 --> z
    s3 --> k["kill older"]
    k --> n["ping"]
    n --> ap{"sign-off"}
    ap -->|72h| ex(["expired"])
    ap --> w{"window and lock"}
    w -->|wait| w
    w --> pl["lock P"]
    pl --> cn["pilot"]
    cn --> cw["watch"]
    cw -.->|bad| coff["canary-off"]
    cn -.->|bad rollout| coff
    cw --> st["stable"]
    st -.->|bad rollout| u2["undo + canary-off"]
    st --> coff2["canary-off"]
    coff2 --> fin(["done + post"])
    coff --> rl["unlock P"] --> z
    u2 --> rl
    N1>"no retry for ut, it retried once, anything still failing ends it before staging"] -.- h
    N2>"undo = kubectl rollout undo, NOT deploy.sh rollback, since SSM is not written yet and rollback would go one too far back"] -.- u1
    N3>"rollback = deploy.sh rollback staging, goes to previous_tag = what staging ran before"] -.- rb
    N4>"release-approvers only, not the commit author, 72h from reaching the gate, then expired and prod never gets it, staging keeps the build"] -.- ap
    N5>"Mon-Thu 09:00-15:00 UTC start only, poll every 5 min, may finish after 15:00"] -.- w
    N6>"staging lock released on smoke pass or fail"] -.- s1
```

Misc (no particular order):
- Tags live in Parameter Store: `/deploy/<env>/current_tag` and `/deploy/<env>/previous_tag`. deploy.sh <env> <tag> writes both but only once the main rollout went fine; deploy.sh rollback flips current back to previous; the pilot never gets written. Who approved and when sits in the CI run record.
- The ping (the approval message, in #deploys) carries IMAGE_TAG, a link to the smoke results and the commit list between prod's current_tag and this tag; people approve in the CI UI.
- kill older = when a run's staging smoke goes green, older runs that haven't begun their prod deploy (still waiting on sign-off, on the window, or on lock P) are cancelled as superseded, so approvers only see the newest staging-verified build.
- An approval given on a Thursday evening just sits there until Monday 09:00 and doesn't lapse once given. Lock P is held by one prod deploy at a time; if it's busy the run waits the same way.
- On the stable step: deploy.sh production (migrate is a no-op by then) writes the SSM tags, then canary-off, the lock is released, and a post in the deploys channel names the approver. A bad rollout there gets kubectl rollout undo, then canary-off.
- Posts go to Slack #deploys for: waiting on approval, superseded, expired, failed (with which step), prod done.
