# -*- coding: utf-8 -*-
import json
import os.path as os_path
import urllib

from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session

from compliance import fitbit_compliance_fix
from config import FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET


class FitBitOAuth2UserClient:
    API_ENDPOINT = "https://api.fitbit.com"
    AUTHORIZE_ENDPOINT = "https://www.fitbit.com"
    API_VERSION = 1

    request_token_url = "%s/oauth2/token" % API_ENDPOINT
    authorization_url = "%s/oauth2/authorize" % AUTHORIZE_ENDPOINT
    access_token_url = request_token_url
    refresh_token_url = request_token_url
    user_data_file_location = './fitbit_sync/auth_data/'
    redirect_url = "http://127.0.0.1:8080/fitbit_auth_redirect"

    US = 'en_US'
    METRIC = 'en_UK'

    def __init__(self, user_id):
        self.user_id = user_id
        self.auth_data_file_location = os_path.join(self.user_data_file_location, 'user_{}.txt'.format(self.user_id))
        self.client_id, self.client_secret = FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET
        self.access_token, self.refresh_token, self.expires_at = self._read_user_token_data()
        self.session = self._initiate_oauth_session()

    def is_authorised(self):
        return self._check_user_authorisation()

    def _check_user_authorisation(self):
        if not self.client_id:
            return False
        elif not self.client_secret:
            return False
        return True

    def _read_user_token_data(self):
        # Reads user token data from file
        access_token = refresh_token = expires_at = None
        if not os_path.isfile(self.auth_data_file_location):
            return access_token, refresh_token, expires_at
        with open(self.auth_data_file_location, 'r') as user_auth_file:
            auth_data_line = user_auth_file.readline()
            if auth_data_line and len(auth_data_line) > 0:
                parsed_auth_data = auth_data_line.split(',')
                access_token = parsed_auth_data[0]
                if len(parsed_auth_data) > 1:
                    refresh_token = parsed_auth_data[1]
                if len(parsed_auth_data) > 2:
                    expires_at = parsed_auth_data[2]
        return access_token, refresh_token, expires_at

    def _initiate_oauth_session(self):
        if not self.is_authorised():
            return False
        session = fitbit_compliance_fix(OAuth2Session(
            self.client_id,
            redirect_uri='{}/{}'.format(self.redirect_url, self.user_id),
            token_updater=self.do_store_token,
            scope=u'weight',
        ))
        session.token = self.get_stored_token()
        session.authorization_url = self.authorization_url
        return session

    def fetch_and_store_access_token(self, code):
        self.session.fetch_token(
            self.access_token_url,
            username=self.client_id,
            password=self.client_secret,
            client_secret=self.client_secret,
            code=code)
        self.do_refresh_token()
        return

    def do_refresh_token(self):
        """Step 3: obtains a new access_token from the the refresh token
        obtained in step 2. Only do the refresh if there is `token_updater(),`
        which saves the token.
        """
        token = {}
        if self.session.token_updater:
            token = self.session.refresh_token(
                self.refresh_token_url,
                auth=HTTPBasicAuth(self.client_id, self.client_secret),
            )
            self.session.token_updater(token)
        return token

    def do_store_token(self, token):
        with open(self.auth_data_file_location, 'w') as user_auth_file:
            user_auth_file.write(json.dumps(token))

    def get_stored_token(self):
        if not os_path.isfile(self.auth_data_file_location):
            return {}
        with open(self.auth_data_file_location, 'r') as user_auth_file:
            return json.loads(user_auth_file.readline())

    def get_authorization_url(self):
        if not self.session:
            return False
        url_data = {
            'scope': self.session.scope,
            'client_id': self.client_id,
            'response_type': 'code',
            'state': self.user_id,
        }
        url = '{}?{}'.format(self.session.authorization_url, urllib.urlencode(url_data))
        return url

    def log_user_weight(self, weight, date):
        if not self.is_authorised():
            return False
        if not self.session:
            self.session = self._initiate_oauth_session()
        if not self.session:
            return False

        url = '{}/{}/user/-/body/log/weight.json'.format(self.API_ENDPOINT, self.API_VERSION)

        data = {
            'weight': weight,
            'date': date.strftime('%Y-%m-%d'),
            'time': date.strftime('%H:%M:%S'),
        }

        method = 'POST'

        request = {
            'headers': {'Accept-Language': self.METRIC},
            'data': data,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        try:
            response = self.session.request(method, url, **request)

            if response.status_code == 401:
                d = json.loads(response.content.decode('utf8'))
                if d['errors'][0]['errorType'] == 'expired_token':
                    self.refresh_token()
                    response = self.session.request(method, url, **request)

            return response.status_code == 202 or response.status_code == 201
        except Exception as e:
            return False
