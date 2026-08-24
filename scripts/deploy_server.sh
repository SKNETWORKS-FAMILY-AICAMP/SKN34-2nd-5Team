#!/usr/bin/env bash
set -Eeuo pipefail

# This script is executed on the AWS application server by GitHub Actions.
# It intentionally does not migrate schemas, load DB data, or alter .env/data.

DEPLOY_BRANCH="main"
EXPECTED_SHA="${EXPECTED_SHA:-}"
API_SERVICE="${API_SERVICE:-}"
AUTH_SERVICE="${AUTH_SERVICE:-}"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-}"
FRONTEND_ROOT="${FRONTEND_ROOT:-}"

log() {
  printf '[deploy] %s\n' "$*"
}

fail() {
  printf '[deploy] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command is missing: $1"
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local attempts="${3:-20}"
  local delay_seconds="${4:-1}"
  local attempt

  for ((attempt = 1; attempt <= attempts; attempt += 1)); do
    if curl --fail --silent --show-error --max-time 3 "$url" >/dev/null; then
      log "$label is healthy: $url"
      return 0
    fi
    sleep "$delay_seconds"
  done

  fail "$label health check failed after $attempts attempts: $url"
}

[[ -n "$EXPECTED_SHA" ]] || fail 'EXPECTED_SHA is required.'
[[ "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]] || fail 'EXPECTED_SHA must be a full Git commit SHA.'
[[ "$API_SERVICE" =~ ^[A-Za-z0-9_.@-]+$ ]] || fail 'API_SERVICE is missing or invalid.'
[[ "$AUTH_SERVICE" =~ ^[A-Za-z0-9_.@-]+$ ]] || fail 'AUTH_SERVICE is missing or invalid.'
[[ "$VITE_API_BASE_URL" =~ ^https://[^/[:space:]]+/?$ ]] || fail 'VITE_API_BASE_URL must be an HTTPS origin without a path.'
PUBLIC_ORIGIN="${VITE_API_BASE_URL%/}"
[[ "$FRONTEND_ROOT" =~ ^/var/www/[A-Za-z0-9._/-]+$ ]] || fail 'FRONTEND_ROOT must be a path below /var/www/.'
[[ "$FRONTEND_ROOT" != *'..'* ]] || fail 'FRONTEND_ROOT must not contain parent-directory traversal.'

require_command git
require_command node
require_command npm
require_command curl
require_command flock
require_command readlink
require_command sudo
require_command systemctl

node_version="$(node -p 'process.versions.node')"
node_major="${node_version%%.*}"
node_minor="${node_version#*.}"
node_minor="${node_minor%%.*}"
if ((node_major == 20 && node_minor >= 19)); then
  :
elif ((node_major == 22 && node_minor >= 12)); then
  :
elif ((node_major > 22)); then
  :
else
  fail "Node.js 20.19+ or 22.12+ is required, found: $node_version"
fi

PROJECT_ROOT="$(pwd -P)"
[[ "$PROJECT_ROOT" != '/' ]] || fail 'Refusing to deploy from the filesystem root.'
[[ -d "$PROJECT_ROOT/.git" ]] || fail "Not a Git checkout: $PROJECT_ROOT"
[[ -f "$PROJECT_ROOT/app/package-lock.json" ]] || fail 'app/package-lock.json was not found.'
[[ "$(readlink -m -- "$FRONTEND_ROOT")" == "$FRONTEND_ROOT" ]] || fail 'FRONTEND_ROOT must be an absolute canonical path.'
[[ "$FRONTEND_ROOT" != '/var/www' ]] || fail 'Refusing to replace /var/www itself.'

exec 9>"$PROJECT_ROOT/.deploy.lock"
flock -n 9 || fail 'Another deployment is already running.'

current_branch="$(git branch --show-current)"
[[ "$current_branch" == "$DEPLOY_BRANCH" ]] || fail "Server branch must be $DEPLOY_BRANCH, found: $current_branch"

# Ignored runtime files such as .env, data, models, and photos are preserved.
# Any tracked edit means the server and GitHub have diverged, so stop safely.
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  git status --short --untracked-files=no >&2
  fail 'Tracked server files are modified. Reconcile them with GitHub before deploying.'
fi

if [[ -x "$PROJECT_ROOT/venv/bin/python" ]]; then
  PYTHON_BIN="$PROJECT_ROOT/venv/bin/python"
elif [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
else
  fail 'Python virtual environment was not found at venv/ or .venv/.'
fi

sudo systemctl cat "$API_SERVICE" >/dev/null || fail "Unknown systemd service: $API_SERVICE"
sudo systemctl cat "$AUTH_SERVICE" >/dev/null || fail "Unknown systemd service: $AUTH_SERVICE"
sudo -n true >/dev/null || fail 'The deploy user needs non-interactive sudo for service management.'

log "Fetching $DEPLOY_BRANCH from origin..."
git fetch --prune origin "$DEPLOY_BRANCH"
remote_sha="$(git rev-parse "origin/$DEPLOY_BRANCH")"
[[ "$remote_sha" == "$EXPECTED_SHA" ]] || fail "GitHub main moved during deployment. Expected $EXPECTED_SHA, found $remote_sha. Run the workflow again."
git merge-base --is-ancestor HEAD "$remote_sha" || fail 'Server history cannot be fast-forwarded to GitHub main.'

log "Fast-forwarding server checkout to $EXPECTED_SHA..."
git merge --ff-only "$remote_sha"

log 'Installing Python runtime dependencies...'
"$PYTHON_BIN" -m pip install --disable-pip-version-check \
  -r "$PROJECT_ROOT/api/requirements.txt" \
  -r "$PROJECT_ROOT/auth_service/requirements.txt"
"$PYTHON_BIN" -m compileall -q \
  "$PROJECT_ROOT/api" \
  "$PROJECT_ROOT/auth_service" \
  "$PROJECT_ROOT/shared"

log 'Building React into a staging directory...'
cd "$PROJECT_ROOT/app"
npm ci

NEXT_DIST="$PROJECT_ROOT/app/dist.next"
CURRENT_DIST="$FRONTEND_ROOT"
PREVIOUS_DIST="${FRONTEND_ROOT}.previous"

[[ "$NEXT_DIST" == "$PROJECT_ROOT/app/dist.next" ]] || fail 'Unexpected staging path.'
[[ "$CURRENT_DIST" == /var/www/* ]] || fail 'Unexpected frontend publish path.'
[[ "$PREVIOUS_DIST" == /var/www/*.previous ]] || fail 'Unexpected frontend backup path.'
rm -rf -- "$NEXT_DIST"
VITE_API_BASE_URL="$VITE_API_BASE_URL" npm run build -- --outDir "$NEXT_DIST" --emptyOutDir
[[ -f "$NEXT_DIST/index.html" ]] || fail 'React build did not create dist.next/index.html.'
if grep -R --fixed-strings --quiet 'http://localhost:8000' "$NEXT_DIST"; then
  fail 'React production build still contains the localhost API fallback.'
fi

log 'Checking Nginx configuration before publishing...'
sudo nginx -t
nginx_config="$(sudo nginx -T 2>&1)"
if [[ "$nginx_config" != *"root $CURRENT_DIST;"* ]]; then
  fail "Nginx does not serve the React build directory: $CURRENT_DIST"
fi
if [[ "$nginx_config" != *"listen 443 ssl"* ]]; then
  fail 'Nginx does not expose an HTTPS listener.'
fi
if [[ "$nginx_config" != *'return 301 https://'* && "$nginx_config" != *'return 308 https://'* ]]; then
  fail 'Nginx does not redirect HTTP traffic to HTTPS.'
fi

restore_previous_frontend() {
  if [[ -d "$PREVIOUS_DIST" ]]; then
    log 'Restoring the previous React build after a failed health check...'
    sudo rm -rf -- "$CURRENT_DIST"
    sudo mv -- "$PREVIOUS_DIST" "$CURRENT_DIST"
  fi
}

trap restore_previous_frontend ERR

sudo rm -rf -- "$PREVIOUS_DIST"
if [[ -d "$CURRENT_DIST" ]]; then
  sudo mv -- "$CURRENT_DIST" "$PREVIOUS_DIST"
fi
sudo mv -- "$NEXT_DIST" "$CURRENT_DIST"

log "Restarting $API_SERVICE and $AUTH_SERVICE..."
sudo systemctl restart "$API_SERVICE"
sudo systemctl restart "$AUTH_SERVICE"

wait_for_http 'http://127.0.0.1:8000/health' 'Analysis API'
api_health="$(curl --fail --silent --show-error --max-time 3 'http://127.0.0.1:8000/health')"
[[ "$api_health" == *'"environment":"production"'* ]] || fail 'Analysis API is not running in production mode.'
[[ "$api_health" == *'"developmentOperator":false'* ]] || fail 'Analysis API development identity is enabled.'
wait_for_http 'http://127.0.0.1:8100/auth/health' 'Auth API'
auth_health="$(curl --fail --silent --show-error --max-time 3 'http://127.0.0.1:8100/auth/health')"
[[ "$auth_health" == *'"environment":"production"'* ]] || fail 'Auth service is not running in production mode.'
[[ "$auth_health" == *'"secureCookie":true'* ]] || fail 'Auth service does not enforce Secure cookies.'
wait_for_http "$PUBLIC_ORIGIN/health" 'Public HTTPS API'
wait_for_http "$PUBLIC_ORIGIN/auth/health" 'Public HTTPS auth service'
wait_for_http "$PUBLIC_ORIGIN/" 'Public HTTPS React'

trap - ERR
sudo rm -rf -- "$PREVIOUS_DIST"

deployed_sha="$(git rev-parse HEAD)"
[[ "$deployed_sha" == "$EXPECTED_SHA" ]] || fail "Deployed SHA mismatch: $deployed_sha"
log "Deployment completed successfully: $deployed_sha"
