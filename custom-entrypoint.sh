#!/bin/bash

. /usr/local/bin/docker-entrypoint.sh

twelve_factorify_config () {
	cp /proxy_conf.yaml /etc/satosa/
        mkdir -p /etc/satosa/config || true
	cp $(find /config -follow -maxdepth 1 -type f) /etc/satosa/config
	mkdir -p /etc/satosa/config/attributemaps || true
	if [ -d "/attributemaps" ]; then
		cp /attributemaps/* /etc/satosa/config/attributemaps/
                rm -rf /etc/satosa/config/attributemaps/__pycache__ || true
	fi
}

unset -f docker_pprint_metadata
# Shunted out because the original insists on `frontend.xml` being a
# correct XML file, which it won't because we don't use SAML as
# front-end.
docker_pprint_metadata () {
	:
}

twelve_factorify_config

if test -d /tls; then
	certopts="--certfile=/tls/satosa.crt --keyfile=/tls/satosa.key"
	port=8443
else
	certopts=""
	port=8080
fi
_main gunicorn ${DEBUG_DISABLE_GUNICORN_TIMEOUTS:+--timeout 0} --threads 10 $certopts -b0.0.0.0:$port epfl.satosa_wsgi:app
