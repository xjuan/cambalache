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
        self.__commands = []
        self.__writing_command = False

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

        self.__writing_command = False
        self.__consume_next_command()

    def __consume_next_command(self):
        if self.__writing_command or not self.__commands:
            return

        self.__writing_command = True
        self.__conn.props.output_stream.write_all_async(
            self.__commands.pop(0),
            0,
            self.__cancellable,
            self.__on_data_output
        )

    def write_command(self, command, args=None):
        cmd = {"command": command}

        if args is not None:
            cmd["args"] = args

        cmd = json.dumps(cmd) + "\n"

        self.__commands.append(cmd.encode())
        self.__consume_next_command()

    def handle_command(self, line):
        pass

    def __on_data_input(self, source, res):
        try:
            line, len = source.read_line_finish_utf8(res)
        except Exception as e:
            if e.code != Gio.IOErrorEnum.CANCELLED:
                logger.warning(f"Error reading command {e}")
            self.close_connection()
            return

        if line is not None and line != "":
            self.handle_command(line)

        # Queue next command read
        source.read_line_async(0, self.__cancellable, self.__on_data_input)

    def init_connection(self, fd):
        self.__cancellable = Gio.Cancellable()

        self.__gsocket = Gio.Socket.new_from_fd(fd)
        self.__conn = Gio.SocketConnection(socket=self.__gsocket)
        self.__data_input = Gio.DataInputStream.new(self.__conn.props.input_stream)

        # Queue first command read
        self.__data_input.read_line_async(0, self.__cancellable, self.__on_data_input)

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
        self.__writing_command = False
