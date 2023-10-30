#!/bin/bash

. /usr/local/bin/docker-entrypoint.sh

twelve_factorify_config () {
	cp /proxy_conf.yaml /etc/satosa/
	cp -a /config /etc/satosa/config

        if test -v SATOSA_ENTITY_ID; then
		sed -i -e "s|entityid: https://satosa-127-0-0-1.nip.io/tequila|entityid: ${SATOSA_ENTITY_ID}|" /etc/satosa/config/saml2_backend.yaml
	fi

	if test -v SATOSA_BASE_URL; then
		for twelve_factorable in /etc/satosa/config/* /etc/satosa/config/*/* ; do
			sed -i -e "s|https://satosa-127-0-0-1.nip.io|${SATOSA_BASE_URL}|" \
				$twelve_factorable;
		done
	else
		export SATOSA_BASE_URL=https://satosa-127-0-0-1.nip.io
	fi
}

unset -f docker_pprint_metadata
# Doctored because the original insists on `frontend.xml` being a correct XML file,
# which it won't because we don't use SAML as front-end.
docker_pprint_metadata () {
	# use the SAML2 backend keymat to temporarily sign the generated metadata
	touch backend.xml frontend.xml
	satosa-saml-metadata proxy_conf.yaml backend.key backend.crt
	sed -i 's/ID="id-[^"]*"//' backend.xml

	echo -----BEGIN SAML2 BACKEND METADATA-----
	xq -x 'del(."ns0:EntityDescriptor"."ns1:Signature")' backend.xml | tee backend.xml.new
	echo -----END SAML2 BACKEND METADATA-----

	mv backend.xml.new backend.xml
}

twelve_factorify_config
_main gunicorn --certfile=/tls/satosa.crt --keyfile=/tls/satosa.key -b0.0.0.0:8443 epfl.satosa_wsgi:app
