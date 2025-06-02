import os
import hashlib

CHUNK_SIZE = 64 * 1024 ## just keeping the chunk size at 64 KB

def divide_file_to_chunks(path, chunk_size=CHUNK_SIZE):
    """
    This function aims at dividing a file into smaller chunks
    then calculates a SHA1 hash for each chunk for integrity,
    yields the chunk data along with the hash and the sequential
    chunk number.
    PARAMETERS:
    path: Path of the file that we want to divide and share 
    chunk_size= Size of each chunk (I have fixed it to 64 can be dynamic)
    yield: it creates a tuple having the chunk data, SHA1 hash, 
    and chunk number for ease of understanding
    """
    if not os.path.exists(path):
        raise FileNotFoundError (f"File {path} does not exist") # Covering the edge case of no file found
    
    chunk_number = 1 # initializing the chunks from 1
    
    with open(path, 'rb') as file:
        while chunk := file.read(chunk_size): ## reading the file as chunks of the specified size
            chunk_hash = hashlib.sha1(chunk).hexdigest() # computing sha1 hash for the current chunk
            yield chunk, chunk_hash, chunk_number # returns the chunk data, chunk hash value and chunk no.
            chunk_number += 1 # increasing the chunk sequence iteratively

def write_chunk_to_file(chunk_data, chunk_number, output_dir = "chunks"):
    """
    This function is aimed at saving a chunk to a file in my specified directory
    PARAMETERS:
    chunk_data : The data of the chunk in binary
    chunk_number: The number of the chunk(I am also using this for naming the file)
    output_dir: Directory to store the chunk files
    """
    if not os.path.exists(output_dir): ## covering an edge case if the output directory doesn't exist
        os.makedirs(output_dir)
    
    chunk_file_path = os.path.join(output_dir, f"chunk_{chunk_number}.chunk") ## creating the file path for the chunk while naming it as per the sequence no.
    with open(chunk_file_path, 'wb') as chunk_file:
        chunk_file.write(chunk_data) ## writing the chunk data in the file.
    print(f" Chunk {chunk_number} saved to {chunk_file_path}")

def print_chunk_data(path, chunk_number_to_display=1):
    """
    Prints data of a specific chunk for demonstration purposes for the blog, including the hash.
    PARAMETERS:
    file_path: Path to the file to be divided into chunks
    chunk_number_to_display: The specific chunk number to display data for
    """
    for chunk, chunk_hash, chunk_number in divide_file_to_chunks(path):
        if chunk_number == chunk_number_to_display:
            print(f"Chunk {chunk_number} hash: {chunk_hash}")
            print(f"Chunk {chunk_number} data:\n{chunk.decode(errors='replace')[:100]}...")  # I am Printing the first 100 characters
            break


if __name__ == "__main__":
    
    path = "/Users/prabhudattamishra/Desktop/P2P/dark_knight.txt"  # Replace it with your own path later 

    # Printing a chunk's data for better understanding
    print_chunk_data(path, chunk_number_to_display=1)

    # saving the data to the disk with the hash number
    output_directory = "/Users/prabhudattamishra/Desktop/P2P/chunks"  # Modify as needed
    for chunk, chunk_hash, chunk_number in divide_file_to_chunks(path):
        write_chunk_to_file(chunk, chunk_number, output_dir=output_directory)
        print(f"Chunk {chunk_number} hash: {chunk_hash}")
