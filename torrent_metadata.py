import os
import json
import hashlib

class TorrentMetadata:
    def __init__(self, file_path, tracker_url, chunk_size=256 * 1024):
        self.file_path = file_path
        self.tracker_url = tracker_url
        self.chunk_size = chunk_size
        self.piece_hashes = []  # Stores SHA1 hashes of each chunk
        self.total_size = None

    def generate_metadata(self):
        """
        Generates metadata including piece hashes for each chunk and total file size.
        This information is stored in a dictionary and can be saved as a .torrent JSON file.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File {self.file_path} does not exist.")
        
        # Calculate the total file size
        self.total_size = os.path.getsize(self.file_path)
        
        # Calculate hashes for each chunk and add to piece_hashes
        with open(self.file_path, 'rb') as file:
            while chunk := file.read(self.chunk_size):
                chunk_hash = hashlib.sha1(chunk).hexdigest()
                self.piece_hashes.append(chunk_hash)
        
        metadata = {
            "file_name": os.path.basename(self.file_path),
            "tracker_url": self.tracker_url,
            "chunk_size": self.chunk_size,
            "total_size": self.total_size,
            "piece_hashes": self.piece_hashes
        }
        
        return metadata

    def save_metadata_to_file(self, output_path):
        """
        Saves the generated metadata to a JSON file, which acts as the .torrent file.
        
        :param output_path: Path where the metadata file will be saved.
        """
        metadata = self.generate_metadata()
        with open(output_path, 'w') as metafile:
            json.dump(metadata, metafile, indent=4)
        print(f"Metadata saved to {output_path}")

    @staticmethod
    def load_metadata(file_path):
        """
        Loads metadata from a JSON file.
        
        :param file_path: Path to the .torrent JSON file.
        :return: Metadata dictionary
        """
        with open(file_path, 'r') as metafile:
            metadata = json.load(metafile)
        return metadata

# Example usage
if __name__ == "__main__":
    file_path = "/Users/prabhudattamishra/Desktop/P2P/dark_knight.txt"  # Replace with actual file path
    tracker_url = "http://127.0.0.1:9090/announce"  # Example tracker URL
    
    torrent_metadata = TorrentMetadata(file_path, tracker_url)
    
    # Generate and save metadata
    output_path = "/Users/prabhudattamishra/Desktop/P2P/dark_knight.torrent"  # Modify as needed
    torrent_metadata.save_metadata_to_file(output_path)
    
    # Load metadata (for testing)
    loaded_metadata = TorrentMetadata.load_metadata(output_path)
    print("Loaded metadata:", loaded_metadata)
