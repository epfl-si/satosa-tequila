import json
import logging
import time
from satosa.frontends.openid_connect import OpenIDConnectFrontend as SATOSAOpenIDConnectFrontend


logger = logging.getLogger(__name__)


class OpenIDConnectFrontend(SATOSAOpenIDConnectFrontend):
    def __init__(self, auth_req_callback_func, internal_attributes, conf, base_url, name):
        """Overloaded to implement continuous reload of the JSON database."""
        super().__init__(auth_req_callback_func, internal_attributes, conf, base_url, name)

        db_type = self.config.get("client_db", {}).get("type")
        if db_type.lower() == "json":
            json_path = self.config["client_db"]["path"]
            logger.info("Will be loading OIDC client database from %s" % json_path)

            self.provider.clients = _CachingDictish(_JSONDB(json_path))

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

    def get_all(self):
        logger.debug("Reloading JSON from %s" % self.json_file)
        with open(self.json_file, 'r') as f:
            return json.load(f)
