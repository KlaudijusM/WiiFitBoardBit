# -*- coding: utf-8 -*-
import logging
import time
from collections import defaultdict

from six import iteritems

from config import FITBIT_SYNC_ENABLED, WEIGHT_SYNC_LOOP_TIME_SECS
from fitbit_oauth_user_client import FitBitOAuth2UserClient
from weight_logger.weight_logger import WeightLogger


def main():
    """ Attempts to get non-synchronized data from weight data file and synchronize it with FitBit """
    logging.info('Starting FitBit weight synchronisation thread (WST)')
    if not FITBIT_SYNC_ENABLED:
        return

    while True:
        # Get unsynced weight data
        wl = WeightLogger()
        unsynced_weight_data = wl.get_unsynced_weight_data()
        if not unsynced_weight_data:
            time.sleep(WEIGHT_SYNC_LOOP_TIME_SECS)
            continue

        # Group weight data by user
        weight_data_by_user = defaultdict(lambda: list())
        for weight_data in unsynced_weight_data:
            uid = weight_data.get('user_id')
            weight_data_by_user[uid].append(weight_data)

        weights_logged = list()
        for user_id, weight_data in iteritems(weight_data_by_user):
            # Attempt weight logging for each user
            client = FitBitOAuth2UserClient(user_id)  # Get user client
            if not client.is_authorised():  # Check if user is authenticated
                continue

            for single_weight_data in weight_data:
                # Attempt to log each weight
                logged = client.log_user_weight(
                    weight=single_weight_data['weight'],
                    date=single_weight_data['date_logged']
                )
                if not logged:
                    logging.error(
                        "[WST] Failed to log user {} weight on FitBit. Please check user authentication!".format(
                            user_id
                        )
                    )
                    continue

                weights_logged.append(single_weight_data)

        if weights_logged:
            wl.update_weight_sync_status(weights_logged)
        time.sleep(WEIGHT_SYNC_LOOP_TIME_SECS)


if __name__ == "__main__":
    main()
