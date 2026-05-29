import json
from gi.repository import Gio

from . import getLogger

logger = getLogger(__name__)


class MrgCommand():
    def init_command(self, command_socket=None):

        self.__cancellable = None
        self.__gsocket = None
        self.__conn = None
        self.__data_input = None

        # List of outgoing commands
        self.__commands = []

        # Current outgoing command buffer
        self.__outgoing_data = None

        # Incoming command message length
        self.__incoming_total = 0

        # Incoming buffer
        self.__incoming_data = None

        if command_socket:
            self.init_connection(command_socket)

    def __on_data_output(self, source, res):
        try:
            status, bytes_written = source.write_all_finish(res)
        except Exception as e:
            if e.code != Gio.IOErrorEnum.CANCELLED:
                logger.warning(f"Error writing command {e}")
            self.close_connection()
            return

        self.__outgoing_data = None
        self.__consume_next_command()

    def __consume_next_command(self):
        if self.__conn is None or self.__outgoing_data or not self.__commands:
            return

        command = self.__commands.pop(0)
        command_len = len(command)

        # Create command buffer by appending size to the beginning
        self.__outgoing_data = command_len.to_bytes(4) + command

        self.__conn.props.output_stream.write_all_async(
            self.__outgoing_data,
            0,
            self.__cancellable,
            self.__on_data_output
        )

    def write_command(self, command, args=None):
        cmd = {"command": command}

        if args is not None:
            cmd["args"] = args

        cmd = json.dumps(cmd)

        self.__commands.append(cmd.encode())
        self.__consume_next_command()

    def handle_command(self, line):
        pass

    def __on_data_input(self, source, res):
        try:
            data = source.read_bytes_finish(res)
        except Exception as e:
            if e.code != Gio.IOErrorEnum.CANCELLED:
                logger.warning(f"Error reading command {e}")
            self.close_connection()
            return

        if self.__incoming_data:
            self.__incoming_data = self.__incoming_data + data.get_data()
        else:
            self.__incoming_data = data.get_data()

        # Check if we are done reading data for command
        if data.get_size() != self.__incoming_total:
            self.__incoming_total -= data.get_size()

            # Read the rest
            source.read_bytes_async(self.__incoming_total, 0, self.__cancellable, self.__on_data_input)
            return

        if self.__incoming_data is not None:
            self.handle_command(self.__incoming_data.decode("UTF-8"))
            self.__incoming_total = 0
            self.__incoming_data = None

        # Queue next command read
        source.read_bytes_async(4, 0, self.__cancellable, self.__on_data_len_input)

    def __on_data_len_input(self, source, res):
        try:
            data = source.read_bytes_finish(res)
        except Exception as e:
            if e.code != Gio.IOErrorEnum.CANCELLED:
                logger.warning(f"Error reading command {e}")
            self.close_connection()
            return

        # Just in case
        if data.get_size() < 4:
            missing_data = source.read_bytes(4 - data.get_size(), None)
            self.__incoming_total = int.from_bytes(data.get_data() + missing_data.get_data())
        else:
            self.__incoming_total = int.from_bytes(data.get_data())

        # Read command data
        source.read_bytes_async(self.__incoming_total, 0, self.__cancellable, self.__on_data_input)

    def init_connection(self, fd):
        self.__cancellable = Gio.Cancellable()

        self.__gsocket = Gio.Socket.new_from_fd(fd)
        self.__conn = Gio.SocketConnection(socket=self.__gsocket)
        self.__data_input = Gio.DataInputStream.new(self.__conn.props.input_stream)

        # Queue first command read
        self.__data_input.read_bytes_async(4, 0, self.__cancellable, self.__on_data_len_input)

    def close_connection(self):
        # Cancel all pending IO
        if self.__cancellable:
            self.__cancellable.cancel()
            self.__cancellable = None

        if self.__conn:
            self.__conn.close()
            self.__conn = None
            self.__data_input = None
            self.__gsocket = None

        self.__commands = []
        self.__outgoing_data = None
        self.__incoming_total = 0
        self.__incoming_data = None
