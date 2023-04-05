import serial
import struct
import abc


class Message(abc.ABC):
    head = b"\xaa"
    tail = b"\xab"

    def __init__(self, *, commandID, deviceID, data):
        assert (
            len(data) == self.data_length
        ), f"Data has unexpected length. Got {len(data)} expected {self.data_length}"

        assert (
            len(deviceID) == 2
        ), f"deviceID has unexpected length. Got {len(deviceID)} expected {2}"

        self._data = data
        self._commandID = commandID
        self._deviceID = deviceID

    @property
    @abc.abstractmethod
    def message_length(self):
        pass

    @property
    @abc.abstractmethod
    def data_length(self):
        pass

    @property
    def deviceID(self):
        return self._deviceID

    @property
    def commandID(self):
        return self._commandID

    @property
    def data(self):
        return self._data

    def _checksum(self):
        bytes_to_checksum = self.data + self.deviceID
        return sum(v for v in bytes_to_checksum) % 256

    def _msg(self):
        buffer = bytearray()
        buffer.extend(self._commandID)
        buffer.extend(self.data)
        buffer.extend(self._deviceID)
        return buffer

    def to_bytes(self):
        frame = bytearray()
        frame.extend(self.head)
        frame.extend(self._msg())
        frame.append(self._checksum())
        frame.extend(self.tail)
        return frame


class ResponseMessage(Message):
    message_length = 10
    data_length = 4

    def __init__(self, *, commandID, deviceID, data):
        super().__init__(commandID=commandID, deviceID=deviceID, data=data)


class CommandMessage(Message):
    message_length = 19
    data_length = 13

    def __init__(self, *, commandID, deviceID, data):
        super().__init__(commandID=commandID, deviceID=deviceID, data=data)


class SetSleepWakeCommandBuilder:
    commandID = b"\xb4"

    def __init__(self, *, messageClass, deviceID):
        self._deviceID = deviceID
        self._messageClass = messageClass
        self._data = bytearray(13)
        self._data[0:1] = b"\x06"

    def sleep(self):
        self._data[1] = 1
        self._data[2] = 0
        return self

    def wake(self):
        self._data[1] = 1
        self._data[2] = 1
        return self

    def build(self):
        return self._messageClass(
            commandID=self.__class__.commandID,
            deviceID=self._deviceID,
            data=self._data,
        )


class WorkingPeriodCommandBuilder:
    commandID = b"\xb4"

    def __init__(self, *, messageClass, deviceID):
        self._deviceID = deviceID
        self._messageClass = messageClass
        self._data = bytearray(13)
        self._data[0:1] = b"\x08"

    def setWorkingPeriod(self, period_in_minutes):
        self._data[1:2] = b"\x01"
        self._data[2:3] = period_in_minutes.to_bytes(1, "big")
        return self

    def build(self):
        return self._messageClass(
            commandID=self.__class__.commandID,
            deviceID=self._deviceID,
            data=self._data,
        )


class MeasurementDecoder:
    @classmethod
    def decode(cls, raw_measurement):
        (pm_2_5, pm_10) = (x / 10 for x in struct.unpack("<HH", raw_measurement.data))

        return {
            "command_id": raw_measurement.commandID,
            "deviceID": raw_measurement.deviceID,
            "pm_2.5": pm_2_5,
            "pm_10": pm_10,
        }


class ResponseHandler:
    def __init__(self, *, message):
        self._message = message

    def read(self, *, serial_device):
        bytes_recieved = bytearray()

        while True:
            buffer = serial_device.read(1)

            if buffer == self._message.head:
                bytes_recieved.extend(buffer)
                packet = serial_device.read(self._message.message_length)
                bytes_recieved.extend(packet)
                break

        return self._parse(bytes_recieved)

    def _parse(self, buffer):
        command_id = buffer[1:2]
        deviceID = buffer[-4:-2]
        data = buffer[2:6]

        return self._message(commandID=command_id, deviceID=deviceID, data=data)


class CommandHandler:
    def write(self, *, serial_device, command):
        raw_command = command.to_bytes()
        return serial_device.write(raw_command)


class SDS011:
    def __init__(self, *, serial_device, deviceID, responseHandler, commandHandler):
        self._deviceID = deviceID
        self._serial_device = serial_device
        self.commandHandler = commandHandler
        self.responseHandler = responseHandler

    @property
    def serial_device(self):
        return self._serial_device

    @property
    def deviceID(self):
        return self._deviceID

    def request(self, cmd):
        return self.commandHandler.write(serial_device=self.serial_device, command=cmd)

    def read(self):
        return self.responseHandler.read(serial_device=self.serial_device)


class SDS011Factory:
    @classmethod
    def create(cls, **config):
        raw_serial_device = serial.Serial(
            port=config["port"],
            baudrate=config["baudrate"],
        )

        return SDS011(
            serial_device=raw_serial_device,
            deviceID=config["deviceID"],
            responseHandler=config["responseHandler"],
            commandHandler=config["commandHandler"],
        )
