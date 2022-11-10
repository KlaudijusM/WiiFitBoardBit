# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import logging
import select
import time
from datetime import datetime
from threading import Thread

import dbus.mainloop.glib
import numpy
import xwiimote
from six import iteritems

from wii_fit_bt_weight_tracker.utils import bluezutils
from wii_fit_bt_weight_tracker.utils.ring_buffer import RingBuffer

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject

from weight_logger.weight_logger import WeightLogger

from config import BALANCE_BOARD_MAC, UNITS

MAX_DEVICE_TYPE_CHECK_RETRIES = 5
relevant_ifaces = [bluezutils.ADAPTER_INTERFACE, bluezutils.DEVICE_INTERFACE]


def convert_measurements_to_units(kg, err):
    units = 'kg' if UNITS == 'METRIC' else 'lbs'
    weight = kg
    if UNITS != 'METRIC':
        weight = kg * 2.2
        err = err * 2.2
    return weight, err, units


def log_weight(weight):
    wl = WeightLogger()
    wl.log_weight(weight)


def get_device_type(dev, num_try=1):
    """ Tries to get the device type with delay """
    if num_try >= MAX_DEVICE_TYPE_CHECK_RETRIES:
        return
    time.sleep(1)  # If the device type is checked to early it is reported as 'unknown'
    iface = xwiimote.iface(dev)
    device_type = iface.get_devtype()
    if not device_type or device_type == 'unknown':
        return get_device_type(dev, num_try + 1)
    return device_type


def dev_is_balance_board(dev):
    """ Checks if the device type is a balance board """
    return get_device_type(dev) == 'balanceboard'


def wait_for_balance_board():
    logging.info("[BBTT] Waiting for the Wii Balance Board to connect...")
    mon = xwiimote.monitor(True, False)
    balance_board_dev = None

    while not balance_board_dev:
        mon.get_fd(True)  # blocks
        connected_device = mon.poll()

        if not connected_device or not dev_is_balance_board(connected_device):
            continue
        logging.info("[BBTT] Balance board connected: {}".format(connected_device))
        balance_board_dev = connected_device
    return balance_board_dev


def measurements(iface):
    p = select.epoll.fromfd(iface.get_fd())

    while True:
        p.poll()  # blocks

        event = xwiimote.event()
        iface.dispatch(event)

        tl = event.get_abs(2)[0]
        tr = event.get_abs(0)[0]
        br = event.get_abs(3)[0]
        bl = event.get_abs(1)[0]

        yield (tl, tr, br, bl)


def average_measurements(ms, max_stddev=30):
    weight_measurements = RingBuffer(600)
    counter = 0

    time.sleep(2)  # Wait for user to get on to the scale
    max_time_to_measure = 5   # How long to measure until logging weight
    measurement_start = datetime.now()

    while True:
        weight = sum(ms.next())

        weight_measurements.append(weight)
        mean = numpy.mean(weight_measurements.data)
        stddev = numpy.std(weight_measurements.data)

        # logging.info("Mean {:.2f} STDDEV {:.2f} WEIGHT {:.2f}".format(mean, stddev, weight))

        if stddev < max_stddev and weight_measurements.filled and mean > 100:
            return numpy.array((mean, stddev))
        if counter > 5000:
            return numpy.array((0, 0))

        time_elapsed = (datetime.now() - measurement_start).seconds
        if time_elapsed > max_time_to_measure and mean > 100 and stddev < max_stddev * 1.5:
            return numpy.array((mean, stddev))

        counter += 1


def find_device_address():
    adapter = bluezutils.find_adapter()
    adapter_path = adapter.object_path

    objects = bluezutils.get_managed_objects()

    # find FIRST registered or connected Wii Balance Board ("RVL-WBC-01") and return address
    for path, interfaces in iteritems(objects):
        if bluezutils.DEVICE_INTERFACE not in interfaces:
            continue
        properties = interfaces[bluezutils.DEVICE_INTERFACE]
        if properties["Adapter"] != adapter_path:
            continue
        if properties["Alias"] != "Nintendo RVL-WBC-01":
            continue
        address = properties["Address"]
        logging.info("[BBTT] Found the Wii Balance Board with address: {}".format(address))
        return address


def connect_balance_board():
    global BALANCE_BOARD_MAC
    # device is something like "/sys/devices/platform/soc/3f201000.uart/tty/ttyAMA0/hci0/hci0:11/0005:057E:0306.000C"
    device = wait_for_balance_board()

    iface = xwiimote.iface(device)
    iface.open(xwiimote.IFACE_BALANCE_BOARD)

    (kg, err) = average_measurements(measurements(iface))
    kg /= 100.0
    err /= 100.0
    weight, err, units = convert_measurements_to_units(kg, err)

    # Log the weight and inform that the weight has been logged.
    logging.info("[BBTT] Weight registered: {:.2f}{}. +/- {:.2f}{}.".format(weight, units, err, units))
    logging.info("[BBTT] Attempting to log weight")
    weight_logging_thread = Thread(target=log_weight, args=(kg,))
    weight_logging_thread.start()

    # find address of the balance board (once) and disconnect (if found).
    if not BALANCE_BOARD_MAC:
        BALANCE_BOARD_MAC = find_device_address()
    if BALANCE_BOARD_MAC:
        device = bluezutils.find_device(BALANCE_BOARD_MAC)
        if device:
            device.Disconnect()


def property_changed(interface, changed, invalidated, path):
    iface = interface[interface.rfind(".") + 1:]
    for name, value in iteritems(changed):
        val = str(value)
        logging.info("[BBTT] {{{}.PropertyChanged}} [{}] {} = {}".format(iface, path, name, val))
        # check if property "Connected" changed to "1". Does NOT check which device has connected, we only assume it
        # was the balance board
        if name == "Connected" and val == "1":
            connect_balance_board()


def main():
    logging.info("Starting Bluetooth WiiFit board tracking thread (BBTT)")

    logging.info("[BBTT] Preparing DBus")
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    logging.info("[BBTT] Adding BlueZ signal receiver")
    # bluetooth (dis)connection triggers PropertiesChanged signal
    bus.add_signal_receiver(property_changed, bus_name="org.bluez",
                            dbus_interface="org.freedesktop.DBus.Properties",
                            signal_name="PropertiesChanged",
                            path_keyword="path")
    try:
        logging.info("[BBTT] Starting GObject MainLoop")
        mainloop = GObject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        logging.info("[BBTT] Stopping Bluetooth WiiFit board tracking due to Keyboard Interrupt event")
        exit(0)
    except Exception as exc:
        logging.error("[BBTT] ERROR! {}:{}".format(type(exc).__name__, exc))
        raise exc


if __name__ == "__main__":
    main()

