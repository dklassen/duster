import pytest

from duster import sensor
from unittest import mock


class SerialMock:
    def __init__(self, *, mocked_bytes):
        self._data = mocked_bytes

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    def read(self, bytes_to_read):
        data = self.data
        self.data = data[bytes_to_read:]
        buffer = data[0:bytes_to_read]
        return buffer


class MessageInteface(sensor.Message):
    data_length = 2
    message_length = 3


class TestMessageBaseClass:
    def test_init_raises_when_data_not_to_length(self):
        with pytest.raises(
            AssertionError, match="Data has unexpected length. Got 4 expected 2"
        ):
            MessageInteface(commandID=b"\xff", deviceID=b"\xff", data=bytearray(4))

    def test_init_raises_when_device_id_is_not_to_length(self):
        with pytest.raises(
            AssertionError, match="deviceID has unexpected length. Got 1 expected 2"
        ):
            MessageInteface(commandID=b"\xff", deviceID=b"\xff", data=bytearray(2))


class TestResponseMessage:
    def test_to_bytes(self):
        expected = bytearray.fromhex("AA C0 D4 04 3A 0A A1 60 1D AB")

        raw_data = expected[2:6]
        commandID = expected[1:2]
        deviceID = expected[6:8]

        subject = sensor.ResponseMessage(
            commandID=commandID, deviceID=deviceID, data=raw_data
        )

        assert subject.to_bytes() == expected


class TestMeasurementHandler:
    def test_decode(self):
        commandID = b"\xC0"
        deviceID = b"\xa1\xa2"

        expected = {
            "command_id": commandID,
            "deviceID": deviceID,
            "pm_2.5": 123.6,
            "pm_10": 261.8,
        }

        raw_measurement = sensor.ResponseMessage(
            commandID=commandID,
            deviceID=deviceID,
            data=bytearray.fromhex("D4 04 3A 0A"),
        )

        assert sensor.MeasurementHandler.decode(raw_measurement) == expected


class TestResponseHandler:
    def test_read(self):
        expected = b"\xaa\xc0\xcc\xcd\x00\x00\xa1\xa2\xdc\xab"

        serial_mock = SerialMock(mocked_bytes=expected)

        subject = sensor.ResponseHandler(message=sensor.ResponseMessage)
        output = subject.read(serial_device=serial_mock)
        assert output.to_bytes() == expected


class TestCommandHandler:
    def test_write_calls_serial_with_expected_bytes(self):
        mock_serial = mock.Mock()
        input_command = sensor.CommandMessage(
            commandID=b"\xc0\x08", deviceID=b"\xff\xff", data=bytearray(13)
        )

        subject = sensor.CommandHandler().write(
            serial_device=mock_serial, command=input_command
        )

        mock_serial.write.assert_called_once_with(input_command.to_bytes())


class TestSDS011:
    def test_read_calls_response_handler(self):
        mock_serial = mock.Mock()
        mock_response_handler = mock.Mock()

        subject = sensor.SDS011(
            serial_device=mock_serial,
            deviceID=b"/xff",
            responseHandler=mock_response_handler,
            commandHandler=sensor.CommandHandler,
        )

        subject.read()

        mock_response_handler.read.assert_called_once

    def test_request_calls_command_handler(self):
        mock_serial = mock.Mock()
        mock_response_handler = mock.Mock()
        mock_command_handler = mock.Mock()
        mock_command = mock.Mock()

        subject = sensor.SDS011(
            serial_device=mock_serial,
            deviceID=b"/xff",
            responseHandler=mock_response_handler,
            commandHandler=mock_command_handler,
        )

        subject.request(mock_command)

        mock_command_handler.write.assert_called_once_with(
            serial_device=mock_serial, command=mock_command
        )


class TestSleepWakeCommandBuilder:
    def test_build_sleep_command(self):
        subject = (
            sensor.SetSleepWakeCommandBuilder(
                messageClass=sensor.CommandMessage,
                deviceID=b"\xa2\xd5",
            )
            .sleep()
            .build()
        )

        expected = bytearray(
            b"\xaa\xb4\x06\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa2\xd5~\xab"
        )

        assert subject.to_bytes() == expected

    def test_build_wake_command(self):
        subject = (
            sensor.SetSleepWakeCommandBuilder(
                messageClass=sensor.CommandMessage,
                deviceID=b"\xa2\xd5",
            )
            .wake()
            .build()
        )

        expected = bytearray(
            b"\xaa\xb4\x06\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa2\xd5\x7f\xab"
        )

        assert subject.to_bytes() == expected

    def test_query_status_as_default(self):
        subject = sensor.SetSleepWakeCommandBuilder(
            messageClass=sensor.CommandMessage,
            deviceID=b"\xa2\xd5",
        ).build()

        expected = bytearray(
            b"\xaa\xb4\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa2\xd5}\xab"
        )

        assert subject.to_bytes() == expected


class TestWorkingPeriodCommandBuilder:
    def test_build_returns_expected_query_command(self):
        subject = sensor.WorkingPeriodCommandBuilder(
            messageClass=sensor.CommandMessage,
            deviceID=b"\xa2\xd5",
        ).build()

        expected = bytearray(
            b"\xaa\xb4\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa2\xd5\x7f\xab"
        )

        assert subject.to_bytes() == expected

    def test_build_setWorkingPeriod_returns_expected_command(self):
        command = sensor.WorkingPeriodCommandBuilder(
            messageClass=sensor.CommandMessage,
            deviceID=b"\xa2\xd5",
        )

        subject = command.setWorkingPeriod(25).build()
        expected = b"\xaa\xb4\x08\x01\x19\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa2\xd5\x99\xab"

        assert subject.to_bytes() == expected