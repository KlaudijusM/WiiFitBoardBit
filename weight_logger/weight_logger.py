# -*- coding: utf-8 -*-

from six import iteritems
from datetime import datetime
from config import DATE_FORMAT, ALLOWED_WEIGHT_FLUCTUATION_KG, WEIGHT_LOG_LOCATION


def create_weight_log_entry(user_id, weight, date_logged):
    weight_log = open(WEIGHT_LOG_LOCATION, "a")
    weight_line = "\n{},{:.2f},{},False".format(user_id, weight, date_logged.strftime(DATE_FORMAT))
    weight_log.write(weight_line)
    weight_log.close()


def log_weight(weight):
    user_id = determine_user_id_by_weight(weight)
    log_date = datetime.utcnow()
    create_weight_log_entry(user_id, weight, log_date)


def determine_user_id_by_weight(weight):
    latest_weight_by_user = get_latest_weight_by_user()
    if not latest_weight_by_user:
        return 1  # No users have logged their weight - asuume it's the first user
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
        header = True
        for weight_line in weight_log:
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
        header = True
        for weight_line in weight_log:
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
    weight_line = weight_line.lstrip().rstrip()
    if not weight_line:
        return [None] * 4
    line_data = weight_line.split(',')
    if not line_data or len(line_data) != 4:
        return [None] * 4
    user_id = int(line_data[0].strip())
    weight = round(float(line_data[1].strip()), 2)
    date_logged = datetime.strptime(line_data[2], DATE_FORMAT)
    synced = line_data[3].strip() == "True"
    return user_id, weight, date_logged, synced
