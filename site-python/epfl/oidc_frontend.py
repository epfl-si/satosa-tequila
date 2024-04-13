from satosa.frontends.openid_connect import OpenIDConnectFrontend as SATOSAOpenIDConnectFrontend

class OpenIDConnectFrontend(SATOSAOpenIDConnectFrontend):
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
