# -*- coding: utf-8 -*-

import csv
from datetime import datetime
from threading import Thread

from six import iteritems

from config import DATE_FORMAT, ALLOWED_WEIGHT_FLUCTUATION_KG, WEIGHT_LOG_LOCATION
from fitbit_sync.fitbit_sync import sync_unsynced_weight


def get_csv_file_options():
    return {
        'delimiter': ',',
        'quotechar': '"',
        'quoting': csv.QUOTE_MINIMAL
    }


def create_weight_log_entry(user_id, weight, date_logged):
    with open(WEIGHT_LOG_LOCATION, 'a') as weight_log:
        csv_writer = csv.writer(weight_log, **get_csv_file_options())
        csv_writer.writerow([user_id, '{:.2f}'.format(weight), date_logged.strftime(DATE_FORMAT), False])


def log_weight(weight):
    log_date = datetime.utcnow()
    user_id = determine_user_id_by_weight(weight)
    create_weight_log_entry(user_id, weight, log_date)

    # Start fit bit weight synchronization thread
    fitbit_sync_thread = Thread(target=sync_unsynced_weight)
    fitbit_sync_thread.start()


def determine_user_id_by_weight(weight):
    latest_weight_by_user = get_latest_weight_by_user()
    if not latest_weight_by_user:
        return 1  # No users have logged their weight - assume it's the first user
    differences_by_user = list()
    for user_id, user_weight_data in iteritems(latest_weight_by_user):
        user_weight = user_weight_data.get('weight', 0.0)
        weight_difference = abs(user_weight - weight)
        differences_by_user.append((user_id, weight_difference))
    differences_by_user.sort(key=lambda dbu: dbu[1])  # Sort by smallest difference
    # Get what is the smallest weight difference and which user it belongs to
    user_id, smallest_difference = differences_by_user[0]
    if smallest_difference > ALLOWED_WEIGHT_FLUCTUATION_KG:
        # Difference exceeds the maximum allowed weight fluctuation. This means a new user has 
        # logged their weight.
        maximum_user_id = max(latest_weight_by_user.keys())
        return maximum_user_id + 1
    return user_id


def get_unsynced_weight_data():
    unsynced_data = list()
    with open(WEIGHT_LOG_LOCATION) as weight_log:
        weight_reader = csv.reader(weight_log, **get_csv_file_options())
        header = True
        for weight_line in weight_reader:
            if header:
                header = False
                continue  # Ignore header line

            # Process line to get the stored weight data
            user_id, weight, date_logged, synced = process_weight_line(weight_line)
            if not user_id:
                continue

            if not synced:
                unsynced_data.append({
                    'user_id': user_id, 'weight': weight, 'date_logged': date_logged,
                })
    return unsynced_data


def get_latest_weight_by_user():
    """ Loops through the log file and gets the latest date for each user """
    weights_by_user = dict()
    with open(WEIGHT_LOG_LOCATION) as weight_log:
        weight_reader = csv.reader(weight_log, **get_csv_file_options())
        header = True
        for weight_line in weight_reader:
            if header:
                header = False
                continue  # Ignore header line

            # Process line to get the stored weight data
            user_id, weight, date_logged, synced = process_weight_line(weight_line)
            if not user_id:
                continue

            latest_log_date = weights_by_user.get(user_id, dict()).get('date_logged')
            if latest_log_date and latest_log_date > date_logged:
                continue  # A newer entry is already stored as the latest weight

            # Add the processed line as the latest log date
            weights_by_user[user_id] = {
                'weight': weight, 'date_logged': date_logged, 'synced': synced
            }
    return weights_by_user


def process_weight_line(weight_line):
    if not weight_line or len(weight_line) != 4:
        return [None] * 4
    user_id = int(weight_line[0])
    weight = round(float(weight_line[1]), 2)
    date_logged = datetime.strptime(weight_line[2], DATE_FORMAT)
    synced = weight_line[3] == "True"
    return user_id, weight, date_logged, synced
