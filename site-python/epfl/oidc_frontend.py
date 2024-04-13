import json
import logging
import time
import kubernetes
from satosa.frontends.openid_connect import OpenIDConnectFrontend as SATOSAOpenIDConnectFrontend


logger = logging.getLogger(__name__)


class OpenIDConnectFrontend(SATOSAOpenIDConnectFrontend):
    def __init__(self, auth_req_callback_func, internal_attributes, conf, base_url, name):
        """Overloaded to implement continuous reload of the JSON database."""
        super().__init__(auth_req_callback_func, internal_attributes, conf, base_url, name)

        db_type = self.config.get("client_db", {}).get("type")
        if db_type.lower() == "json":
            json_path = self.config["client_db"]["path"]
            db = _JSONDB(json_path)
        elif db_type.lower() == "kubernetes":
            def provider_is_us (provider_url):
                return self.base_url.rstrip("/") == provider_url.rstrip("/")

            db = _KubernetesDB(provider_is_us)
        else:
            db = None

        if db:
            logger.info("Will be loading OIDC client database from %s" % repr(db))
            self.provider.clients = _CachingDictish(db)

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


class _CachingDictish(object):
    """Minimalist implementation of a dict, that caches all lookups for a few seconds."""
    def __init__(self, getter, timeout_seconds=2):
        self.getter = getter
        self.last_time_read = None
        self.timeout_seconds = timeout_seconds
        self.cached_data = None

    def data(self):
        now = time.time()
        if self.last_time_read and self.last_time_read + self.timeout_seconds > now:
            return self.cached_data
        else:
            self.cached_data = self.getter.get_all()
            self.last_time_read = now
            return self.cached_data

    def __getitem__(self, key):
        return self.data()[key]

    def __contains__(self, key):
        return key in self.data()

    def __repr__(self):
        return repr(self.data())


class _JSONDB(object):
    """A getter for `CachingDictish` that reads out of a JSON file."""
    def __init__(self, json_file):
        self.json_file = json_file

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, self.json_file)

    def get_all(self):
        logger.debug("Reloading JSON from %s" % self.json_file)
        with open(self.json_file, 'r') as f:
            return json.load(f)


class _KubernetesDB(object):
    """A getter for `CachingDictish` that reads `TequilaOIDCMapping`s."""
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
