from __future__ import annotations

import pytest

from bc3param.param.codes import derived_code, index_to_letter, letter_to_index, split_derived_code


def test_letter_index_roundtrip():
    assert letter_to_index("a") == 1
    assert letter_to_index("z") == 26
    assert letter_to_index("A") == 27
    assert letter_to_index("0") == 53
    assert letter_to_index("9") == 62
    for i in range(1, 63):
        assert letter_to_index(index_to_letter(i)) == i


def test_invalid_letter_and_index():
    with pytest.raises(ValueError):
        letter_to_index("$")
    with pytest.raises(ValueError):
        index_to_letter(0)
    with pytest.raises(ValueError):
        index_to_letter(63)


def test_derived_code():
    assert derived_code("OEB020$", (2, 2, 2, 1, 1)) == "OEB020bbbaa"


def test_split_derived_code():
    families = {"OEB020$", "OEB0203$"}
    assert split_derived_code("OEB020bbbaa", families) == ("OEB020$", (2, 2, 2, 1, 1))
    assert split_derived_code("OEB0203ab", families) == ("OEB0203$", (1, 2))
    with pytest.raises(ValueError):
        split_derived_code("XXX", families)
