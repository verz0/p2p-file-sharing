import unittest
from unittest.mock import patch, MagicMock
from peer import Peer

class TestPeer(unittest.TestCase):
    def setUp(self):
        """
        Create a Peer instance before every test.
        """
        self.peer = Peer()

    @patch('peer.socket.socket')
    def test_listen_for_requests(self, mock_socket):
        """
        Test if the peer starts listening on a dynamically assigned port.
        """
        mock_socket_inst = MagicMock()
        mock_socket.return_value = mock_socket_inst

        self.peer.listen_for_requests()
        mock_socket_inst.bind.assert_called()  # Ensure the socket is bound to a port
        mock_socket_inst.listen.assert_called_with(5)

    @patch('peer.socket.socket')
    def test_request_chunk(self, mock_socket):
        """
        Test requesting a chunk from a peer.
        """
        mock_socket_inst = MagicMock()
        mock_socket.return_value = mock_socket_inst
        mock_socket_inst.recv.return_value = b'test_chunk_data'  # Mock received chunk data

        chunk = self.peer.request_chunk("127.0.0.1", 1, 9090)
        self.assertEqual(chunk, b'test_chunk_data')  # Ensure the correct chunk data is returned
        mock_socket_inst.connect.assert_called_with(("127.0.0.1", 9090))
        mock_socket_inst.send.assert_called_with(b'1')

    @patch('peer.socket.socket')
    def test_request_chunk_not_found(self, mock_socket):
        """
        Test behavior when requesting a chunk that is not found on the peer.
        """
        mock_socket_inst = MagicMock()
        mock_socket.return_value = mock_socket_inst
        mock_socket_inst.recv.return_value = b'CHUNK_NOT_FOUND'

        chunk = self.peer.request_chunk("127.0.0.1", 1, 9090)
        self.assertIsNone(chunk)  # Ensure None is returned for missing chunk
        mock_socket_inst.connect.assert_called_with(("127.0.0.1", 9090))

    @patch('peer.socket.socket')
    def test_connect_to_tracker(self, mock_socket):
        """
        Test connecting to the tracker and retrieving the list of peers.
        """
        mock_socket_inst = MagicMock()
        mock_socket.return_value = mock_socket_inst
        mock_socket_inst.recv.side_effect = [
            b'PEER_ADDED',  # First call simulates peer registration
            b'127.0.0.1:9090\n127.0.0.2:9091'  # Second call simulates peers list
        ]

        peers = self.peer.connect_to_tracker()
        self.assertEqual(peers, ['127.0.0.1:9090', '127.0.0.2:9091'])  # Check if peer list matches

    @patch('peer.socket.socket')
    def test_add_chunk_and_handle_request(self, mock_socket):
        """
        Test if the peer can correctly handle chunk requests.
        """
        # Prepare a chunk to be served
        self.peer.peer_chunks = {1: b'test_chunk_data'}
        
        client_socket = MagicMock()
        client_socket.recv.return_value = b'1'
        
        self.peer.handle_chunk_request(client_socket)
        client_socket.send.assert_called_with(b'test_chunk_data')  # Ensure correct chunk is sent
    
    @patch('peer.socket.socket')
    def test_handle_missing_chunk_request(self, mock_socket):
        """
        Test behavior when a peer requests a chunk that is not available.
        """
        client_socket = MagicMock()
        client_socket.recv.return_value = b'99'  # Request a non-existent chunk
        
        self.peer.handle_chunk_request(client_socket)
        client_socket.send.assert_called_with(b'CHUNK_NOT_FOUND')  # Ensure 'CHUNK_NOT_FOUND' is sent

    def test_update_top_peers(self):
        """
        Test updating the top 4 peers based on upload contribution.
        """
        # Simulate uploaded chunks for several peers
        self.peer.uploaded_chunks = {
            "127.0.0.1": 5,
            "127.0.0.2": 3,
            "127.0.0.3": 8,
            "127.0.0.4": 2,
            "127.0.0.5": 10
        }
        self.peer.peers = ["127.0.0.1", "127.0.0.2", "127.0.0.3", "127.0.0.4", "127.0.0.5"]

        self.peer.update_top_peers()
        self.assertEqual(self.peer.top_peers, ["127.0.0.5", "127.0.0.3", "127.0.0.1", "127.0.0.2"])
        self.assertIn(self.peer.optimistic_peer, ["127.0.0.4"])  # Non-top peers

if __name__ == '__main__':
    unittest.main()
