from datetime import datetime
import functools
import logging
import re
import requests
import socket
from satosa.base import STATE_KEY as STATE_KEY_BASE
from satosa.exception import SATOSAError, SATOSAAuthenticationError
from satosa.internal import AuthenticationInformation, InternalData

from satosa.response import Redirect
from satosa.backends.base import BackendModule

logger = logging.getLogger(__name__)


class TequilaBackend(BackendModule):
    """A SATOSA back-end to authenticate against Tequila."""

    def __init__(self, auth_callback_func, internal_attributes, config, base_url, name):
        """
        Sign in with Tequçila.
        :param auth_callback_func: Callback should be called by the module after the authorization
        in the backend is done.
        :param internal_attributes: Mapping dictionary between SATOSA internal attribute names and
        the names returned by underlying IdP's/OP's as well as what attributes the calling SP's and
        RP's expects namevice.
        :param config: Configuration parameters for the module.
        :param base_url: base url of the service
        :param name: name of the plugin

        :type auth_callback_func:
        (satosa.context.Context, satosa.internal.InternalData) -> satosa.response.Response
        :type internal_attributes: dict[string, dict[str, str | list[str]]]
        :type config: dict[str, dict[str, str] | list[str]]
        :type base_url: str
        :type name: str
        """
        super().__init__(auth_callback_func, internal_attributes, base_url, name)

    def register_endpoints(self):
        return [
            ("/back-from-tequila",
             self._handle_back_from_tequila)
        ]

    def start_auth(self, context, request_info):
        """
        See super class method satosa.backends.base#start_auth
        :type context: satosa.context.Context
        :type request_info: satosa.internal.InternalData
        """
        teq = _TequilaProtocol()
        client_name = context.state.state_dict[STATE_KEY_BASE]['requester']
        back_from_tequila_uri = "%s/%s/back-from-tequila" % (
            self.base_url,
            self.name)
        return Redirect(teq.createrequest(client_name, back_from_tequila_uri,
                                          # TODO: should be figured out either from the OIDC scope, or from the JSON client table, or both
                                          request="name,firstname,lastname,email,group"
                                          ))

    def _handle_back_from_tequila(self, context, *unused_args):
        """
        Handles the browser returning from Tequila upon successful authentication.
        :type context: satosa.context.Context
        :rtype: satosa.response.Response

        :param context: SATOSA context
        :return:
        """
        auth_details = _TequilaProtocol().fetchattributes(
            context.request['key'])
        if "group" in auth_details:
            auth_details["group"] = auth_details["group"].split(",")
        logger.debug("Back from Tequila with %s", auth_details)

        auth_info = AuthenticationInformation(
            "tequila",
            timestamp=datetime.utcnow().timestamp())

        internal_resp = InternalData(
            auth_info=auth_info,
            attributes=_arrayify_values(auth_details),
            subject_type=None,
            subject_id="tequila")

        return self.auth_callback_func(context, internal_resp)


