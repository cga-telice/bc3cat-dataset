"""P7 (bc3cat-retrieval REORDER_LOOKUP_ARGUMENTS.md): a placeholder is the whole
call, argument order included.

`$T(%A,%B,%C)` is a lookup into a table indexed by (A, B, C). The old
placeholder regex matched at most one argument, so `$T(%A,%B,%C)` reduced to
`$T` and a reorder to `$T(%C,%A,%B)` passed — rendering a sibling leaf's TEXTO
under the gold's parameters. All hermetic.
"""

import pytest

from synthetic.taxonomy import ModificationType
from synthetic.variant_proposer import _placeholders, _validate_payload


def _payload(original, new):
    return {"original": original, "new": new, "preserves_meaning": True}


@pytest.mark.parametrize("new", [
    "$T(%C,%A,%B)",      # the approved OEC140$ rule
    "$T(%B,%C,%A)",
    "$T(%B,%A,%C)",
    "$T(%C, %B, %A)",
])
@pytest.mark.parametrize("mtype", [ModificationType.REORDER, ModificationType.TEMPLATE_PARAPHRASE])
def test_permuted_lookup_arguments_rejected(new, mtype):
    with pytest.raises(ValueError, match="placeholders_not_preserved"):
        _validate_payload(_payload("$T(%A,%B,%C)", new), mtype)


def test_permuted_literal_lookup_argument_rejected():
    # `$L(b,%C)` selects row b: swapping it for row c changes the referent.
    original = "anclaje $T(%A). $L(b,%C). Trabajo: $L(c,%C)."
    new = "anclaje $T(%A). $L(c,%C). Trabajo: $L(b,%C)."
    assert _placeholders(original) == _placeholders(new)  # same multiset of calls: allowed
    new_bad = "anclaje $T(%A). $L(%C,b). Trabajo: $L(c,%C)."
    with pytest.raises(ValueError, match="placeholders_not_preserved"):
        _validate_payload(_payload(original, new_bad), ModificationType.REORDER)


def test_moving_a_multi_argument_call_is_still_a_valid_reorder():
    original = "Reparación $T(%A,%B,%C) de cámara $B"
    new = "Reparación de cámara $B, $T(%A, %B, %C)"   # whitespace inside the call is not meaning
    assert _validate_payload(_payload(original, new), ModificationType.REORDER) is not None


def test_placeholder_is_the_whole_call():
    assert _placeholders("x $T(%A,%B,%C) y $L(b,%C) z $A") == {"$T(%A,%B,%C)", "$L(b,%C)", "$A"}
