import os
import pytest
import igsn_lib.flob

hash_tests = [
    [
        b"test 1",
        "f67213b122a5d442d2b93bda8cc45c564a70ec5d2a4e0e95bb585cf199869c98",
        None,
    ],
    [
        "Съешь же ещё этих мягких французских булок, да выпей чаю".encode("utf-8"),
        "87b68d66bbd8b19f3d73c1a0fb2966ad6adafdc8595f039a2fc2155ff9443816",
        None,
    ],
    [
        b"test 2",
        "dec2e4bc4992314a9c9a51bbd859e1b081b74178818c53c19d18d6f761f5d804",
        {"type": "text/plain", "fname": "test2.txt"},
    ],
]


@pytest.mark.parametrize("data,expected_hash,metadata", hash_tests)
def test_adding(data, expected_hash, metadata):
    test_folder = "/tmp/test_flob/"
    os.makedirs(test_folder, exist_ok=True)
    flobber = igsn_lib.flob.FLOB(test_folder)
    res = flobber.add(data, metadata=metadata)
    assert res[0] == f"{expected_hash[0]}/{expected_hash[1]}/{expected_hash[2]}"
    assert res[1] == expected_hash


def test_fakehash():
    test_folder = "/tmp/test_flob/"
    os.makedirs(test_folder, exist_ok=True)
    flobber = igsn_lib.flob.FLOB(test_folder)
    try:
        flobber.add(
            b"fake hash test",
            "87b68d66bbd8b19f3d73c1a0fb2966ad6adafdc8595f039a2fc2155ff94438XX",
        )
    except Exception as e:
        assert isinstance(e, ValueError)
        return
    raise Exception("failed")


def test_listing():
    test_folder = "/tmp/test_flob/"
    flobber = igsn_lib.flob.FLOB(test_folder)
    for f in flobber.listAllBlobs():
        print(f.name)
        failed = True
        for ht in hash_tests:
            if ht[1] in f.name:
                failed = False
                break
        assert not failed
