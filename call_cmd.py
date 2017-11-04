from subprocess import Popen, CalledProcessError, PIPE, STDOUT
from threading import Thread
from queue import Queue, Empty
from time import sleep


class Executor:
    def __init__(self):
        self.commands = Queue()
        self.executor = Thread(target=self.subscribe_commands)
        self.executor.daemon = True
        self.done = False

    def start(self):
        self.executor.start()

    def stop(self):
        self.done = True
        self.async_execute_string("terminate", lambda: print("done"))

    def async_execute_string(self, command, output_handler):
        stripped_command = command.strip()
        if stripped_command:
            self.commands.put((stripped_command, output_handler))

    def subscribe_commands(self):
        while not self.done:
            try:
                (command, output_handler) = self.commands.get(block=True, timeout=10)
                if command != "terminate":
                    self.execute_command(command, output_handler)
                else:
                    output_handler()
            except Empty:
                pass

    def execute_command(self, command, output_handler):
        try:
            proc = Popen(["-c", command],
                         executable="bash",
                         stdout=PIPE,
                         stderr=STDOUT,
                         shell=True)

            while proc.poll() is None:
                for output in proc.stdout.readlines():
                    output_handler(output.decode())
        except CalledProcessError as e:
            output_handler(e)
        except OSError as e:
            if e.errno == 2:
                output_handler(e.strerror)
            else:
                output_handler(e)
        finally:
            self.commands.task_done()

# c = Executor()
# c.start()
# c.async_execute_string("ls", lambda output: print("1>>>" + output))
# c.async_execute_string("ls -ltr", lambda output: print("2>>>" + output))
# c.async_execute_string("ls -ltrh", lambda output: print("3>>>" + output))
#
# sleep(10)
# c.stop()
# sleep(2)
