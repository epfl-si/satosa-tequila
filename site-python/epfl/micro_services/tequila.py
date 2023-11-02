import logging

from satosa.micro_services.base import ResponseMicroService

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
        return callback_orig(self.context, self.data)
