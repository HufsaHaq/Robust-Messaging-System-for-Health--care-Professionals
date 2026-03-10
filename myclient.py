"""
IRC chat client implementing Task 2.6.

start the server: python3 myserver.py localhost 8090

start one or more clients : python3 myclient.py localhost 8090

- The client automatically sends HELLO <name> on startup.

  SEND hello everyone              -> broadcasts to all users
  SEND_TO <username> hi there      -> private message to one user
  LIST                             -> shows all online users
  QUIT                             -> disconnects cleanly
"""

import sys
import threading
from ex2utils import Client


class IRCClient(Client):

    # Task 2.6 - set up registration state before connecting
    def __init__(self):
        super().__init__()
        self.registered = False
        self._pending_name = None
        self._register_event = threading.Event()
        self._quit_event = threading.Event()

    # Task 2.6 - handle every message that arrives from the server
    def onMessage(self, socket, message):
        # server confirmed registration
        if self._pending_name and message == f"welcome {self._pending_name}":
            self.registered = True
            self._register_event.set()
            print(f"Registered as {self._pending_name}")
            return True

        # server rejected the screen name tried
        if message == "username taken":
            self._register_event.set()
            return True

        # server acknowledged  QUIT 
        if message == "Client exiting":
            print(message)
            self._quit_event.set()
            return False

        print(message)
        return True

    def _try_register(self, username):
        """Send HELLO and block until the server responds."""
        self._pending_name = username
        self.registered = False
        self._register_event.clear()
        self.send(f"HELLO {username}".encode())
        self._register_event.wait(timeout=5)
        return self.registered

    # Task 2.6 - main entry point: connect, register, then loop on user input
    def run(self, ip, port):
        self.start(ip, port)

        # keep asking until it accepted screen name
        username = input("Enter your screen name: ").strip()
        while not self._try_register(username):
            print("Username already taken, try another.")
            username = input("Enter your screen name: ").strip()

        print("Commands: SEND <msg>  |  SEND_TO <user> <msg>  |  LIST  |  QUIT")

        # relay typed input straight to the server
        while self.isRunning():
            try:
                user_input = input()
            except (EOFError, KeyboardInterrupt):
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            self.send(user_input.encode())

            if user_input.upper() == "QUIT":
                # wait for the server to confirm before we leave
                self._quit_event.wait(timeout=3)
                break

        if self.isRunning():
            self.stop()


ip = sys.argv[1]
port = int(sys.argv[2])

client = IRCClient()
client.run(ip, port)