#!/usr/bin/env bash
# deploy.sh: how shop-api is deployed today (run by hand from a laptop).
#
#   ./deploy.sh <staging|production> <tag>   migrate, then roll stable shop-api to <tag>
#   ./deploy.sh canary <tag>                  production only: migrate, then run <tag>
#                                             on shop-api-canary (2 pods, 10% of traffic)
#   ./deploy.sh canary-off                    scale shop-api-canary to 0 pods
#   ./deploy.sh rollback <env>                roll stable shop-api back to previous_tag
#
# Live state is NOT kept in this repo. Per environment, SSM Parameter Store holds:
#   /deploy/<env>/current_tag    the tag the stable deployment runs
#   /deploy/<env>/previous_tag   the tag it ran before that
# The canary is never recorded there.
set -euo pipefail

REGISTRY="registry.internal/shop-api"
get_param() { aws ssm get-parameter --name "$1" --query Parameter.Value --output text; }
put_param() { aws ssm put-parameter --name "$1" --value "$2" --type String --overwrite >/dev/null; }
kc() { kubectl --context "$1" -n shop "${@:2}"; }

# Migrations are forward-only: there are no down steps, and nothing in this
# script undoes one. `migrate up` applies only pending migrations, so running
# it again is a no-op. Every migration must keep working with the previous image.
migrate() { kc "$1" run "migrate-$2" --rm -i --restart=Never --image="$REGISTRY:$2" -- ./bin/migrate up; }

case "$1" in
  canary)
    migrate production "$2"
    kc production set image deploy/shop-api-canary app="$REGISTRY:$2"
    kc production scale deploy/shop-api-canary --replicas=2
    kc production rollout status deploy/shop-api-canary --timeout=300s
    ;;
  canary-off)
    kc production scale deploy/shop-api-canary --replicas=0
    ;;
  rollback)
    TAG="$(get_param "/deploy/$2/previous_tag")"
    # Image only: the schema stays where it is.
    kc "$2" set image deploy/shop-api app="$REGISTRY:$TAG"
    kc "$2" rollout status deploy/shop-api --timeout=300s
    put_param "/deploy/$2/current_tag" "$TAG"
    ;;
  staging|production)
    CURRENT="$(get_param "/deploy/$1/current_tag")"
    migrate "$1" "$2"
    kc "$1" set image deploy/shop-api app="$REGISTRY:$2"
    kc "$1" rollout status deploy/shop-api --timeout=300s
    # Tags are written only after the rollout succeeded.
    put_param "/deploy/$1/previous_tag" "$CURRENT"
    put_param "/deploy/$1/current_tag" "$2"
    ;;
  *)
    echo "usage: see the header of this file" >&2
    exit 2
    ;;
esac
