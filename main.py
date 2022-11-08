# -*- coding: utf-8 -*-
import logging
import time
from threading import Thread

from config import FITBIT_SYNC_ENABLED, LOG_LOCATION, DATETIME_FORMAT
from fitbit_sync import webserver, weight_sync
from wii_fit_bt_weight_tracker import tracker


def main():
    # Setup logging
    logging.basicConfig(filename=LOG_LOCATION, filemode='a', format='%(asctime)s %(message)s', datefmt=DATETIME_FORMAT,
                        level=logging.INFO)

    try:
        # Start Bluetooth tracking thread
        bt_thread = Thread(name="[WiiFitBoardBit] BT Tracking", target=tracker.main)
        bt_thread.setDaemon(True)
        bt_thread.start()

        if FITBIT_SYNC_ENABLED:
            # Start FitBit authentication Flask webserver thread
            flask_thread = Thread(name="[WiiFitBoardBit] FitBit Authentication Web Server", target=webserver.main)
            flask_thread.setDaemon(True)
            flask_thread.start()

            # Start FitBit weight synchronisation thread
            sync_thread = Thread(name="[WiiFitBoardBit] FitBit OAuth2 Weight Synchronisation", target=weight_sync.main)
            sync_thread.setDaemon(True)
            sync_thread.start()
        else:
            logging.info("FitBit synchronisation is disabled. Authentication web server and weight synchronisation "
                         "threads were not started")
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("Stopping due to Keyboard Interrupt event")
        logging.shutdown()
        print("Exiting")
        exit(0)


if __name__ == "__main__":
    main()
