from six import iteritems
import dbus

SERVICE_NAME = "org.bluez"
ADAPTER_INTERFACE = SERVICE_NAME + ".Adapter1"
DEVICE_INTERFACE = SERVICE_NAME + ".Device1"


def get_managed_objects():
	bus = dbus.SystemBus()
	manager = dbus.Interface(bus.get_object(SERVICE_NAME, "/"), "org.freedesktop.DBus.ObjectManager")
	return manager.GetManagedObjects()


def find_adapter(pattern=None):
	return find_adapter_in_objects(get_managed_objects(), pattern)


def find_adapter_in_objects(objects, pattern=None):
	bus = dbus.SystemBus()
	for path, ifaces in iteritems(objects):
		adapter = ifaces.get(ADAPTER_INTERFACE)
		if adapter is None:
			continue
		if not pattern or pattern == adapter["Address"] or \
							path.endswith(pattern):
			obj = bus.get_object(SERVICE_NAME, path)
			return dbus.Interface(obj, ADAPTER_INTERFACE)
	raise Exception("Bluetooth adapter not found")


def find_device(device_address, adapter_pattern=None):
	return find_device_in_objects(get_managed_objects(), device_address, adapter_pattern)

def find_device_in_objects(objects, device_address, adapter_pattern=None):
	bus = dbus.SystemBus()
	path_prefix = ""
	if adapter_pattern:
		adapter = find_adapter_in_objects(objects, adapter_pattern)
		path_prefix = adapter.object_path
	for path, ifaces in iteritems(objects):
		if not path.startswith(path_prefix):
			continue
		device = ifaces.get(DEVICE_INTERFACE)
		if not device or device.get("Address") != device_address:
			continue
		obj = bus.get_object(SERVICE_NAME, path)
		return dbus.Interface(obj, DEVICE_INTERFACE)

	raise Exception("Bluetooth device not found")
