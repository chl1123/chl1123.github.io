from .pymodule import PyModule


def publish(channel_name: str, message_type):
    PyModule.publish(channel_name, message_type.DESCRIPTOR.full_name)


def subscribe(channel_name: str, message_type, function: callable = None):
    if function is None:
        PyModule.subscribe(channel_name, message_type.DESCRIPTOR.full_name)
    else:
        PyModule.subscribe(channel_name, message_type.DESCRIPTOR.full_name, function)


def unsubscribe(channel_name: str, message_type):
    PyModule.unsubscribe(channel_name, message_type.DESCRIPTOR.full_name)


def put(channel_name: str, msg):
    PyModule.put(channel_name, msg)


def get(channel_name: str, message_type):
    return PyModule.get(channel_name, message_type.DESCRIPTOR.full_name)
