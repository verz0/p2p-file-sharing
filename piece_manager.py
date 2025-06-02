from collections import defaultdict
import random

class PieceManager:
    def __init__(self, total_pieces):
        """
        Initializes the PieceManager.
        PARAMETERS:
        total_pieces: Total number of pieces in the file.
        """
        self.total_pieces = total_pieces
        self.available_pieces = defaultdict(int)  # Tracks the number of copies for each piece
        self.missing_pieces = set(range(1, total_pieces + 1))  # Tracks missing pieces

    def update_available_pieces(self, peer_chunks):
        """
        Updates the availability of pieces based on a peer's available chunks.
        PARAMETERS:
        peer_chunks: List of chunk numbers that a peer has.
        """
        for piece in peer_chunks:
            self.available_pieces[piece] += 1

    def get_rarest_piece(self):
        """
        Returns the rarest piece that is still missing.
        RETURNS:
        The rarest piece number or None if all pieces are acquired.
        """
        rarest_piece = None
        min_count = float('inf')

        for piece, count in self.available_pieces.items():
            if piece in self.missing_pieces and count < min_count:
                min_count = count
                rarest_piece = piece

        return rarest_piece

    def mark_piece_complete(self, piece_number):
        """
        Marks a piece as complete and removes it from the missing set.
        PARAMETERS:
        piece_number: The piece number that has been completed.
        """
        self.missing_pieces.discard(piece_number)

    def is_complete(self):
        """
        Checks if all pieces have been downloaded.
        RETURNS:
        True if all pieces are complete, False otherwise.
        """
        return len(self.missing_pieces) == 0
