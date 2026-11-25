#!/usr/bin/env bash
# After a deploy: the public parts answer, the private parts stay private.
# Everything is scaled to zero, so the first request may wait for a cold start (retries below).
# Usage: smoke.sh <api-url> <web-url> <resource-group>
set -euo pipefail
api_url="$1"
web_url="$2"
rg="$3"

wait_for() { # url expected-status
  local code=""
  for _ in $(seq 1 30); do
    code=$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 30 "$1" || true)
    if [ "$code" = "$2" ]; then return 0; fi
    sleep 5
  done
  echo "::error::$1 answered $code, expected $2"
  return 1
}

start=$(date +%s)
wait_for "$api_url/health" 200
echo "api awake after $(($(date +%s) - start)) s"
test "$(curl --silent --output /dev/null --write-out '%{http_code}' "$api_url/me")" = "401"

# The browser calls the API from the web app's address: CORS must allow exactly that origin.
curl --silent --dump-header - --output /dev/null --request OPTIONS \
  --header "Origin: $web_url" --header "Access-Control-Request-Method: GET" "$api_url/me" |
  grep --ignore-case --quiet "access-control-allow-origin: $web_url"

start=$(date +%s)
wait_for "$web_url/" 200
echo "web awake after $(($(date +%s) - start)) s"
curl --silent --header "Accept-Language: de-DE" "$web_url/" | grep --quiet 'lang="de"'
curl --silent --header "Accept-Language: en-GB" "$web_url/" | grep --quiet 'lang="en"'

# The validator has no authentication: it must not be reachable from the internet (ADR-0005).
test "$(az containerapp show --name validator --resource-group "$rg" \
  --query properties.configuration.ingress.external --output tsv)" = "false"
test -z "$(az containerapp show --name worker --resource-group "$rg" \
  --query properties.configuration.ingress --output tsv)"
echo "smoke test passed"
