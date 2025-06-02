import socket
import threading
import random
from file_chunker import divide_file_to_chunks, CHUNK_SIZE
from torrent_metadata import TorrentMetadata
from time import sleep
from piece_manager import PieceManager
import sys
import argparse
import requests
import os
import json
from hashing import verify_chunk
import tkinter as tk
from tkinter import filedialog, messagebox

TRACKER_HOST = '127.0.0.1'  # the host IP for the tracker server
TRACKER_PORT = 9090  # the port on which the tracker server is listening
MIN_PEERS_REQUIRED = 2  # minimum number of peers required to start downloading chunks

class Peer:
    def __init__(self, peer_ip, file_to_share=None, torrent_metadata_path=None):
        """
        Initializes the peer with the IP and the file to share
        PARAMETERS:
        peer_ip: the IP address of the peer
        file_to_share: Path to the file that this peer is sharing
        """
        self.peer_ip = peer_ip
        self.file_to_share = file_to_share
        self.torrent_metadata_path = torrent_metadata_path
        self.peer_chunks = {}  # Store local chunks of the file in memory
        self.received_chunks = set()  # Track downloaded chunks
        self.tracker_peers = {}  # Store other peers and the chunks they have
        self.total_chunks = 0  # Total number of chunks in the file
        self.peer_port = None  # The port number on which the peer listens for requests
        self.uploaded_chunks = {}  # Track how many chunks each peer has uploaded
        self.top_peers = []  # List of the top 4 peers sorted by upload contribution
        self.optimistic_peer = None  # Randomly select a peer for optimistic unchoking
        self.piece_manager = None  # PieceManager instance
        self.expected_hashes = None

        if not file_to_share and torrent_metadata_path:
            # Load expected hashes for leechers
            with open(torrent_metadata_path, 'r') as f:
                meta = json.load(f)
                self.expected_hashes = meta['piece_hashes']
                self.total_chunks = len(self.expected_hashes)
                self.piece_manager = PieceManager(self.total_chunks)  # Ensure piece_manager is initialized for leechers

    def start(self):
        """
        Starts the peer's operations:
        -> Listening for incoming requests
        -> Registering with the tracker
        -> Waiting for sufficient peers to connect
        -> Downloading chunks
        """
        # Start listening thread
        listening_thread = threading.Thread(target=self.listen_for_requests)
        listening_thread.start()

        while self.peer_port is None:
            sleep(0.1)

        if self.file_to_share:
            print(f"Sharing file: {self.file_to_share}")
            self.prepare_file_chunks()  # Prepare chunks for sharing if there is a file

        # Register with the tracker
        self.register_with_tracker()
        # Wait for the minimum number of peers
        self.wait_for_peers()
        # Periodically refresh top peers
        threading.Thread(target=self.refresh_top_peers_periodically).start()
        # Start downloading missing chunks
        self.download_chunks()

    def prepare_file_chunks(self):
        """
        Prepares chunks for sharing. If this is the first seeder, share all chunks for maximum swarm efficiency.
        Otherwise, share a random subset (as before).
        """
        chunks = list(divide_file_to_chunks(self.file_to_share))
        self.total_chunks = len(chunks)
        self.piece_manager = PieceManager(self.total_chunks)

        # Check if this is the only seeder (no other peers with chunks)
        is_first_seeder = False
        try:
            tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tracker_socket.connect((TRACKER_HOST, TRACKER_PORT))
            tracker_socket.send(b"REQUEST_PEERS")
            peer_list = tracker_socket.recv(4096).decode().split("\n")
            tracker_socket.close()
            # If no other peer has any chunks, this is the first seeder
            is_first_seeder = all((': ' not in p or p.endswith(': ')) for p in peer_list if p)
        except Exception:
            pass  # If tracker not available, fallback to random subset

        if is_first_seeder:
            # Share all chunks for the first seeder
            for chunk, chunk_hash, chunk_number in chunks:
                self.peer_chunks[chunk_number] = chunk
                print(f"[Seeder] Sharing ALL chunks: {chunk_number}")
        else:
            # Share a random subset for subsequent seeders
            num_chunks_to_have = max(1, self.total_chunks // 2)
            random_chunk_indices = random.sample(range(self.total_chunks), num_chunks_to_have)
            for index in random_chunk_indices:
                chunk, chunk_hash, chunk_number = chunks[index]
                self.peer_chunks[chunk_number] = chunk
                print(f"Prepared chunk {chunk_number} for sharing")

    def register_with_tracker(self):
        """
        Registers the peer and its available chunks with the tracker.
        Adds a user-friendly error if the tracker is not running.
        Also initializes piece_manager for leechers if needed.
        """
        try:
            tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tracker_socket.connect((TRACKER_HOST, TRACKER_PORT))
            available_chunks = " ".join(map(str, self.peer_chunks.keys()))
            registration_msg = f"ADD_PEER {self.peer_ip}:{self.peer_port} {available_chunks}"
            tracker_socket.send(registration_msg.encode())

            response = tracker_socket.recv(1024).decode()
            print(f"Tracker response: {response}")

            tracker_socket.send("REQUEST_PEERS".encode())
            peer_list = tracker_socket.recv(1024).decode().split("\n")
            tracker_socket.close()

            # For leechers: determine total_chunks from peer list if not set
            if not self.file_to_share and self.total_chunks == 0:
                max_chunk = 0
                for peer_info in peer_list:
                    if peer_info:
                        try:
                            _, chunks = peer_info.split(": ")
                            chunk_nums = [int(x) for x in chunks.split(",") if x.strip()]
                            if chunk_nums:
                                max_chunk = max(max_chunk, max(chunk_nums))
                        except Exception:
                            continue
                if max_chunk > 0:
                    self.total_chunks = max_chunk
                    self.piece_manager = PieceManager(self.total_chunks)

            for peer_info in peer_list:
                if peer_info:
                    try:
                        peer_addr, chunks = peer_info.split(": ")
                        # Accept empty chunk lists for leechers
                        if chunks.strip():
                            chunk_list = list(map(int, chunks.split(",")))
                        else:
                            chunk_list = []
                        self.tracker_peers[peer_addr] = chunk_list
                        if self.piece_manager and chunk_list:
                            self.piece_manager.update_available_pieces(chunk_list)
                    except Exception:
                        continue
            print(f"Known peers and their chunks: {self.tracker_peers}")
        except ConnectionRefusedError:
            print(f"[ERROR] Could not connect to tracker at {TRACKER_HOST}:{TRACKER_PORT}. Make sure the tracker server is running.")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Unexpected error registering with tracker: {e}")
            sys.exit(1)

    def wait_for_peers(self):
        """
        Waits until the minimum number of peers have connected before starting the downloads
        """
        print("Waiting for minimum peers to join...")
        while len(self.tracker_peers) < MIN_PEERS_REQUIRED:
            sleep(5)  # waiting for 5 seconds before checking again
            self.register_with_tracker()  # Refresh the list of peers from the tracker
        print("Minimum peer threshold has been reached, starting download process")

    def save_chunk_to_disk(self, chunk_data, chunk_number, output_dir="received_chunks"):
        """
        Saves a received chunk to disk in the specified directory.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        chunk_file_path = os.path.join(output_dir, f"chunk_{chunk_number}.chunk")
        with open(chunk_file_path, 'wb') as chunk_file:
            chunk_file.write(chunk_data)
        print(f"Saved chunk {chunk_number} to {chunk_file_path}")

    @staticmethod
    def get_public_ip():
        """
        Attempts to detect the public IP address of this machine using an external service.
        Returns the public IP as a string, or None if detection fails.
        """
        try:
            response = requests.get('https://api.ipify.org?format=text', timeout=5)
            if response.status_code == 200:
                return response.text.strip()
        except Exception as e:
            print(f"[WARN] Could not detect public IP: {e}")
        return None

    def download_chunks(self):
        """
        Downloads missing chunks from other peers and saves them to disk.
        """
        while len(self.received_chunks) < self.total_chunks:
            # Get the rarest piece first
            rarest_piece = self.piece_manager.get_rarest_piece()

            if rarest_piece:
                # Try to download the rarest piece from the peers
                for peer_addr in self.tracker_peers:
                    if rarest_piece in self.tracker_peers[peer_addr]:
                        success, received_chunk = self.request_chunk_from_peer(peer_addr, rarest_piece)
                        if success:
                            self.received_chunks.add(rarest_piece)
                            self.piece_manager.mark_piece_complete(rarest_piece)
                            self.save_chunk_to_disk(received_chunk, rarest_piece)
                            print(f"Downloaded chunk {rarest_piece} from {peer_addr}")
                            self.display_progress()
                            break

            # Check if all chunks have been downloaded
            if len(self.received_chunks) == self.total_chunks:
                print("Download complete! You are now a seeder")
                self.reconstruct_file_from_chunks()
                break
            sleep(5)  # Wait before retrying

    def reconstruct_file_from_chunks(self, output_file="reconstructed_download.txt", chunk_dir="received_chunks"):
        """
        Reconstructs the original file from all downloaded chunks in the correct order.
        """
        if self.total_chunks == 0:
            print("[ERROR] No chunks to reconstruct.")
            return
        chunk_files = []
        for i in range(1, self.total_chunks + 1):
            chunk_path = os.path.join(chunk_dir, f"chunk_{i}.chunk")
            if not os.path.exists(chunk_path):
                print(f"[ERROR] Missing chunk: {chunk_path}")
                return
            chunk_files.append(chunk_path)
        with open(output_file, "wb") as out_f:
            for chunk_path in chunk_files:
                with open(chunk_path, "rb") as c_f:
                    out_f.write(c_f.read())
        print(f"Successfully reconstructed file as {output_file}")

    def display_progress(self):
        """ 
        Displays the download progress as a percentage.
        """
        progress = (len(self.received_chunks) / self.total_chunks) * 100
        print(f"File download progress: {progress:.2f}%")

    def listen_for_requests(self):
        """
        Listening for incoming requests from other peers asking for chunks.
        Now robust to port conflicts: if the port is in use, try the next one.
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_port = getattr(self, 'listen_port', 8000)
        max_tries = 20
        tries = 0
        while tries < max_tries:
            try:
                server_socket.bind(('0.0.0.0', listen_port))
                break
            except OSError as e:
                if e.errno == 10048:  # Address already in use
                    print(f"[WARN] Port {listen_port} in use, trying next port...")
                    listen_port += 1
                    tries += 1
                    sleep(0.5)
                else:
                    raise
        else:
            print(f"[ERROR] Could not bind to any port after {max_tries} attempts.")
            sys.exit(1)
        self.peer_port = server_socket.getsockname()[1]  # Store the assigned port
        print(f"Listening for chunk requests on port {self.peer_port}...")

        server_socket.listen(5)
        while True:
            conn, addr = server_socket.accept()
            print(f"Connection from {addr}")
            threading.Thread(target=self.handle_chunk_request, args=(conn,)).start()

    def handle_chunk_request(self, conn):
        """
        Handles requests for chunks from other peers.
        """
        try:
            chunk_number = int(conn.recv(1024).decode())  # Reading the requested chunk number
            if chunk_number in self.peer_chunks:
                conn.send(self.peer_chunks[chunk_number])  # Sending the requested chunk
                # Update the upload contribution for the requesting peer
                peer_ip = conn.getpeername()[0]
                self.uploaded_chunks[peer_ip] = self.uploaded_chunks.get(peer_ip, 0) + 1
                print(f"Uploaded chunk {chunk_number} to {peer_ip}")
            else:
                conn.send(b"CHUNK_NOT_FOUND")  # Inform if the chunk is not available
        except Exception as e:
            print(f"Error handling chunk request: {e}")
        finally:
            conn.close()

    def request_chunk_from_peer(self, peer_addr, chunk_number):
        """
        Requests a specific chunk from another peer.
        PARAMETERS:
        peer_addr: The address of the peer to request from.
        chunk_number: The number of the chunk to request.
        """
        try:
            peer_ip, peer_port = peer_addr.split(":")
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((peer_ip, int(peer_port)))
            peer_socket.send(str(chunk_number).encode())  # Send the chunk request
            
            # Receive the chunk data
            chunk_data = peer_socket.recv(CHUNK_SIZE)
            peer_socket.close()

            # Check if the chunk was not found
            if chunk_data == b"CHUNK_NOT_FOUND":
                print(f"Chunk {chunk_number} not found on peer {peer_addr}")
                return False, f"Chunk {chunk_number} not found on peer {peer_addr}"
            
            # Return the successfully retrieved chunk data
            return True, chunk_data

        except Exception as e:
            print(f"Error requesting chunk {chunk_number} from {peer_addr}: {e}")
            # Return False with the error message
            return False, f"Error requesting chunk {chunk_number} from {peer_addr}: {e}"

    def update_top_peers(self):
        """
        Updates the list of top 4 peers based on the number of chunks they've uploaded.
        """
        sorted_peers = sorted(self.uploaded_chunks.items(), key=lambda item: item[1], reverse=True)
        self.top_peers = [peer[0] for peer in sorted_peers[:4]]  # Top 4 peers by upload contribution
        
        # Select a random peer outside the top 4 for optimistic unchoking
        non_top_peers = [peer for peer in self.tracker_peers if peer not in self.top_peers]
        self.optimistic_peer = random.choice(non_top_peers) if non_top_peers else None

        print(f"Top 4 peers: {self.top_peers}")
        print(f"Optimistically unchoked peer: {self.optimistic_peer}")

    def refresh_top_peers_periodically(self, interval=30):
        """
        Periodically refreshes the list of top peers every given interval.
        PARAMETERS:
        interval: Time in seconds between each refresh.
        """
        while True:
            self.update_top_peers()  # Update the top peers
            sleep(interval)

class PeerGUI:
    def __init__(self, master):
        self.master = master
        master.title("P2P File Sharing Peer")
        master.geometry("480x420")

        self.role_var = tk.StringVar(value="seeder")
        self.file_path = tk.StringVar()
        self.torrent_path = tk.StringVar()
        self.peer_ip = tk.StringVar(value="127.0.0.1")
        self.port = tk.StringVar(value="8000")
        self.tracker_host = tk.StringVar(value=TRACKER_HOST)
        self.peer_thread = None
        self.peer_instance = None
        self.running = False

        # Title
        tk.Label(master, text="P2P File Sharing Peer", font=("Arial", 16, "bold")).pack(pady=8)

        # Role selection
        role_frame = tk.Frame(master)
        role_frame.pack(pady=2)
        tk.Label(role_frame, text="Peer Role:").pack(side=tk.LEFT)
        tk.Radiobutton(role_frame, text="Seeder", variable=self.role_var, value="seeder", command=self.toggle_role).pack(side=tk.LEFT)
        tk.Radiobutton(role_frame, text="Leecher", variable=self.role_var, value="leecher", command=self.toggle_role).pack(side=tk.LEFT)

        # Peer IP/Port/Tracker
        form_frame = tk.Frame(master)
        form_frame.pack(pady=2)
        tk.Label(form_frame, text="Peer IP:").grid(row=0, column=0, sticky=tk.W)
        tk.Entry(form_frame, textvariable=self.peer_ip, width=18).grid(row=0, column=1)
        tk.Label(form_frame, text="Port:").grid(row=0, column=2, sticky=tk.W)
        tk.Entry(form_frame, textvariable=self.port, width=8).grid(row=0, column=3)
        tk.Label(form_frame, text="Tracker Host:").grid(row=1, column=0, sticky=tk.W)
        tk.Entry(form_frame, textvariable=self.tracker_host, width=18).grid(row=1, column=1)

        # File/torrent selection
        self.file_frame = tk.Frame(master)
        self.file_frame.pack(pady=2)
        tk.Label(self.file_frame, text="File to Share:").pack(side=tk.LEFT)
        tk.Entry(self.file_frame, textvariable=self.file_path, width=28).pack(side=tk.LEFT)
        tk.Button(self.file_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT)

        self.torrent_frame = tk.Frame(master)
        self.torrent_frame.pack(pady=2)
        tk.Label(self.torrent_frame, text=".torrent File:").pack(side=tk.LEFT)
        tk.Entry(self.torrent_frame, textvariable=self.torrent_path, width=28).pack(side=tk.LEFT)
        tk.Button(self.torrent_frame, text="Browse", command=self.browse_torrent).pack(side=tk.LEFT)

        # Start/Stop buttons
        btn_frame = tk.Frame(master)
        btn_frame.pack(pady=8)
        self.start_button = tk.Button(btn_frame, text="Start Peer", command=self.start_peer, width=14, bg="#4CAF50", fg="white")
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = tk.Button(btn_frame, text="Stop Peer", command=self.stop_peer, width=14, state=tk.DISABLED, bg="#f44336", fg="white")
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.new_window_button = tk.Button(btn_frame, text="New Peer Window", command=self.launch_new_window, width=16, bg="#2196F3", fg="white")
        self.new_window_button.pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_var = tk.StringVar(value="Idle.")
        tk.Label(master, textvariable=self.status_var, fg="blue", font=("Arial", 11, "bold")).pack(pady=2)

        # Output box
        self.output_text = tk.Text(master, height=10, width=58, state=tk.DISABLED, bg="#f7f7f7")
        self.output_text.pack(pady=4)

        self.toggle_role()

    def toggle_role(self):
        if self.role_var.get() == "seeder":
            self.file_frame.pack(pady=2)
            self.torrent_frame.forget()
        else:
            self.torrent_frame.pack(pady=2)
            self.file_frame.forget()
        self.status_var.set("Idle.")
        self.clear_output()

    def browse_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.file_path.set(path)

    def browse_torrent(self):
        path = filedialog.askopenfilename(filetypes=[("Torrent Files", "*.torrent")])
        if path:
            self.torrent_path.set(path)

    def launch_new_window(self):
        import subprocess, sys, os
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        subprocess.Popen([python_exe, script_path])

    def start_peer(self):
        if self.running:
            messagebox.showinfo("Peer Running", "Peer is already running in this window.\nOpen a new window for another peer.")
            return
        role = self.role_var.get()
        ip = self.peer_ip.get()
        port = int(self.port.get())
        tracker = self.tracker_host.get()
        file = self.file_path.get() if role == "seeder" else None
        torrent = self.torrent_path.get() if role == "leecher" else None
        if role == "seeder" and not file:
            messagebox.showerror("Missing File", "Please select a file to share.")
            return
        if role == "leecher" and not torrent:
            messagebox.showerror("Missing Torrent", "Please select a .torrent file.")
            return
        self.clear_output()
        self.status_var.set(f"Starting {role}...")
        self.append_output(f"[INFO] Starting {role} on {ip}:{port}\n")
        global TRACKER_HOST
        TRACKER_HOST = tracker
        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.peer_thread = threading.Thread(target=self.run_peer, args=(ip, file, torrent, port, role), daemon=True)
        self.peer_thread.start()

    def run_peer(self, ip, file, torrent, port, role):
        try:
            self.peer_instance = Peer(ip, file, torrent)
            self.peer_instance.listen_port = port
            # Patch print to redirect output
            import builtins
            orig_print = builtins.print
            def gui_print(*args, **kwargs):
                msg = ' '.join(str(a) for a in args)
                self.append_output(msg + "\n")
                orig_print(*args, **kwargs)
            builtins.print = gui_print
            self.peer_instance.start()
            builtins.print = orig_print
            self.status_var.set(f"{role.capitalize()} finished. (You are now a seeder!)" if role == "leecher" else f"Seeder running.")
        except Exception as e:
            self.append_output(f"[ERROR] {e}\n")
            self.status_var.set("Error occurred.")
        finally:
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def stop_peer(self):
        # This is a soft stop; for a real stop, you'd need to add stop logic to Peer
        self.status_var.set("Peer stopped (restart app to fully stop threads).")
        self.append_output("[INFO] Peer stopped. (Threads may still be running in background.)\n")
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def append_output(self, msg):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, msg)
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def clear_output(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = PeerGUI(root)
    root.mainloop()
