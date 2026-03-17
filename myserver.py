"""
python3 myserver.py localhost 8090
"""

import sys
from ex2utils import Server


class IRCServer(Server):

    # initialise server-wide state on startup
    def onStart(self):
        self.clients = {}       # maps username -> socket for registered users kinda like a hashmap/dictionary
        self.client_count = 0
        self.printOutput("Server started")

    # fires when a new TCP connection arrives
    def onConnect(self, socket):
        socket.username = None
        self.client_count += 1
        self.printOutput("new client connected")
        self.printOutput(f"{self.client_count} active clients")

    #fires when a connection drops for any reason
    def onDisconnect(self, socket):
        if socket.username and socket.username in self.clients:
            del self.clients[socket.username]
        self.client_count -= 1
        self.printOutput("a client disconnected")
        self.printOutput(f"{self.client_count} active clients")

    # parse command and dispatch to the right handler
    def onMessage(self, socket, message):
        message = message.strip('\r')

        self.printOutput(message)

        # split into command and everything after it
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

        # SEND: broadcast to every connected user
        if command == "SEND":
            return self._handle_send(socket, params)

        # SEND_TO: private message to one user
        if command == "SEND_TO":
            return self._handle_send_to(socket, params)

        #  anything else is unknown
        socket.send(b"unknown command")
        return True


    def _handle_register(self, socket, username):
        """Register the given username, rejecting duplicates."""
        if not username:
            socket.send(b"unknown command")
            return True
        if username in self.clients:
            socket.send(b"username taken")
            return True
        socket.username = username
        self.clients[username] = socket
        self.printOutput(f"{username} registered")
        socket.send(f"welcome {username}".encode())
        return True

    def _handle_send(self, socket, message):
        """Broadcast a message from this user to everyone."""
        if not message:
            socket.send(b"empty message - format should be SEND <msg>")
            return True
        formatted = f"message from {socket.username}: {message}"
        for client in self.clients.values():
            client.send(formatted.encode())
        return True

    def _handle_send_to(self, socket, params):
        """Send a private message to a single named user."""
        parts = params.split(" ", 1)
        # need both a target name and a non-empty message body
        if len(parts) < 2 or not parts[1].strip():
            socket.send(b"empty message or no user listed - format should be SEND_TO <user> <msg>")
            return True
        target = parts[0]
        msg_text = parts[1].strip()
        if target not in self.clients:
            socket.send(b"user not found")
            return True
        formatted = f"message from {socket.username}: {msg_text}"
        self.clients[target].send(formatted.encode())
        return True

    def _handle_list(self, socket):
        """Reply with a comma-separated list of online usernames."""
        user_list = ", ".join(self.clients.keys()) if self.clients else "no users online"
        socket.send(f"online users: {user_list}".encode())
        return True
    

ip = sys.argv[1]
port = int(sys.argv[2])

server = IRCServer()
server.start(ip, port)