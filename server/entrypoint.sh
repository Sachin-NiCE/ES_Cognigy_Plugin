#!/bin/sh
set -eu

: "${SERVER_NAME:=_}"  # nginx catch-all if not set

if [ ! -f /etc/nginx/certs/fullchain.pem ] || [ ! -f /etc/nginx/certs/privkey.pem ]; then
    echo "ERROR: /etc/nginx/certs/fullchain.pem and privkey.pem are required." >&2
    echo "Mount your corporate certificate/key there (see nginx/certs/README.md)." >&2
    exit 1
fi

export SERVER_NAME
envsubst '${SERVER_NAME}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

exec supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
