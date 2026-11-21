# catalog-web blue-green deploy

- [ ] Get the deploy lock
- [ ] Work out live / idle colour
- [ ] Build image + migration lint
- [ ] Run migrations (additive only, indexes built concurrently)
- [ ] Deploy new release to idle colour (4 instances)
- [ ] Health checks
- [ ] Smoke tests via test listener
- [ ] Switch the LB to the new colour
- [ ] Watch 5xx for 15 min, roll back if it spikes
- [ ] Keep old colour up for the rollback window
- [ ] Tear down old colour
- [ ] Release the lock
