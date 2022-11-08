# -*- coding: utf-8 -*-
import logging

from flask import Flask, redirect, render_template, request
from flask_bootstrap import Bootstrap

from config import FITBIT_SYNC_ENABLED

from fitbit_oauth_user_client import FitBitOAuth2UserClient


app = Flask(__name__)
Bootstrap(app)


@app.route('/')
def no_route():
    return redirect('/fitbit_auth')


@app.route('/fitbit_auth')
def fitbit_auth():
    return render_template('fitbit_auth.html')


@app.route('/fitbit_auth_new_user')
def fitbit_auth_new_user():
    return redirect('/fitbit_auth/1')


@app.route('/fitbit_auth/<user_id>')
def fitbit_auth_user(user_id):
    if not user_id or not isinstance(user_id, int):
        redirect('/fitbit_auth')
    client = FitBitOAuth2UserClient(user_id)
    return redirect(client.get_authorization_url())


@app.route('/fitbit_auth_redirect')
def auth_token_handle():
    user_id, code = request.args['state'], request.args['code']
    if not user_id or not code:
        return 'Nay'
    client = FitBitOAuth2UserClient(user_id)
    client.fetch_and_store_access_token(code)
    return 'Yay'


def main():
    logging.info("Starting FitBit Authentication web server (FBAS)")
    if FITBIT_SYNC_ENABLED:  # No point in running this server if FitBit sync is not enabled
        app.run(port=8080)


if __name__ == "__main__":
    main()
