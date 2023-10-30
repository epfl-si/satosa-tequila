#!/bin/bash

. /usr/local/bin/docker-entrypoint.sh

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

_main gunicorn --certfile=/tls/satosa.crt --keyfile=/tls/satosa.key -b0.0.0.0:8443 epfl.satosa_wsgi:app
