import hashlib

def calculate_sha1(data):
    """
    Calculates the SHA1 hash for a given data chunk.

    :param data: The data to hash.
    :return: SHA1 hash of the data as a hex string.
    """
    sha1 = hashlib.sha1()
    sha1.update(data)
    return sha1.hexdigest()

def verify_chunk(chunk_data, expected_hash):
    """
    Verifies that the SHA1 hash of the given chunk data matches the expected hash.

    :param chunk_data: The chunk data to verify.
    :param expected_hash: Expected SHA1 hash of the chunk.
    :return: True if the chunk matches the expected hash, False otherwise.
    """
    return calculate_sha1(chunk_data) == expected_hash
