"""Small fail-closed primitives shared by the offline and device workflows."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile


class ReviewRequired(RuntimeError):
    """Stop and preserve evidence; never infer that a failed write did nothing."""


def require(condition, message):
    if not condition:
        raise ReviewRequired(message)


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        before = os.fstat(source.fileno())
        remaining = before.st_size
        while remaining:
            block = source.read(min(4 * 1024 * 1024, remaining))
            require(block, f"File became shorter while hashing: {path}")
            h.update(block)
            remaining -= len(block)
        require(source.read(1) == b"", f"File grew while hashing: {path}")
        after = os.fstat(source.fileno())
        require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_size, after.st_mtime_ns, after.st_ctime_ns), f"File changed while hashing: {path}")
    return h.hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w") as target:
            json.dump(value, target, indent=2, sort_keys=True)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise ReviewRequired(f"Cannot read JSON {path}: {error}") from error


@contextmanager
def execution_lock():
    """One converter process per local user, across all run directories."""
    parent = Path.home() / ".cache" / "oppo-china-to-eu-changer"
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (parent / "execution.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ReviewRequired("Another converter process holds the execution lock") from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
