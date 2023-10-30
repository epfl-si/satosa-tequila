# Custom WSGI entry point for SATOSA
# Adds CORS support

import logging
import pprint

from werkzeug.wrappers import Response
from satosa.wsgi import app as app_orig

logger = logging.getLogger(__name__)

class CORSMiddleware(object):
    """Add suitable CORS (cross-origin resource sharing) headers to all responses."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        def start_response_with_cors_headers(status, headers, *args, **kwargs):
            headers.append(('Access-Control-Allow-Origin', "*"))
            return start_response(status, headers,  *args, **kwargs)
        return self.app(environ, start_response_with_cors_headers)

app = CORSMiddleware(app_orig)