class _TequilaProtocol(object):
    """Headless implementation of the Tequila protocol.
    Follows the terminology of [Lecommandeur-eunis-2005]; functions
    are named after the URLs on the Tequila server (see also
    [Lecommandeur-WritingClients]).

    [Lecommandeur-eunis-2005] Tequila. A distributed Web
    authentication and access control tool, Claude Lecommandeur,
    Ecole Polytechnique Fédérale de Lausanne, EUNIS 2005

    [Lecommandeur-WritingClients] Tequila: Writing Clients,
    https://tequila.epfl.ch/download/2.0/docs/writing-clients.odt

    [mod_tequila-config] Apache Module - Tequila Identity Management,
    https://tequila.epfl.ch/download/2.0/docs/apache-module-config.pdf
    """

    @functools.cached_property
    def tequila_host(self):
        hostparts = ".".split(socket.gethostname())
        hostparts[0] = "tequila"
        if len(hostparts) == 1:
            # We may be in a container. Take a guess.
            return "tequila.epfl.ch"
        else:
            return ".".join(hostparts)

    @functools.cached_property
    def tequila_port(self):
        return 443

    @functools.cached_property
    def tequila_protocol(self):
        return "https"

    def _tequila_uri(self, cgi_basename):
        return "%s://%s:%d/cgi-bin/tequila/%s" % (
            self.tequila_protocol,
            self.tequila_host, self.tequila_port, cgi_basename)

    @functools.cached_property
    def tequila_createrequest_uri(self):
        return self._tequila_uri("createrequest")

    @functools.cached_property
    def tequila_requestauth_uri(self):
        # Not "requestauth", as erroneously stated in
        # [Lecommandeur-WritingClients]:
        return self._tequila_uri("auth")

    @functools.cached_property
    def tequila_fetchattributes_uri(self):
        # Not /requestauth, as erroneously stated in
        # [Lecommandeur-WritingClients]:
        return self._tequila_uri("fetchattributes")

    @functools.cached_property
    def tequila_logout_uri(self):
        return self._tequila_uri("logout")

    def createrequest(self, service, redirect_url, require=None, request=None):
        """
        Obtain an initial authentication ticket from the Tequila server.

        This is step 1 of § 2, "Local authentication" in [Lecommandeur-eunis-2005].
        :param service: The app-provided service name (like TequilaService in [mod_tequila-config])
        :param redirect_url: The location that Tequila should tell the browser to go back to, once authentication succeeds
        :param require: A filter expression (e.g. "username=~.") (like TequilaAllowIf in [mod_tequila-config])
        :param request: A list of user identity fields to fetch, e.g. ['name', 'firstname']
                (like TequilaRequest in [mod_tequila-config])

        :property service: The app-provided service name (like TequilaService in [mod_tequila-config])
        :property tequila_host: The host name of the Tequila server
        :property tequila_port: The port number of the Tequila server (HTTP/S is mandatory)
        """
        createrequest_args = dict(
            client="SATOSA TequilaBackend",
            service=service,
            urlaccess=redirect_url)

        if request is not None:
            createrequest_args["request"] = request

        if require is not None:
            createrequest_args["require"] = require

        uri = self.tequila_createrequest_uri
        data = _dict2txt(createrequest_args)

        logger.debug("Sending to %s: %s" % (uri, data))

        response = requests.post(uri,
                                 data=data,
                                 headers={"Content-Type": "text/plain"})

        if response.status_code == 200:
            parsed_response = _txt2dict(response.text)
            redirect_to = self._tequila_redirect_uri(parsed_response)
            logger.debug("Redirecting to %s", redirect_to)
            return redirect_to
        else:
            raise SATOSAError("Tequila is in a bad mood? Response: %s" %
                              response.text)

    def _tequila_redirect_uri(self, parsed_response):
        return "%s?requestkey=%s" % (
            self.tequila_requestauth_uri, parsed_response['key'])

    def fetchattributes(self, key):
        fetchattributes_args = dict(key=key)

        uri = self.tequila_fetchattributes_uri
        data = _dict2txt(fetchattributes_args)

        response = requests.post(uri,
                                 data=data,
                                 headers={"Content-Type": "text/plain"})
        if response.status_code == 200:
            return _txt2dict(response.text)
        else:
            raise SATOSAError("Tequila: negative response from fetchattributes (code %d): %s" %
                              (response.status_code, response.text))


def _dict2txt(dict):
    return "".join("%s=%s\n" % item for item in dict.items())

def _txt2dict(tequila_response):
    returned = {}
    for line in tequila_response.split("\n"):
        line = re.sub(r'\r$', '', line)
        matched = re.match(r'^(.*?)=(.*)$', line)
        if matched:
            returned[matched[1]] = matched[2]

    return returned


def _arrayify_values(dict_):
    return dict((k, v if isinstance(v, list) else [v]) for k, v in dict_.items())
