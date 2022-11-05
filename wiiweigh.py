#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import select
import time

import dbus.mainloop.glib
import numpy
import xwiimote
from six import iteritems

import utils.bluezutils as bluezutils

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject

from utils.bluezutils import ADAPTER_INTERFACE, DEVICE_INTERFACE

from utils.ring_buffer import RingBuffer

from weight_logger.weight_logger import log_weight

MAX_DEVICE_TYPE_CHECK_RETRIES = 5
relevant_ifaces = [ADAPTER_INTERFACE, DEVICE_INTERFACE]


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
    print("Waiting for the Wii Balance Board to connect..")
    mon = xwiimote.monitor(True, False)
    balance_board_dev = None

    while not balance_board_dev:
        mon.get_fd(True)  # blocks
        connected_device = mon.poll()

        if not connected_device or not dev_is_balance_board(connected_device):
            continue
        print("Balance board connected: {}".format(connected_device))
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
    last_measurements = RingBuffer(600)
    counter = 0

    while True:
        weight = sum(ms.next())

        last_measurements.append(weight)

        mean = numpy.mean(last_measurements.data)
        stddev = numpy.std(last_measurements.data)
        # print ("%f, %f" % (mean, stddev))
        if stddev < max_stddev and last_measurements.filled and mean > 100:
            return numpy.array((mean, stddev))
        if counter > 5000:
            return numpy.array((0, 0))
        counter = counter + 1


def find_device_address():
    adapter = bluezutils.find_adapter()
    adapter_path = adapter.object_path

    objects = bluezutils.get_managed_objects()

    # find FIRST registered or connected Wii Balance Board ("RVL-WBC-01") and return address
    for path, interfaces in iteritems(objects):
        if DEVICE_INTERFACE not in interfaces:
            continue
        properties = interfaces[DEVICE_INTERFACE]
        if properties["Adapter"] != adapter_path:
            continue
        if properties["Alias"] != "Nintendo RVL-WBC-01":
            continue
        print("Found the Wii Balance Board with address %s" % (properties["Address"]))
        return properties["Address"]


def connect_balance_board():
    global BALANCE_BOARD_MAC
    # device is something like "/sys/devices/platform/soc/3f201000.uart/tty/ttyAMA0/hci0/hci0:11/0005:057E:0306.000C"
    device = wait_for_balance_board()

    iface = xwiimote.iface(device)
    iface.open(xwiimote.IFACE_BALANCE_BOARD)

    (kg, err) = average_measurements(measurements(iface))
    kg /= 100.0
    err /= 100.0

    # Log the weight and inform that the weight has been logged.
    log_weight(kg)
    print("Weight logged: {:.2f}kg. +/- {:.2f}kg.".format(kg, err))

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
        print("{%s.PropertyChanged} [%s] %s = %s" % (iface, path, name, val))
        # check if property "Connected" changed to "1". Does NOT check which device has connected, we only assume it
        # was the balance board
        if name == "Connected" and val == "1":
            connect_balance_board()


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    # bluetooth (dis)connection triggers PropertiesChanged signal
    bus.add_signal_receiver(property_changed, bus_name="org.bluez",
                            dbus_interface="org.freedesktop.DBus.Properties",
                            signal_name="PropertiesChanged",
                            path_keyword="path")
    try:
        mainloop = GObject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        print("\nExiting")
