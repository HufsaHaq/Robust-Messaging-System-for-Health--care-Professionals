"""
1. Start the server in one terminal:
       python3 myserver.py localhost 8090

2. Start one or more clients in separate terminals:
       python3 myclient.py localhost 8090

   Each client will be prompted to enter a screen name.
   If the name is already taken the client keeps asking until
   a unique name is accepted by the server.

-----------------------------------------------
Open three terminals (one server, two clients).

Terminal 1 - server:
    python3 myserver.py localhost 8090

Terminal 2 - client A (A):
    python3 myclient.py localhost 8090
    > Enter your screen name: A
    Server prints "A registered" and "2 active clients".

Terminal 3 - client "B" (B):
    python3 myclient.py localhost 8090
    > Enter your screen name: B

Test duplicate name rejection:
    Start a third client and enter "A" when prompted.
    The client prints "Username already taken, try another." and asks again.

Test broadcast  ->  SEND:
    In A's terminal:
        SEND hello everyone
    Both A and B see:  message from A: hello everyone

Test private message  ->  SEND_TO:
    In A's terminal:
        SEND_TO B hi there
    Only B sees:  message from A: hi there

Test user list  ->  LIST:
    In A's terminal:
        LIST
    A sees:  online users: A, B

Test unknown command:
    In A's terminal type any unrecognised word, e.g. BADCMD.
    A sees:  unknown command

Test clean disconnect  ->  QUIT:
    In A's terminal:
        QUIT
    A sees "Client exiting" and exits cleanly.
    Server prints "a client disconnected" and "1 active clients".

-----------------
  REGISTER <name>             register a screen name with the server
  SEND <message>           broadcast a message to all connected users
  SEND_TO <name> <msg>     send a private message to one user
  LIST                     get the list of currently online users
  QUIT                     disconnect cleanly from the server
"""

import sys
import threading
from ex2utils import Client


class IRCClient(Client):

    # set up registration state before connecting
    def __init__(self):
        super().__init__()
        self.registered = False
        self._pending_name = None
        self._register_event = threading.Event()
        self._quit_event = threading.Event()

    # handle every message that arrives from the server
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
        """Send REGISTER and block until the server responds."""
        self._pending_name = username
        self.registered = False
        self._register_event.clear()
        self.send(f"REGISTER {username}".encode())
        self._register_event.wait(timeout=5)
        return self.registered

    # main entry point: connect, register, then loop on user input
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