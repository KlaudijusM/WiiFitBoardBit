# -*- coding: utf-8 -*-

import csv
import logging
import os.path
from collections import defaultdict
from datetime import datetime

from six import iteritems

from config import DATETIME_FORMAT, ALLOWED_WEIGHT_FLUCTUATION_KG, WEIGHT_LOG_LOCATION, UNITS

WEIGHT_UNITS = 'kg' if UNITS == 'METRIC' else 'lbs'


def get_csv_file_options():
    return {
        'delimiter': ',',
        'quotechar': '"',
        'quoting': csv.QUOTE_MINIMAL
    }


def format_weight(weight):
    return '{:.2f}'.format(weight)


class WeightLogger:

    weight_log_data_file = os.path.join(WEIGHT_LOG_LOCATION)
    log_header_columns = ['user_id', 'weight', 'datetime', 'synced']

    @staticmethod
    def _process_weight_line(weight_line):
        if not weight_line or len(weight_line) != 4:
            return
        weight_data = {
            'user_id': int(weight_line[0]),
            'weight': round(float(weight_line[1]), 2),
            'date_logged': datetime.strptime(weight_line[2], DATETIME_FORMAT),
            'synced': weight_line[3] == 'True',
        }
        return weight_data

    @staticmethod
    def _format_weight_data_as_file_row(weight_data):
        return [
            weight_data['user_id'],
            format_weight(weight_data['weight']),
            weight_data['date_logged'].strftime(DATETIME_FORMAT),
            weight_data.get('synced', False)
        ]

    def __init__(self):
        self.weights = self._read_all_weights()

    def _create_new_weight_log(self):
        logging.info('[WL] Creating new weight log')
        weight_log = open(self.weight_log_data_file, "w")
        weight_log.write(','.join(self.log_header_columns) + '\n')
        weight_log.close()

    def _read_all_weights(self):
        logging.info('[WL] Attempting to read weights from log file')

        weights = list()

        if not os.path.isfile(self.weight_log_data_file):
            logging.info('[WL] Weight log file not found')
            self._create_new_weight_log()
            return weights

        with open(self.weight_log_data_file) as weight_log:
            weight_reader = csv.reader(weight_log, **get_csv_file_options())
            header = True
            for file_line in weight_reader:
                if header:
                    header = False
                    continue

                # Process line to get the stored weight data
                processed_weight_line = self._process_weight_line(file_line)
                if processed_weight_line:
                    weights.append(processed_weight_line)
        weight_log.close()

        logging.info('[WL] Found {} weight entries'.format(len(weights)))
        return weights

    def _add_weight(self, weight_data):
        self.weights.append(weight_data)

    def _create_single_weight_log_entry(self, weight_data):
        self._add_weight(weight_data)
        logging.info(
            "[WL] Writing weight log entry for user id {} ({} {})".format(
                weight_data['user_id'], weight_data['weight'], WEIGHT_UNITS
            )
        )
        with open(self.weight_log_data_file, 'a') as weight_log:
            csv_writer = csv.writer(weight_log, **get_csv_file_options())
            csv_writer.writerow(self._format_weight_data_as_file_row(weight_data))
        weight_log.close()

    def log_weight(self, weight):
        logging.info("Weight logging for weight {:.2f}, started (WL)".format(weight))
        self._create_single_weight_log_entry({
            'user_id': self.determine_user_id_by_weight(weight),
            'weight': weight,
            'date_logged': datetime.now(),
            'synced': False
        })

    def determine_user_id_by_weight(self, weight):
        logging.info(
            "[WL] Searching user by weight (allowed fluctuation {:.2f} {}.)".format(
                ALLOWED_WEIGHT_FLUCTUATION_KG, WEIGHT_UNITS
            )
        )
        latest_weight_by_user = self.get_latest_weights_by_user()
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
        logging.info("[WL] Weight assigned to user ID: {}".format(user_id))
        return user_id

    def get_weights_by_user(self):
        weights_by_user = defaultdict(lambda: list())
        for weight in self.weights:
            weights_by_user[weight['user_id']].append(weight)
        return weights_by_user

    def get_latest_weights_by_user(self):
        logging.info("[WL] Getting latest weights by user")

        weights_by_user = {}
        for user_id, user_weights in iteritems(self.get_weights_by_user()):
            user_weights.sort(key=lambda w: w['date_logged'], reverse=True)
            weights_by_user[user_id] = user_weights[0]

        logging.info("[WL] Found {} users with logged weight".format(len(weights_by_user)))
        return weights_by_user

    def get_unsynced_weight_data(self):
        logging.info("[WL] Getting unsynced weight data")
        unsynced_data = [weight for weight in self.weights if not weight['synced']]
        logging.info("[WL] Found {} unsynced entries".format(len(unsynced_data)))
        return unsynced_data

    def update_weight_sync_status(self, synced_weights):
        def generate_weight_identifying_key(single_weight_data):
            return '{}__{}__{}'.format(
                single_weight_data['user_id'],
                single_weight_data['date_logged'].strftime(DATETIME_FORMAT),
                single_weight_data['weight']
            )

        logging.info("[WL] Attempting sync status update of {} weights".format(len(synced_weights)))
        keys_updated = [generate_weight_identifying_key(synced_weight) for synced_weight in synced_weights]
        weights_updated = 0
        for weight in self.weights:
            if generate_weight_identifying_key(weight) in keys_updated:
                weight['synced'] = True
                weights_updated += 1
        if weights_updated > 0:
            self.store_all_weights()
        logging.info("[WL] Updated sync status for {} out of {} weights".format(weights_updated, len(synced_weights)))

    def store_all_weights(self):
        logging.info("[WL] Storing {} weights currently in memory".format(len(self.weights)))
        with open(WEIGHT_LOG_LOCATION, 'w') as weight_log:
            csv_writer = csv.writer(weight_log, **get_csv_file_options())
            csv_writer.writerow(self.log_header_columns)
            for weight in self.weights:
                csv_writer.writerow(self._format_weight_data_as_file_row(weight))
        weight_log.close()
