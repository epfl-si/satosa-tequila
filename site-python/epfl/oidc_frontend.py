import json
import logging
import time
import kubernetes
from urllib.parse import urlparse

from pyop.exceptions import InvalidRedirectURI
from satosa.frontends.openid_connect import OpenIDConnectFrontend as SATOSAOpenIDConnectFrontend

logger = logging.getLogger(__name__)


class OpenIDConnectFrontend(SATOSAOpenIDConnectFrontend):
    def __init__(self, auth_req_callback_func, internal_attributes, conf, base_url, name):
        """Overloaded so as to implement EPFL-specific enhancements.

          - continuous reload of the JSON database
          - Kubernetes database (backed by the `TequilaOIDCMapping` CRD) 
          - wildcard matching of redirect URIs
      """
        super().__init__(auth_req_callback_func, internal_attributes, conf, base_url, name)

        clients_db = self._init_clients_db ()
        if clients_db:
            logger.info("Will be loading OIDC client database from %s" % repr(clients_db))
            self.provider.clients = clients_db

        self.provider.authentication_request_validators = self._init_provider_validators(self.provider)

    def _init_clients_db (self):
        def wrap_into_a_dict(something_that_implements_get_all):
            return _ClientDatabaseDictish(something_that_implements_get_all)

        db_type = self.config.get("client_db", {}).get("type")
        if db_type.lower() == "json":
            json_path = self.config["client_db"]["path"]
            return wrap_into_a_dict(_JSONDB(json_path))
        elif db_type.lower() == "kubernetes":
            def provider_is_us (provider_url):
                return self.base_url.rstrip("/") == provider_url.rstrip("/")

            return wrap_into_a_dict(_KubernetesDB(provider_is_us))

    def _init_provider_validators(self, provider):
        def ensure_valid_redirect_uri (authentication_request):
            try:
                allowed_redirect_uris = provider.clients[authentication_request['client_id']]['redirect_uris']
            except KeyError as e:
                logger.error('client metadata is missing redirect_uris')
                raise InvalidRedirectURI(
                    'No redirect uri registered for this client',
                    authentication_request,
                    oauth_error="invalid_request")

            redirect_uri = authentication_request['redirect_uri']
            if redirect_uri in allowed_redirect_uris:
                return   # OK
            elif self._as_wildcard_url(redirect_uri) in allowed_redirect_uris:
                return   # OK
            else:
                logger.error("Redirect uri \'{0}\' is not registered for this client".format(authentication_request['redirect_uri']))
                raise InvalidRedirectURI(
                    'Redirect uri is not registered for this client',
                    authentication_request,
                    oauth_error="invalid_request")

        return [ v for v in provider.authentication_request_validators
                 if not (hasattr(v, 'func')
                         and 'redirect_uri_is_in_registered_redirect_uris' in v.func.__name__)
                ] + [ ensure_valid_redirect_uri ]

    def _as_wildcard_url (self, url):
        # No, _replace() is not a private API — just (yet another)
        # example of sloppy design in the Python standard library.
        # https://docs.python.org/3/library/urllib.parse.html#structured-parse-results
        return urlparse(url)._replace(path='*').geturl()

    def _get_extra_id_token_claims(self, user_id, client_id):
        """Overloaded to support loading the extra token claims from the client database."""
        base_token_claims = super()._get_extra_id_token_claims(user_id, client_id)
        if base_token_claims:
            return base_token_claims

        if client_id in self.provider.clients:
            config = self.provider.clients[client_id].get("extra_id_token_claims",
                                                          [])
            if type(config) is list and len(config) > 0:
                requested_claims = {k: None for k in config}
                return self.provider.userinfo.get_claims_for(user_id, requested_claims)

        return {}

    def _handle_authn_request(self, context):
        """Overloaded to set `context.tequila_require` from the configuration."""

        context.tequila_require = None
        client_id = context.request.get("client_id")
        if client_id and client_id in self.provider.clients:
            requires = self.provider.clients[client_id].get("tequila_requires",
                                                            [])
            if requires:
                require_stanza = "&".join("(%s)" % r for r in requires)
                logger.info("tequila_require %s" % require_stanza)
                context.tequila_require = require_stanza

        return super()._handle_authn_request(context)


class _ClientDatabaseDictish(object):
    """Minimalist implementation of a dict, that caches all lookups for a few seconds."""
    def __init__(self, getter_all, timeout_seconds=2):
        self.getter_all = getter_all
        self.last_time_read = None
        self.timeout_seconds = timeout_seconds
        self.cached_data = None

    def data(self):
        now = time.time()
        if self.last_time_read and self.last_time_read + self.timeout_seconds > now:
            return self.cached_data
        else:
            self.cached_data = self.getter_all.get_all()
            self.last_time_read = now
            return self.cached_data

    def __getitem__(self, key):
        return self.data()[key]

    def __contains__(self, key):
        return key in self.data()

    def __repr__(self):
        return repr(self.data())


class _JSONDB(object):
    """A getter_all for `_ClientDatabaseDictish` that reads out of a JSON file."""
    def __init__(self, json_file):
        self.json_file = json_file

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, self.json_file)

    def get_all(self):
        logger.debug("Reloading JSON from %s" % self.json_file)
        with open(self.json_file, 'r') as f:
            return json.load(f)


class _KubernetesDB(object):
    """A getter_all for `_ClientDatabaseDictish` that reads `TequilaOIDCMapping`s."""
    CR_GROUP = "tequila.epfl.ch"
    CR_VERSION = "v1"
    CR_NAME = "TequilaOIDCMapping"
    CR_PLURAL = "tequilaoidcmappings"

    def __init__(self, provider_url_filter_fn):
        self.provider_url_filter_fn = provider_url_filter_fn

    def __repr__(self):
        return "<%s>" % self.__class__.__name__

    def get_all(self):
        kubernetes.config.load_incluster_config()
        crs = kubernetes.client.CustomObjectsApi().list_cluster_custom_object(
            self.CR_GROUP, self.CR_VERSION, self.CR_PLURAL)

        logger.debug("Read %d %s's from Kubernetes" % (
            len(crs['items']), self.CR_NAME))

        retval = {
                self.get_client_id(tequila_cr):
                self.as_satosa_client_db_entry(tequila_cr)
                for tequila_cr in crs['items']
                if self.provider_url_filter_fn(tequila_cr["spec"]["oidc"]["providerURL"])
        }

        logger.debug("Data passed to SATOSA: %s" % repr(retval))
        return retval

    @classmethod
    def get_client_id (cls, tequila_cr):
        return tequila_cr["spec"]["oidc"]["clientID"]

    @classmethod
    def as_satosa_client_db_entry (cls, tequila_cr):
        return dict(
            client_id=cls.get_client_id(tequila_cr),
            token_endpoint_auth_method="none",
            response_types=["code"],
            redirect_uris=[uri for uri in tequila_cr["spec"]["oidc"]["redirectURIs"]],
            tequila_requires=[
                cls.as_tequila_require_formula(r)
                for r in tequila_cr["spec"]["tequila"]["requires"]],
            extra_id_token_claims=[
                claim_name for claim_name in tequila_cr["spec"]["oidc"]["extraIDTokenClaims"]
            ])

    @classmethod
    def as_tequila_require_formula(cls, require):
        if "or" in require:
            return "|".join(cls.as_tequila_require_formula(r)
                            for r in require["or"])
        else:
            return "%s=%s" % (require["key"], require["value"])
