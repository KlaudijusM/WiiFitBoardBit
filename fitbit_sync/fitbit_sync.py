# -*- coding: utf-8 -*-

from config import FITBIT_SYNC_ENABLED
from weight_logger.weight_logger import get_unsynced_weight_data


def sync_unsynced_weight():
    """ Attempts to get non-synchronized data from weight data file and synchronize it with FitBit """
    if not FITBIT_SYNC_ENABLED:
        return
    unsynced_weight_data = get_unsynced_weight_data()
    if not unsynced_weight_data:
        return
