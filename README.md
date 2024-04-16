# satosa-tequila

OpenID-Connect (OIDC) bridge as-a-service to Tequila (SAML), built on top of [SATOSA](https://github.com/IdentityPython/SATOSA/).

## Development Rig

1. Copy and adapt `data/clients.json.sample` into `data/clients.json`
2. **Make sure your port 443 is free** — `service apache stop`, remove any Docker containers that might be occupying it, etc
3. Clone the repository and start up the development container using the following command:
   ```bash
   make down up logs
   ```
4. Browse https://satosa-127-0-0-1.nip.io/.well-known/openid-configuration and override the security warning caused by the development rig using a bogus certificate. (💡 You will only have to do this once per browser, until you `make clean`)
5. We suggest https://github.com/epfl-si/rails.starterkit as the demo OpenID-Connect application. Clone it somewhere else and apply the following diff to it:
   ```diff
   diff --git a/config/oidc.yml b/config/oidc.yml
   index bd338c1..b9a2c3a 100644
   --- a/config/oidc.yml
   +++ b/config/oidc.yml
   @@ -7,5 +7,5 @@ oidc_config: &oidc_config
        # this structure is available to anyone who issues an
        # unauthenticated GET to `/oidc/config` (see
        # app/controllers/OIDC/frontend_config_controller.rb)
   -    auth_server: <%= ENV.fetch("OIDC_SERVER_URL") { "http://localhost:8080/realms/rails/" } %>
   +    auth_server: <%= ENV.fetch("OIDC_SERVER_URL") { "https://satosa-127-0-0-1.nip.io/" } %>
   ```
6. Edit the same file (`config/oidc.yml` in your cloned `rails.starterkit` repository), uncomment the `auth_server_certificate:` section and replace the bogus certificate found there with the contents of the `tls/satosa.crt` file (found below this `README.md` after step 2)
7. Fire up the Rails application with `./bin/dev`
8. (Optional, but recommended) install the SAML-tracer browser extension ([for Chrome](https://chrome.google.com/webstore/detail/saml-tracer/mpdajninpobndbfcldcmbpnnbhibjmch), [for Firefox](https://addons.mozilla.org/fr/firefox/addon/saml-tracer/))
9. Browse the Rails application at http://localhost:3000/ and try out the Login button.
