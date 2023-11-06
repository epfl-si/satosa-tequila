import json
import logging

from satosa.micro_services.base import ResponseMicroService
from satosa.exception import SATOSAAuthenticationError

logger = logging.getLogger(__name__)


class TequilaRequire(ResponseMicroService):
    """
    Honor Tequila-style `require` clause in the JSON configuration
    """
    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = config

    def process(self, context, data):
        return TequilaRequireProcessor(self.config, context, data).process(super().process)


class TequilaRequireProcessor(object):
    def __init__(self, config, context, data):
        self.config = config
        self.context = context
        self.data = data

    def process(self, callback_orig):
        if not self.backend_is_tequila:
            return callback_orig(self.context, self.data)

        requirement_set = self.requirement_set
        if not requirement_set:
            return callback_orig(self.context, self.data)

        groups = self.saml_groups
        if not groups:
            self.authentication_failed("Requirements cannot be checked - Please add `tequila` to the requested scopes in your OIDC client")

        if not requirement_set.is_met(groups=groups):
            self.authentication_failed("You do not have access to this Web application.")

        return callback_orig(self.context, self.data)

    def authentication_failed(self, message):
        raise SATOSAAuthenticationError(self.context.state, message)

    @property
    def oidc_client_name(self):
        return self.data.data["requester"]

    @property
    def saml_groups(self):
        return self.data.data["attributes"].get("epflGroups")

    @property
    def requirement_set(self):
        client_db = self.client_db

        oidc_client_name = self.oidc_client_name
        if oidc_client_name not in self.client_db:
            self.authentication_failed("Unknown client %s" % oidc_client_name)

        try:
            return TequilaRequirementSet.from_config_list(
                self.client_db[oidc_client_name].get('tequila_requires'))
        except TequilaRequirementSetError as e:
            self.authentication_failed("Error in Tequila requirements: %s" % e)

    @property
    def openid_connect_frontend(self):
        from satosa.wsgi import app
        return app.app.app.module_router.frontends[self.openid_connect_frontend_slug]["instance"]

    @property
    def openid_connect_frontend_slug(self):
        return 'OIDC'   # As per ../../../config/openid_connect_frontend.yaml

    @property
    def backend_is_tequila(self):
        return self.context.target_backend == "tequila"

    @property
    def client_db_path(self):
        return self.openid_connect_frontend.config['client_db_path']

    # Load-once, because we need to restart whenever the JSON file changes anyway...
    _client_db_cache = None
    @property
    def client_db(self):
        if self.__class__._client_db_cache is None:
            self.__class__._client_db_cache = json.load(open(self.client_db_path))
        return self.__class__._client_db_cache

class TequilaRequirementSetError(Exception):
    pass

class TequilaRequirementClauseError(TequilaRequirementSetError):
    def __init__(self, message, clause_as_data):
        super(TequilaRequirementClauseError, self).__init__(
            '%s: %s' % (message, json.dumps(clause_as_data)))

class TequilaRequirementSet(object):
    @classmethod
    def from_config_list(cls, config_list):
        if not config_list:
            return None

        return cls([cls.RequireClause.construct(config) for config in config_list])

    def __init__(self, clauses):
        self.clauses = clauses

    def is_met(self, **user_details):
        for clause in self.clauses:
            if not clause.holds(**user_details):
                logger.debug("Failed clause: %s" % clause)
                return False
        return True

    class RequireClause(object):
        def __init__(self, clause_as_data):
            self.config = clause_as_data

        def __str__(self):
            return '<%s %s>' % (self.__class__.__name__,
                                json.dumps(self.config))

        @classmethod
        def fits_if_sole_key(self, key, clause_as_data):
            if key not in clause_as_data:
                return False
            if len(clause_as_data.keys()) > 1:
                raise TequilaRequirementClauseError(
                    "Cannot have another key besides %s" % key,
                    clause_as_data)
            return True

        @classmethod
        def construct(cls, clause_as_data):
            for subcls in cls.__subclasses__():
                if subcls.fits(clause_as_data):
                    return subcls(clause_as_data)
            raise TequilaRequirementClauseError(
                "Unknown Tequila requirement", clause_as_data)

    class GroupRequireClause(RequireClause):
        CONFIG_KEY = 'group'

        @classmethod
        def fits(cls, clause_as_data):
            return cls.fits_if_sole_key(cls.CONFIG_KEY, clause_as_data)

        def __init__(self, clause_as_data):
            super(TequilaRequirementSet.GroupRequireClause, self).__init__(
                clause_as_data)

        def holds(self, **args):
            return self.config[self.__class__.CONFIG_KEY] in args.get('groups', [])
