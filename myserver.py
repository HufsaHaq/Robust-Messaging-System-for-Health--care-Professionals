"""
python3 myserver.py localhost 8090
"""

import sys
from ex2utils import Server


class IRCServer(Server):

    # initialise server-wide state on startup
    def onStart(self):
        self.clients = {}       # maps lowercase_key -> socket
        self.client_count = 0
        self.printOutput("Server started")

    # fires when a new TCP connection arrives
    def onConnect(self, socket):
        socket.username = None      # lowercase key used for auth/lookup
        socket.display_name = None  # original casing used for display
        self.client_count += 1
        self.printOutput("new client connected")
        self.printOutput(f"{self.client_count} active clients")

    # fires when a connection drops for any reason
    def onDisconnect(self, socket):
        # remove every entry pointing to this socket - guards against stale entries
        stale = [name for name, sock in self.clients.items() if sock is socket]
        for name in stale:
            del self.clients[name]
        self.client_count -= 1
        self.printOutput("a client disconnected")
        self.printOutput(f"{self.client_count} active clients")

    # parse command and dispatch to the right handler
    def onMessage(self, socket, message):
        # telnet sends \r\n line endings - strip the \r so commands match correctly
        message = message.strip('\r')

        self.printOutput(message)

        # split into command word and everything after it
        parts = message.split(" ", 1)
        command = parts[0].upper()
        params = parts[1].strip() if len(parts) > 1 else ""

        # REGISTER: open to anyone - this is how you get a username
        if command == "REGISTER":
            return self._handle_register(socket, params)

        # QUIT: anyone can disconnect, registered or not
        if command == "QUIT":
            socket.send(b"Client exiting")
            return False

        # LIST: allow unregistered clients too (useful for telnet testing)
        if command == "LIST":
            return self._handle_list(socket)

        # every command below this point requires a registered user
        if not socket.username:
            socket.send(b"not registered")
            return True

        # SEND: broadcast to every registered user
        if command == "SEND":
            return self._handle_send(socket, params)

        # SEND_TO: private message to one user
        if command == "SEND_TO":
            return self._handle_send_to(socket, params)

        # anything else is unknown
        socket.send(b"unknown command")
        return True


    def _handle_register(self, socket, username):
        """Register the given username, rejecting duplicates."""
        if not username:
            socket.send(b"unknown command")
            return True
        # spaces in names break SEND_TO parsing since space is our separator
        if ' ' in username:
            socket.send(b"unknown command")
            return True
        # check for a duplicate name first (case-insensitive) - this must come
        # before the already-registered check so that re-attempting with a different
        # capitalisation of a taken name gives "username taken" not "already registered"
        username_key = username.lower()
        if username_key in self.clients:
            socket.send(b"username taken")
            return True
        # only now check if this socket already holds a different registered name
        if socket.username:
            socket.send(b"already registered")
            return True
        # username_key is the lowercase lookup key; username preserves original casing
        socket.username = username_key
        socket.display_name = username
        self.clients[username_key] = socket
        self.printOutput(f"{username} registered")
        self.printOutput(f"{self.client_count} active clients")
        socket.send(f"welcome {username}".encode())
        return True

    def _handle_send(self, socket, message):
        """Broadcast a message from this user to everyone."""
        # blank messages are allowed - no empty-message guard
        formatted = f"message from {socket.display_name}: {message}"
        # collect dead sockets during broadcast rather than crashing mid-loop
        dead = []
        for username, client in self.clients.items():
            try:
                client.send(formatted.encode())
            except Exception:
                dead.append(username)
        for username in dead:
            self.printOutput(f"removed dead socket for {username}")
            del self.clients[username]
        return True

    def _handle_send_to(self, socket, params):
        """Send a private message to a single named user."""
        parts = params.split(" ", 1)
        # need at least a target name; message body may be blank
        if len(parts) < 1 or not parts[0].strip():
            socket.send(b"unknown command")
            return True
        # normalise target to lowercase to match how names are stored
        target = parts[0].lower()
        msg_text = parts[1] if len(parts) > 1 else ""
        if target not in self.clients:
            socket.send(b"user not found")
            return True
        formatted = f"message from {socket.display_name}: {msg_text}"
        try:
            self.clients[target].send(formatted.encode())
        except Exception:
            # target socket died - clean it up and tell the sender
            self.printOutput(f"removed dead socket for {target}")
            del self.clients[target]
            socket.send(b"user not found")
        return True

    def _handle_list(self, socket):
        """Reply with a comma-separated list of online usernames (original casing)."""
        user_list = ", ".join(sock.display_name for sock in self.clients.values()) if self.clients else "no users online"
        socket.send(f"online users: {user_list}".encode())
        return True


ip = sys.argv[1]
port = int(sys.argv[2])

server = IRCServer()
server.start(ip, port)