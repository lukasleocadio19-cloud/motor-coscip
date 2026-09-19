from __future__ import annotations

import hashlib
import io

import pytest

from coscip_storage import LocalFileStorage, PathOutsideRootError


def test_write_is_atomic_and_hashed(tmp_path):
    st = LocalFileStorage(tmp_path)
    data = b"x" * 3_000_000
    obj = st.write_stream("projects/p1/originals/r1/a.dxf", io.BytesIO(data))
    assert obj.sha256 == hashlib.sha256(data).hexdigest()
    assert obj.size == len(data)
    assert st.sha256_of(obj.key) == obj.sha256
    assert not st.find_orphan_temps()


def test_originals_are_immutable(tmp_path):
    st = LocalFileStorage(tmp_path)
    st.write_stream("a/b.bin", [b"1"])
    with pytest.raises(FileExistsError):
        st.write_stream("a/b.bin", [b"2"])


@pytest.mark.parametrize("key", ["../fora.txt", "a/../../fora", "/abs", "C:/win", "\\\\srv\\x", ""])
def test_traversal_and_absolute_rejected(tmp_path, key):
    with pytest.raises(PathOutsideRootError):
        LocalFileStorage(tmp_path / "root").resolve(key)


def test_failed_write_leaves_no_partial(tmp_path):
    st = LocalFileStorage(tmp_path)

    def boom():
        yield b"abc"
        raise OSError("disco cheio")

    with pytest.raises(OSError):
        st.write_stream("x/y.bin", boom())
    assert not (tmp_path / "x" / "y.bin").exists()
    assert not st.find_orphan_temps()
