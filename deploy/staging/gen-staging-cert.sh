#!/usr/bin/env bash
# one-time staging certificate generator — SELF-SIGNED, for local staging only.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p certs
openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
  -keyout certs/phoenix-staging.key \
  -out certs/phoenix-staging.crt \
  -subj "/C=XX/O=PhantomPhoenixStaging/CN=phoenix-staging-local" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
chmod 600 certs/phoenix-staging.key
echo "staging cert generated: certs/phoenix-staging.crt (self-signed, 30 days)"
