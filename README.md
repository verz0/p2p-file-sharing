# P2P File Sharing System (BitTorrent-inspired)

This project is a simple BitTorrent-inspired peer-to-peer (P2P) file sharing system implemented in Python. It allows multiple peers to share and download files in chunks, coordinated by a tracker server. The system supports both local and LAN (same network) operation, and can reconstruct the original file from downloaded chunks.

---

## Features
- Chunk-based file sharing (like BitTorrent)
- Seeder/leecher roles
- Tracker server for peer discovery
- Robust to port conflicts and common errors
- Works on localhost and across machines in the same network
- Automatic file reconstruction after download

---

## Setup

### 1. Requirements
- Python 3.8+
- All dependencies in `requirements.txt` (install with `pip install -r requirements.txt`)
- All peers and tracker must be able to reach each other on the network (firewall rules may need to be adjusted)

### 2. Folder Structure
- `peer.py` - Main peer logic
- `tracker_server.py` - Tracker server
- `file_chunker.py`, `piece_manager.py`, etc. - Supporting modules
- `received_chunks/` - Downloaded chunks are saved here
- `reconstructed_download.txt` - The reconstructed file after download

---

## Usage

### 1. Localhost Testing (Single Machine)

#### Start the Tracker
```powershell
python tracker_server.py
```

#### Start a Seeder Peer
```powershell
python peer.py 127.0.0.1 --port 8001 --file dark_knight.txt
```

#### Start a Leecher Peer
```powershell
python peer.py 127.0.0.1 --port 8002
```

- You can start more peers on different ports for more complex tests.
- After download, the leecher will reconstruct the file as `reconstructed_download.txt`.

### 2. LAN/Network Testing (Multiple Machines)

#### Step 1: Find the Tracker Machine's IP
- On the tracker machine, run `ipconfig` (Windows) or `ifconfig` (Linux/Mac) and note the IPv4 address.

#### Step 2: Update `TRACKER_HOST`
- In both `peer.py` and `tracker_server.py`, set:
  ```python
  TRACKER_HOST = <ip>
  ```

#### Step 3: Start the Tracker
- On the tracker machine:
  ```powershell
  python tracker_server.py
  ```

#### Step 4: Start Peers on Any Machine
- Seeder:
  ```powershell
  python peer.py <seeder_ip> --port 8001 --file dark_knight.txt
  ```
- Leecher:
  ```powershell
  python peer.py <leecher_ip> --port 8002
  ```
- Replace `<seeder_ip>` and `<leecher_ip>` with the local IPs of each machine (use `ipconfig`/`ifconfig` to find them).
- You can use `--auto-public-ip` to auto-detect the peer's IP.

#### Step 5: Ensure Ports Are Open
- Make sure port 9090 (tracker) and the peer ports (e.g., 8001, 8002) are open on all machines (check firewall settings).

---

## File Reconstruction
- After all chunks are downloaded, the peer will automatically reconstruct the original file as `reconstructed_download.txt` in the project directory.
- You can compare this file to the original to verify integrity.

---

## Troubleshooting
- If you see port conflicts, use a different port for each peer.
- If peers cannot connect, check firewall settings and ensure all machines are on the same network.
- If the tracker is not reachable, double-check the `TRACKER_HOST` IP and port.

---

## Advanced
- You can run multiple seeders and leechers for swarm testing.
- The system is robust to peer restarts and tracker restarts (as long as ports are not reused immediately).
- For public IP testing, use `--auto-public-ip` and ensure your router/firewall allows incoming connections.

---

## License
See LICENSE file.


