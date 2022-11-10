# -*- coding: utf-8 -*-

import hashlib
import hmac
import json
import os
import os.path as os_path
from datetime import datetime, timedelta

from config import DATETIME_FORMAT

user_data_file_location = './fitbit_sync/auth_data/'


def get_user_file_location(user_id):
    return os_path.join(user_data_file_location, 'user_{}.json'.format(user_id))

# General class to read/write user data from json file


class FitBitUser:

    csrf_secret = 'WiiFitBoardBit'

    def __init__(self, user_id):
        """
        @type user_id: int
        @param user_id: user id to load
        """
        self.user_id = user_id
        self.user_exists = False
        self.auth_data_file_location = get_user_file_location(user_id)
        self.user_data = self._get_user_data_data_from_file()
        self.user_name = self._get_user_name()
        self.user_token = self._get_user_token()
        self.csrf_token = self._get_user_csrf_token()

    def _get_user_data_data_from_file(self):
        """ Reads user data from json file """
        if not os_path.isfile(self.auth_data_file_location):
            return {}
        user_auth_file = open(self.auth_data_file_location, 'r')
        user_data = json.loads(user_auth_file.read())
        user_auth_file.close()
        if user_data:
            self.user_exists = True
        return user_data

    def _get_user_name(self):
        """ Gets username from loaded data """
        return self.user_data.get('user_name')

    def _get_user_token(self):
        """ Gets token from loaded data """
        return self.user_data.get('token_data')

    def _get_user_csrf_token(self):
        """ Gets csrf token from loaded data """
        return self.user_data.get('csrf_token')

    def check_user_csrf_validity(self, csrf_to_check):
        """
        Checks if the provided csrf token matches the stored token of the user
        @type csrf_to_check: str
        @param csrf_to_check: csrf string token to check
        """
        if not self.csrf_token or not isinstance(csrf_to_check, basestring):
            return False
        try:
            expires, provided_csrf = self.csrf_token.split('##')
        except IndexError:
            return False

        if not expires or not provided_csrf:
            return False

        _, current_csrf = self.csrf_token.split('##')

        return hmac.compare_digest(current_csrf, provided_csrf)

    def store_user_data(self):
        """ Stores user data from memory to file """
        with open(self.auth_data_file_location, 'w') as user_data_file:
            user_data_file.write(json.dumps({
                'user_id': self.user_id,
                'user_name': self.user_name,
                'token_data': self.user_token,
                'csrf_token': self.csrf_token
            }))

    def generate_new_user_csrf_token(self):
        """ Generates a new csrf token for the user and stores it """
        expires = (datetime.now() + timedelta(minutes=1)).strftime(DATETIME_FORMAT)
        csrf = '{}{}'.format(hashlib.sha1(os.urandom(64)).hexdigest(), expires)
        hmac_csrf = hmac.new(self.csrf_secret, csrf.encode('utf8'), digestmod=hashlib.sha1)
        csrf_token = '{}##{}'.format(expires, hmac_csrf.hexdigest())
        self.csrf_token = csrf_token
        self.store_user_data()
        return csrf_token


def create_new_fitbit_user(user_name):
    """
    Finds empty user_id and creates a new user record
    @type user_name: str
    @param user_name: username to save on user record
    @return (int) created user id
    """
    empty_user_id = None
    for user_id in range(1, 1000):
        if not os_path.isfile(get_user_file_location(user_id)):
            empty_user_id = user_id
            user = FitBitUser(user_id)
            user.user_name = user_name
            user.store_user_data()
            break
    return empty_user_id


def get_all_existing_fitbit_users():
    """
    Gets all existing users
    @return (list(dict)) a list of all basic user data - user_id and user_name
    """
    existing_users = list()
    for user_id in range(1, 1000):
        if os_path.isfile(get_user_file_location(user_id)):
            user = FitBitUser(user_id)
            if not user.user_exists:
                continue
            existing_users.append({'user_id': user_id, 'user_name': user.user_name})
    return existing_users


def get_user_id_by_csrf(csrf):
    """
    Reads all user data files to determine which user matches the CSRF token
    @type csrf: str
    @param csrf: csrf token to check
    """
    matched_user_id = False
    for user_id in range(1, 1000):
        if os_path.isfile(get_user_file_location(user_id)):
            user = FitBitUser(user_id)
            if not user.user_exists:
                continue
            if user.check_user_csrf_validity(csrf):
                matched_user_id = user_id
                break
    return matched_user_id
