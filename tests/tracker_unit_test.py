import unittest
from unittest.mock import patch, MagicMock
from tracker import Tracker

class TestTracker(unittest.TestCase):

    def setUp(self):
        self.tracker = Tracker()

    @patch('tracker.socket.socket')
    def test_add_peer(self, mock_socket):
        client_socket = MagicMock()
        self.tracker.add_peer(client_socket, "ADD_PEER 127.0.0.1:8000")
        self.assertIn("127.0.0.1:8000", self.tracker.peers)
        client_socket.send.assert_called_with(b"PEER_ADDED")

    @patch('tracker.socket.socket')
    def test_add_duplicate_peer(self, mock_socket):
        client_socket = MagicMock()
        self.tracker.peers.append("127.0.0.1:8000")  # Simulate already added peer
        self.tracker.add_peer(client_socket, "ADD_PEER 127.0.0.1:8000")
        client_socket.send.assert_called_with(b"PEER_ALREADY_EXISTS")

    @patch('tracker.socket.socket')
    def test_send_peer_list(self, mock_socket):
        client_socket = MagicMock()
        self.tracker.peers.append("127.0.0.1:8000")
        self.tracker.send_peers_list(client_socket, "127.0.0.1")
        client_socket.send.assert_called_with(b"127.0.0.1:8000")

if __name__ == '__main__':
    unittest.main()
