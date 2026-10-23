#!/usr/bin/env bash
# Build on this machine, ship images to the VM over SSH, and (re)start the stack.
#   SSH_KEY=~/.ssh/snapurl.key ./deploy/deploy.sh ubuntu@129.225.104.110 snapurl.duckdns.org
# Secrets are generated on the VM on first deploy and never leave it.
set -euo pipefail

HOST="${1:?usage: deploy.sh user@host domain}"
DOMAIN="${2:?usage: deploy.sh user@host domain}"
KEY="${SSH_KEY:-$HOME/.ssh/snapurl.key}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH=(ssh -i "$KEY" -o ConnectTimeout=20 "$HOST")

echo "==> Building images (linux/amd64)"
docker build --platform linux/amd64 -q -t snapurl-api:latest "$ROOT/backend"
docker build --platform linux/amd64 -q -t snapurl-web:latest "$ROOT/frontend"

echo "==> Shipping images to $HOST"
docker save snapurl-api:latest snapurl-web:latest | gzip -1 | "${SSH[@]}" 'gunzip | docker load -q'

echo "==> Copying config"
"${SSH[@]}" 'mkdir -p ~/snapurl'
scp -i "$KEY" -q "$ROOT/deploy/docker-compose.prod.yml" "$HOST:snapurl/docker-compose.yml"
scp -i "$KEY" -q "$ROOT/deploy/Caddyfile" "$HOST:snapurl/Caddyfile"

echo "==> Starting stack"
"${SSH[@]}" DOMAIN="$DOMAIN" bash -s <<'REMOTE'
set -euo pipefail
cd ~/snapurl
if [ ! -f .env ]; then
  umask 077
  cat > .env <<EOF
DOMAIN=$DOMAIN
JWT_SECRET=$(openssl rand -base64 48 | tr -d '\n=+/')
POSTGRES_PASSWORD=$(openssl rand -hex 24)
EOF
  echo "   created .env with fresh secrets"
fi
docker compose up -d --remove-orphans --wait --wait-timeout 180
docker image prune -f >/dev/null
docker compose ps --format '   {{.Service}}: {{.Status}}'
REMOTE

echo "==> Checking https://$DOMAIN/health"
for _ in $(seq 1 30); do
  if curl -fsS --max-time 10 "https://$DOMAIN/health"; then echo; echo "==> Live at https://$DOMAIN"; exit 0; fi
  sleep 3
done
echo "Health check failed; see: ssh $HOST 'cd snapurl && docker compose logs --tail 50'" >&2
exit 1
