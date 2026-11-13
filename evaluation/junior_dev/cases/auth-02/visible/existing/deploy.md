# Deploying orders-api

- CI builds one container image per merge to `main`. The image includes
  `config/app.yaml` exactly as it is in the repo.
- Production runs 4 replicas on the cluster, all under the service identity
  `orders-api-prod`.
- Deploys are rolling, one pod at a time, with `maxUnavailable: 0`: a new pod
  must pass its readiness probe (`GET /healthz` returns 200) before an old pod
  is stopped. If a new pod never becomes ready, the rollout halts and the old
  pods keep serving.
- Today `/healthz` returns `{"status": "ok"}` as soon as the HTTP server is
  listening.
- Rollback = redeploying an earlier image.
- Developers run the app locally with `make run`, which loads the same
  `config/app.yaml` -- so local runs use the live keys today.
- Logs go to the central log service and are kept for 30 days.
