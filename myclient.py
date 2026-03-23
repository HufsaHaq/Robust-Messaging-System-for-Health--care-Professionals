"""
1. Start the server in one terminal:
       python3 myserver.py localhost 8090

2. Start one or more clients in separate terminals:
       python3 myclient.py localhost 8090

   Each client is prompted for a screen name.  Blank names are rejected
   immediately.  Names already in use are rejected by the server and the
   client asks again.  Usernames are case-insensitive; commands are also
   case-insensitive.  Usernames may not contain spaces (space is the
   protocol separator).


  - Commands are case-insensitive: SEND, send, Send all work.
  - Usernames are case-insensitive: Alice and alice are the same user.
  - Usernames cannot contain spaces.
  - Broadcasts (SEND) only go to registered users.
  - Each connection may only register one username.

Open three terminals.

Terminal 1 - server:
    python3 myserver.py localhost 8090

Terminal 2 - client Alice:
    python3 myclient.py localhost 8090
    > Enter your screen name: Alice
    Server prints "alice registered" and "1 active clients".

Terminal 3 - client Bob:
    python3 myclient.py localhost 8090
    > Enter your screen name: Bob
    Server prints "bob registered" and "2 active clients".

Test blank username:
    When prompted for a screen name just press Enter.
    Client prints "Screen name cannot be blank." and asks again immediately.

Test duplicate name:
    Start a third client and enter "Alice" when prompted.
    Client prints "Username already taken, try another." and asks again.
    Note: entering "ALICE" or "alice" also counts as a duplicate.

Test broadcast  ->  SEND:
    In Alice's terminal:
        SEND hello everyone
    Both Alice and Bob see:  message from alice: hello everyone

Test private message  ->  SEND_TO:
    In Alice's terminal:
        SEND_TO Bob hi there
    Only Bob sees:  message from alice: hi there
    Note: SEND_TO BOB hi there also works (target name is case-insensitive).

Test user list  ->  LIST:
    In Alice's terminal:
        LIST
    Alice sees:  online users: alice, bob

Test unknown command:
    In Alice's terminal type any unrecognised word, e.g. BADCMD.
    Alice sees:  unknown command

Test clean disconnect  ->  QUIT:
    In Alice's terminal:
        QUIT
    Alice sees "Client exiting" and exits cleanly.
    Server prints "a client disconnected" and "1 active clients".
    Bob's next LIST shows only bob.

TESTING WITH TELNET

Telnet sends \r\n line endings; the server strips \r automatically so all
commands work identically to the Python client.

    telnet localhost 8090

    REGISTER Alice          -> welcome alice
    LIST                    -> online users: alice
    SEND hello everyone     -> message from alice: hello everyone
    SEND_TO alice hi        -> message from alice: hi
    QUIT                    -> Client exiting  (connection closes)

Test unregistered behaviour via telnet:
    telnet localhost 8090
    SEND hello              -> not registered
    LIST                    -> online users: (whoever is currently registered)
    QUIT                    -> Client exiting  (works without registering)

Test invalid commands via telnet:
    REGISTER                -> unknown command  (no name given)
    REGISTER Alice Bob      -> unknown command  (spaces in name not allowed)
    SEND                    -> unknown command  (no message given)
    BADCMD                  -> not registered  (or unknown command if registered)

----------------
  REGISTER <n>         register a screen name (no spaces; one per connection)
  SEND <message>       broadcast to all registered users
  SEND_TO <n> <msg>    send a private message to one user
  LIST                 get the list of currently online users
  QUIT                 disconnect cleanly (works before and after registering)
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
        # server lowercases all usernames, so we store lowercase here to match
        # the "welcome {username}" reply we'll get back
        self._pending_name = username.lower()
        self.registered = False
        self._register_event.clear()
        self.send(f"REGISTER {username}".encode())
        self._register_event.wait(timeout=5)
        return self.registered

    # main entry point: connect, register, then loop on user input
    def run(self, ip, port):
        self.start(ip, port)

        # keep asking until they give a name that the server accepts
        username = input("Enter your screen name: ").strip()
        while not username:
            print("Screen name cannot be blank.")
            username = input("Enter your screen name: ").strip()
        while not self._try_register(username):
            print("Username already taken, try another.")
            username = input("Enter your screen name: ").strip()
            while not username:
                print("Screen name cannot be blank.")
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