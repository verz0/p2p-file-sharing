import socket 
import threading 

class Tracker:
    def __init__(self, host="0.0.0.0", port=9090):
        
        """
        Initializes the tracker server with a specified host and port.
        PARAMETERS:
        host: The IP address to which the tracker server binds to. I have set it up at '0.0.0.0'
        port: The port number on which the tracker server will listen for incoming peer connections
        """
        self.host = host
        self.port = port
        self.peers = {} ## this is a dictionary to store peer addresses and the chunks they have
        self.peer_connections = {} ## Keep trackn of peer connections for broadcasting

    def start(self):
        """
        Starting the tracker server to manage the peers for a connection.
        The server is binding to the specified host and port and keeps on listening on that port
        for peer connections, all peer connections are handled in a separate thread.
        """
        try:
            ## creating a socket for the tracker server
            tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tracker_socket.bind((self.host, self.port)) ## binding the socket to the specified host and port
            tracker_socket.listen(5) ## listening for incoming connections, with a maximum backlog of 5
            print(f"Tracker started on {self.host}:{self.port}, waiting for peers....")

            while True:
                client_socket, addr = tracker_socket.accept()
                print(f"Peer {addr} connected.")
                ## here i will start a new thread to handle the peer connection.
                threading.Thread(target=self.handle_peer, args =(client_socket, addr)).start()
        except Exception as e:
            print(f"Error in tracker operation: {e}")
        finally:
             # Ensuring the tracker socket is closed if an error occurs.
            tracker_socket.close()

    def handle_peer(self, client_socket, addr):
        """
        This is one of the crucial function of our system.
        Manages communication with the peer.
        This method handles a request from a peer, such as requesting the peer list,
        adding or removing a peer and broadcasting updates to all peers.
        It keeps on listening to the peer connection until it is closed
        PARAMETERS:
        client_socket: This socket is used for communicating with the connected peer.
        addr: Address of the connected peer(It's host and port)
        """
        try:
            while True:
                data= client_socket.recv(1024).decode()
                ## If not receiving any data , breaking the loop to exit the connection
                if not data:
                    break

                ## Handling different types of requests from the peer
                if data == "REQUEST_PEERS":
                    ## sending the list, if the peer requests the list of other peers
                    self.send_peers_list(client_socket, addr)
                elif data.startswith("ADD_PEER"):
                    ## if the peer wants to be added to the tracker, we update the list and broadcast to others
                    self.add_peer(client_socket, data)
                    self.broadcast_peer_list()
                elif data.startswith("REMOVE_PEER"):
                    ## if the peers is removing itself, we update the list and broadcast to the others
                    self.remove_peer(client_socket, addr)
                    self.broadcast_peer_list()
                else:
                    # Handle any unrecognized requests.
                    print(f"Unknown request from {addr}: {data}")
        
        except Exception as e:
            print(f"Error handling peer {addr}: {e}")
        
        finally:
            # Close the socket connection with the peer.
            client_socket.close()
            # Removing the peer from the tracker, for ensuring it's no longer in the list.
            self.remove_peer(None, addr)

    def send_peers_list(self, client_socket, addr):
        """
        Sends the list of known peers and their chunks to the connected peers.
        PARAMETERS:
        client_socket: The socket used to communicate with the connected peer.
        addr: The address of the connected peer.

        """
        try:
            if self.peers:
                # Formatting the  peer list with the chunks the peers have
                peer_list = "\n".join([f"{peer}: {','.join(map(str, chunks))}" for peer, chunks in self.peers.items()])
            else:
                peer_list = "NO_PEERS"  # If no peers are available, inform the peer
            print(f"Sending peer list to {addr}: {peer_list}")
            client_socket.send(peer_list.encode())
        except Exception as e:
            print(f"Error sending peer list to {addr}: {e}")

    def add_peer(self, client_socket, data):
        """
        Adds a peer to the peer list and registers the chunks they have.
        Handles leechers (peers with no chunks) gracefully.
        """
        try:
            parts = data.split(" ")
            peer_ip = parts[1]
            # If no chunks are provided, treat as an empty list (leecher)
            if len(parts) > 2 and any(parts[2:]):
                chunks = [int(x) for x in parts[2:] if x.strip()]
            else:
                chunks = []
            if peer_ip not in self.peers:
                self.peers[peer_ip] = chunks
                self.peer_connections[peer_ip] = client_socket
                print(f"Peer {peer_ip} with chunks {chunks} added.")
                client_socket.send("PEER_ADDED".encode())
            else:
                self.peers[peer_ip] = chunks
                client_socket.send("PEER_UPDATED".encode())
            print(f"Current list of peers: {self.peers}")
        except Exception as e:
            print(f"Error adding peer: {e}")
            client_socket.send("ERROR".encode())

    def remove_peer(self, client_socket, addr):
        """
        Removes a peer from the list when they disconnect or request removal.
        PARAMETERS:
        client_socket: The socket used to communicate with the connected peer.
        addr: The address of the peer to be removed
        """
        try:
            # Extract the Ip address of the peer.
            peer_ip = addr[0]
            if peer_ip in self.peers:
                ## Removing the Ip address of the peer from both the dictionaries.
                del self.peers[peer_ip]
                if peer_ip in self.peer_connections:
                    del self.peer_connections[peer_ip]
                print(f"Peer {peer_ip} removed.")
                ## Informing that the client has been removed from the dictionaries.
                if client_socket:
                    client_socket.send("PEER_REMOVED".encode())
            else:
                ## Edge case for handling if the peer is not found
                if client_socket:
                    client_socket.send("PEER_NOT_FOUND".encode())
        except Exception as e:
            print(f"Error removing peer {addr}: {e}")

    def broadcast_peer_list(self):
        """
        Broadcasts the updated peer list and their 
        chunks to all connected peers.

        """
        # Create a formatted string of all peers and their chunks.
        peer_list = "\n".join([f"{peer}: {','.join(map(str, chunks))}" for peer, chunks in self.peers.items()])
        for peer, connection in self.peer_connections.items():
            try:
                # Send the updated peer list to each connected peer.
                print(f"Broadcasting updated peer list to {peer}: {peer_list}")
                connection.send(peer_list.encode())
            except Exception as e:
                # Handle any errors that occur during broadcasting.
                print(f"Error broadcasting to {peer}: {e}")

if __name__ == "__main__":
    ## Started an instance of the tracker class
    tracker = Tracker()
    tracker.start()
