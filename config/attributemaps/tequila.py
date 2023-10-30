"""`saml_uri` attribute map plus Tequila-specific extensions.

There is one important detail that that documentation for attribute
maps (at
https://pysaml2.readthedocs.io/en/latest/howto/config.html?highlight=config#attribute-map-dir)
almost completely glosses over: there can be no two `attribute_maps`
Python definitions with the same `MAP.identifier`, lest one of them
clobber the other! (See e.g.
https://github.com/IdentityPython/pysaml2/blob/master/src/saml2/attribute_converter.py#L138)

Therefore, this file copies and overloads the `MAP` dict from the
saml2.attributemaps.saml_uri module, adding nonstandard Tequila-specific attribute statements
such as `EPFLgroups`.
"""

from saml2.attributemaps.saml_uri import MAP as saml_uri_map
from copy import deepcopy

MAP = deepcopy(saml_uri_map)

MAP["fro"]["EPFLgroups"] = "epflGroups"
