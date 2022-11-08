# -*- coding: utf-8 -*-
import logging

import csv
import time
from collections import defaultdict

from six import iteritems

from config import FITBIT_SYNC_ENABLED, DATETIME_FORMAT, WEIGHT_LOG_LOCATION
from fitbit_oauth_user_client import FitBitOAuth2UserClient
from weight_logger.weight_logger import get_unsynced_weight_data, process_weight_line, get_csv_file_options

WEIGHT_SYNC_LOOP_TIME_SECS = 30  # How often to attempt weight logging on FitBit


def update_weight_sync_status(weight_data_synced):
    updated_rows = list()
    # Read entire file and update synced status for each weight that matches the data passed as the argument
    with open(WEIGHT_LOG_LOCATION) as weight_log:
        weight_reader = csv.reader(weight_log, **get_csv_file_options())
        header = True
        for weight_line in weight_reader:
            if header:
                header = False
                updated_rows.append(weight_line)
                continue

            # Process line to get the stored weight data
            user_id, weight, date_logged, synced = process_weight_line(weight_line)
            line_data = {
                'user_id': user_id,
                'weight': weight,
                'date_logged': date_logged.strftime(DATETIME_FORMAT),
                'synced': synced,
            }
            if not synced:
                # Check if user, weight and date matches any of the data passed as the just synced weight argument
                line_data['synced'] = any(all(
                    line_data[k] == entry_in_weight_data_synced[k] for k in ('user_id', 'weight', 'date_logged')
                ) for entry_in_weight_data_synced in weight_data_synced)

            updated_rows.append((line_data['user_id'], line_data['weight'], date_logged, line_data['synced']))
    weight_log.close()

    # Replace entire file with updated data
    with open(WEIGHT_LOG_LOCATION, 'w') as weight_log:
        csv_writer = csv.writer(weight_log, **get_csv_file_options())
        for row in updated_rows:
            csv_writer.writerow(row)
    weight_log.close()


def main():
    """ Attempts to get non-synchronized data from weight data file and synchronize it with FitBit """
    logging.info('Starting FitBit weight synchronisation thread')
    if not FITBIT_SYNC_ENABLED:
        return

    while True:
        unsynced_weight_data = get_unsynced_weight_data()
        if not unsynced_weight_data:
            time.sleep(WEIGHT_SYNC_LOOP_TIME_SECS)
            continue
        # Group weight data by user
        weight_data_by_user = defaultdict(lambda: list())
        for weight_data in unsynced_weight_data:
            uid = weight_data.pop('user_id')
            weight_data_by_user[uid].append(weight_data)

        weight_logged = list()
        for user_id, weight_data in iteritems(weight_data_by_user):
            client = FitBitOAuth2UserClient(user_id)
            if not client.is_authorised():
                continue
            for single_weight_data in weight_data:
                logged = client.log_user_weight(weight=single_weight_data['weight'], date=single_weight_data['date_logged'])
                if not logged:
                    # Failed to sync data, fails silently, debugging is required. Most likely due to authorization issues.
                    continue
                logged_weight_data = single_weight_data
                logged_weight_data.update({'user_id': user_id, 'date_logged': single_weight_data['date_logged'].strftime(DATETIME_FORMAT)})
                weight_logged.append(logged_weight_data)

        update_weight_sync_status(weight_logged)
        time.sleep(WEIGHT_SYNC_LOOP_TIME_SECS)


if __name__ == "__main__":
    main()
