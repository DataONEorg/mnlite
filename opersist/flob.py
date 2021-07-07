"""
flob is a blob writer to a file system hierarchy.

A sha256 hash of the blob is created and stored in a folder
three levels down, with folders named by the first three
characters of the sha256 hash hex digest.

Each blob may have metadata stored under the same name but
with the extension ".json". Any valid json-serializable
informaiton may be included in the metadata.
"""

import os
import logging
import hashlib
import tempfile
import pathlib
import shutil
import re

try:
    import orjson as json
except ModuleNotFoundError:
    import json


class FLOB(object):

    L = logging.getLogger("FLOB")
    EXTENSION = "bin"
    BLOCK_SIZE = 65536
    SHA256_REGEX = re.compile(r"^[a-f0-9]{64}(:.+)?$", re.IGNORECASE)

    def __init__(self, root_path: str = "."):
        self.root_path = os.path.abspath(root_path)
        os.makedirs(self.root_path, exist_ok=True)

    def close(self):
        pass

    def pathFromHash(self, hash: str):
        hash = hash.strip().lower()
        if not self.SHA256_REGEX.match(hash):
            raise ValueError("String '%s' is not a valid SHA256 hash", hash)
        fldr = os.path.join(hash[0], hash[1], hash[2])
        return fldr

    def remove(self, hash: str):
        removed = 0
        fldr = self.pathFromHash(hash)
        abs_fldr = os.path.join(self.root_path, fldr)
        f_base = os.path.join(abs_fldr, hash)
        f_name = f"{f_base}.{self.EXTENSION}"
        if os.path.exists(f_name):
            os.unlink(f_name)
            removed = 1
        f_meta = f"{f_base}.json"
        if os.path.exists(f_meta):
            os.unlink(f_meta)
            removed = removed + 2
        return removed

    def add(
        self, b: bytes, hash: str = None, metadata: dict = None, allow_replace=False
    ):
        """
        Add a blob file to the stash.

        Raises an error if the blob already exists and allow_replace is False

        Args:
            b: bytes
            hash: pre-computed SHA256 hash or None
            metadata: optional dict to be written as json
            allow_replace: OK to replace existing hash, otherwise raise ValueError

        Returns:
            fldr_dest, sha256, path_to_file
        """
        if hash is None:
            sha = hashlib.sha256()
            sha.update(b)
            hash = sha.hexdigest()
        else:
            hash = hash.strip().lower()
        fldr_dest = self.pathFromHash(hash)
        abs_fldr = os.path.join(self.root_path, fldr_dest)
        os.makedirs(abs_fldr, exist_ok=True)
        f_base = os.path.join(abs_fldr, hash)
        f_dest = f"{f_base}.{self.EXTENSION}"
        if os.path.exists(f_dest) and not allow_replace:
            raise ValueError("Entry already exists: %s", hash)
        with open(f_dest, "wb") as fout:
            fout.write(b)
        if not metadata is None:
            with open(f"{f_base}.json", "w") as fout:
                json.dump(metadata, fout, indent=2)
        self.L.debug("wrote %s bytes to %s", len(b), f_dest)
        return fldr_dest, hash, os.path.join(fldr_dest, f"{hash}.{self.EXTENSION}")

    def addFile(self, fh, hash: str = None, metadata: dict = None, allow_replace=False):
        """
        Adds the file stream to the stash as a blob.

        Args:
            fh: file open for read
            metadata: Optional dictionary of metadata
            allow_replace: If True, then ok to replace existing file

        Returns:
            fldr_dest, sha256, path_to_file
        """
        sha = hashlib.sha256()
        nbytes = 0
        tmpfile_name = None
        with tempfile.NamedTemporaryFile(delete=False) as tmp_dest:
            tmpfile_name = tmp_dest.name
            fbuf = fh.read(self.BLOCK_SIZE)
            while len(fbuf) > 0:
                if hash is None:
                    sha.update(fbuf)
                tmp_dest.write(fbuf)
                nbytes += len(fbuf)
                fbuf = fh.read(self.BLOCK_SIZE)
        if nbytes <= 0:
            raise ValueError("No content in provided file hande")
        if hash is None:
            hash = sha.hexdigest()
        fldr_dest = self.pathFromHash(hash)
        abs_fldr = os.path.join(self.root_path, fldr_dest)
        os.makedirs(abs_fldr, exist_ok=True)
        f_base = os.path.join(abs_fldr, hash)
        f_dest = f"{f_base}.{self.EXTENSION}"
        if os.path.exists(f_dest) and not allow_replace:
            os.unlink(tmpfile_name)
            raise ValueError("Entry already exists: %s", hash)
        shutil.move(tmpfile_name, f_dest)
        if not metadata is None:
            with open(f"{f_base}.json", "w") as fout:
                json.dump(metadata, fout, indent=2)
        self.L.debug("wrote %s bytes to %s", nbytes, f_dest)
        return fldr_dest, hash, os.path.join(fldr_dest, f"{hash}.{self.EXTENSION}")

    def addFilePath(
        self, fname, hash: str = None, metadata: dict = None, allow_replace=False
    ):
        if metadata is None:
            metadata = {}
        metadata.setdefault("original_path", fname)
        with open(fname, "rb") as f_src:
            return self.addFile(
                f_src, hash=hash, metadata=metadata, allow_replace=allow_replace
            )

    def listAllBlobs(self):
        _path = pathlib.Path(self.root_path)
        for entry in _path.glob("**/*.bin"):
            if not entry.is_dir():
                yield entry
