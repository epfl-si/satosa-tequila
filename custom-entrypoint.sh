#!/bin/bash

. /usr/local/bin/docker-entrypoint.sh

unset -f docker_pprint_metadata
# Shunted out because the original insists on `frontend.xml` being a
# correct XML file, which it won't because we don't use SAML as
# front-end.
docker_pprint_metadata () {
	:
}

if test -d /tls; then
	certopts="--certfile=/tls/satosa.crt --keyfile=/tls/satosa.key"
	port=8443
else
	certopts=""
	port=8080
fi
_main gunicorn ${DEBUG_DISABLE_GUNICORN_TIMEOUTS:+--timeout 0} --threads 10 $certopts -b0.0.0.0:$port epfl.satosa_wsgi:app
