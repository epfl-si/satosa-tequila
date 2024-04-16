#!/bin/bash

. /usr/local/bin/docker-entrypoint.sh

# Shunted out because we do all the required prep by ourselves:
unset -f docker_pprint_metadata
docker_pprint_metadata () {
	:
}
unset -f docker_create_config
docker_create_config () {
	:
}

(cd /tmp; _make_selfsigned frontend)

if test -d /tls; then
	certopts="--certfile=/tls/tls.crt --keyfile=/tls/tls.key"
	port=8443
else
	certopts=""
	port=8080
fi
_main gunicorn ${DEBUG_DISABLE_GUNICORN_TIMEOUTS:+--timeout 0} --threads 10 $certopts -b0.0.0.0:$port epfl.satosa_wsgi:app
