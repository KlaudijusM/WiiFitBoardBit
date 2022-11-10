# -*- coding: utf-8 -*-
# From https://github.com/orcasgit/python-fitbit/blob/master/fitbit/compliance.py
from json import loads, dumps

from oauthlib.common import to_unicode


def fitbit_compliance_fix(session):

    def _missing_error(r):
        token = loads(r.text)
        if 'errors' in token:
            # Set the error to the first one we have
            token['error'] = token['errors'][0]['errorType']
        r._content = to_unicode(dumps(token)).encode('UTF-8')
        return r

    session.register_compliance_hook('access_token_response', _missing_error)
    session.register_compliance_hook('refresh_token_response', _missing_error)
    return session
