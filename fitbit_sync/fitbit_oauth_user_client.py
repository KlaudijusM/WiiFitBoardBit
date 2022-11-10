# -*- coding: utf-8 -*-
import json
import logging
import urllib

from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session

from config import FITBIT_SYNC_ENABLED, FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET, UNITS
from fitbit_sync.user import FitBitUser
from fitbit_sync.utils.compliance import fitbit_compliance_fix


class FitBitOAuth2UserClient:
    API_ENDPOINT = "https://api.fitbit.com"
    AUTHORIZE_ENDPOINT = "https://www.fitbit.com"
    API_VERSION = 1

    request_token_url = "%s/oauth2/token" % API_ENDPOINT
    authorization_url = "%s/oauth2/authorize" % AUTHORIZE_ENDPOINT
    access_token_url = request_token_url
    refresh_token_url = request_token_url

    redirect_url = "http://127.0.0.1:8080/fitbit_auth_redirect"
    client_id = FITBIT_CLIENT_ID
    client_secret = FITBIT_CLIENT_SECRET

    scope = u'weight'

    US = 'en_US'
    METRIC = 'en_UK'

    def __init__(self, user_id):
        self.user_id = user_id
        self.user = FitBitUser(user_id)
        self.session = self._initiate_oauth_session()

    def is_authorised(self):
        """ Check if the app is authorised """
        return self._check_app_authorisation()

    def _check_app_authorisation(self):
        """ Check if the FitBit App settings are set """
        if not FITBIT_SYNC_ENABLED:
            return False
        elif not self.client_id:
            return False
        elif not self.client_secret:
            return False
        return True

    def _initiate_oauth_session(self):
        """ Initiates OAuth 2 session """
        if not self.is_authorised():
            return False
        session = fitbit_compliance_fix(OAuth2Session(
            self.client_id,
            redirect_uri='{}/{}'.format(self.redirect_url, self.user_id),
            token_updater=self.do_store_token,
            scope=self.scope,
        ))
        stored_token = self.get_stored_token()
        if stored_token:
            session.token = stored_token
        session.authorization_url = self.authorization_url
        return session

    def get_stored_token(self):
        """ Checks if the user has a stored token and returns it """
        if not self.user.user_data:
            return {}
        return self.user.user_token

    def fetch_and_store_refresh_token(self, code):
        """ Fetches FitBit OAuth2 refresh token and stores it """
        self.session.fetch_token(
            self.access_token_url,
            username=self.client_id,
            password=self.client_secret,
            client_secret=self.client_secret,
            code=code)
        self.do_refresh_token()
        return

    def do_refresh_token(self):
        """ Refreshes access token based on user refresh token if needed """
        token = {}
        if self.session.token_updater:
            token = self.session.refresh_token(
                self.refresh_token_url,
                auth=HTTPBasicAuth(self.client_id, self.client_secret),
            )
            self.session.token_updater(token)
        return token

    def do_store_token(self, token):
        """ Saves user token info and stores it """
        self.user.user_token = token
        self.user.store_user_data()

    def get_authorization_url(self):
        """ Gets the user authorisation URL """
        if not self.session:
            return False
        url_data = {
            'scope': self.scope,
            'client_id': self.client_id,
            'response_type': 'code',
            'state': self.user.generate_new_user_csrf_token(),
        }
        url = '{}?{}'.format(self.authorization_url, urllib.urlencode(url_data))
        return url

    def log_user_weight(self, weight, date):
        """
        Sends a POST request to FitBit to log user weight for the specified date
        @type weight: float
        @param weight: weight to log
        @type date: datetime.datetime
        @param date: datetime object for which to store the date
        """
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
            'headers': {'Accept-Language': self.METRIC if UNITS == 'METRIC' else self.US},
            'data': data,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        try:
            response = self.session.request(method, url, **request)

            if response.status_code == 401:
                d = json.loads(response.content.decode('utf8'))
                if d['errors'][0]['errorType'] == 'expired_token':
                    self.do_refresh_token()
                    response = self.session.request(method, url, **request)

            success = response.status_code == 202 or response.status_code == 201
        except Exception as e:
            success = False

        if success:
            logging.info("Successfully logged weight {:.2f} for user {} on FitBit".format(weight, self.user.user_name))
        else:
            logging.info("Failed logging weight {:.2f} for user {}. Please check user authentication".format(
                weight, self.user.user_name or self.user.user_id)
            )
        return success
