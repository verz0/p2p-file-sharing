import unittest
import subprocess
import time
import socket

class TestP2PSystem(unittest.TestCase):
    def setUp(self):
        """
        Start the tracker server before every test.
        """
        # Start the tracker server as a subprocess
        self.tracker_process = subprocess.Popen(['python3', 'tracker.py'])
        time.sleep(2)  # Wait for the tracker to initialize

    def tearDown(self):
        """
        Terminate the tracker and any peer subprocesses after each test.
        """
        # Terminate tracker process
        self.tracker_process.terminate()
        time.sleep(1)  # Give it some time to cleanly terminate

    def start_peer(self, peer_ip, file_to_share=None):
        """
        Helper function to start a peer subprocess.
        """
        args = ['python3', 'peer.py', peer_ip]
        if file_to_share:
            args.append(file_to_share)
        return subprocess.Popen(args)

    def test_peer_registration_and_discovery(self):
        """
        Test that peers can register with the tracker and discover each other.
        """
        # Start two peer processes
        peer1 = self.start_peer('127.0.0.1', 'file1.txt')
        peer2 = self.start_peer('127.0.0.2', 'file2.txt')

        time.sleep(5)  # Give peers time to register with the tracker

        # Connect to the tracker and request the list of peers
        tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tracker_socket.connect(('127.0.0.1', 9090))
        tracker_socket.send("REQUEST_PEERS".encode())
        peers_list = tracker_socket.recv(1024).decode().split("\n")
        tracker_socket.close()

        # Assert that both peers are in the list
        self.assertIn('127.0.0.1:8000', peers_list)  # Peer 1's IP and port
        self.assertIn('127.0.0.2:8000', peers_list)  # Peer 2's IP and port

        # Terminate peer processes
        peer1.terminate()
        peer2.terminate()

    def test_peer_chunk_exchange(self):
        """
        Test that peers can request and exchange file chunks with each other.
        """
        # Start two peers
        peer1 = self.start_peer('127.0.0.1', 'file1.txt')
        peer2 = self.start_peer('127.0.0.2')

        time.sleep(5)  # Give peers time to register with the tracker

        # Peer 2 requests chunk 1 from peer 1
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.connect(('127.0.0.1', 8000))  # Peer 1's listening port
        peer_socket.send(b'1')  # Request chunk 1
        chunk_data = peer_socket.recv(1024)
        peer_socket.close()

        # Assert that peer 2 successfully received the chunk
        self.assertNotEqual(chunk_data, b'CHUNK_NOT_FOUND')
        self.assertGreater(len(chunk_data), 0)

        # Terminate peer processes
        peer1.terminate()
        peer2.terminate()

    def test_optimistic_unchoking(self):
        """
        Test that the peer correctly handles optimistic unchoking for non-top peers.
        """
        # Start 5 peers
        peer1 = self.start_peer('127.0.0.1', 'file1.txt')
        peer2 = self.start_peer('127.0.0.2')
        peer3 = self.start_peer('127.0.0.3')
        peer4 = self.start_peer('127.0.0.4')
        peer5 = self.start_peer('127.0.0.5')

        time.sleep(10)  # Wait for peers to upload/download and establish optimistic unchoking

        # We could monitor logs for peer unchoking status and verify the optimistic unchoking peer

        # Terminate peer processes
        peer1.terminate()
        peer2.terminate()
        peer3.terminate()
        peer4.terminate()
        peer5.terminate()

if __name__ == '__main__':
    unittest.main()
