"""List and download files from the Minex SFTP server. Run locally:

    pip install paramiko
    python sftp_connect.py            # list the root directory
    python sftp_connect.py /path      # list a directory
    python sftp_connect.py /file get  # download a file to the current folder
"""
import getpass
import os
import stat
import sys

import paramiko

HOST = "node.minex.gg"
PORT = 2022
USER = "bencrickmore99.c41975ee"

password = os.environ.get("SFTP_PASSWORD") or getpass.getpass("SFTP password: ")
path = sys.argv[1] if len(sys.argv) > 1 else "."
download = len(sys.argv) > 2 and sys.argv[2] == "get"

transport = paramiko.Transport((HOST, PORT))
try:
    transport.connect(username=USER, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    if download:
        local = os.path.basename(path)
        sftp.get(path, local)
        print(f"Downloaded {path} -> {local}")
    else:
        for entry in sorted(sftp.listdir_attr(path), key=lambda e: e.filename):
            kind = "d" if stat.S_ISDIR(entry.st_mode) else "-"
            print(f"{kind} {entry.st_size:>12}  {entry.filename}")
finally:
    transport.close()
