# -*- coding: utf-8 -*-
import logging

from flask import Flask, redirect, render_template, request
from flask_bootstrap import Bootstrap

from config import FITBIT_SYNC_ENABLED

from fitbit_oauth_user_client import FitBitOAuth2UserClient
from fitbit_sync.user import create_new_fitbit_user, get_all_existing_fitbit_users, get_user_id_by_csrf

app = Flask(__name__)
Bootstrap(app)


@app.route('/')
def no_route():
    return redirect('/fitbit_auth')


@app.route('/fitbit_auth')
def fitbit_auth():
    return render_template('fitbit_auth.html', user_data=get_all_existing_fitbit_users())


# User routes
@app.route('/create_new_user')
def create_new_user():
    return render_template('new_user.html')


@app.route('/fitbit_create_user', methods=['POST'])
def fitbit_create_user():
    user_name = request.form['user_name']
    if not user_name or not isinstance(user_name, basestring):
        return fitbit_auth()
    user_id = create_new_fitbit_user(user_name)
    return redirect('/fitbit_auth/{}'.format(user_id))


@app.route('/fitbit_auth/<user_id>')
def fitbit_auth_user(user_id):
    if not user_id:
        return redirect('/fitbit_auth')
    try:
        user_id = int(user_id)
    except Exception:
        return fitbit_auth()
    client = FitBitOAuth2UserClient(user_id)
    return redirect(client.get_authorization_url())


@app.route('/fitbit_auth_redirect')
def auth_token_handle():
    state, code = request.args['state'], request.args['code']
    if not state or not code:
        logging.warning("[FBAS] Could not get state or code!")
        return redirect('/fitbit_auth')
    user_id = get_user_id_by_csrf(state)
    if not user_id:
        return redirect('/fitbit_auth')
    client = FitBitOAuth2UserClient(user_id)
    client.fetch_and_store_refresh_token(code)
    return redirect('/successfully_authorised')


@app.route('/successfully_authorised')
def successfully_authorised():
    return render_template('successfully_authorised.html')


def main():
    logging.info("Starting FitBit Authentication web server (FBAS)")
    if FITBIT_SYNC_ENABLED:  # No point in running this server if FitBit sync is not enabled
        app.run(port=8080)


if __name__ == "__main__":
    main()
