"""Sprint 38.6-B — hermetic tests for :mod:`synthetic.template_masking`."""
from __future__ import annotations

import pytest

from synthetic.template_masking import check_sentinels, mask_invariants, unmask


_TEMPLATE = (
    "Ejecución de canalización para línea subterránea de doble circuito de "
    "220 ó 400 kV en terreno $A, $B de pavimento, con hormigón HM-20, de "
    "2 m de ancho por 1,60 m de alto, hormigonado a 760 mm, compactado al "
    "95% P.M., 2 ternas de tubos de 250 mm, tetratubos de 4x40 mm. "
    "($L(%C)/$M(%D))"
)


def test_roundtrip_is_identity():
    masked, mapping = mask_invariants(_TEMPLATE)
    assert unmask(masked, mapping) == _TEMPLATE


def test_masked_text_has_no_placeholders_digits_or_units():
    masked, _ = mask_invariants(_TEMPLATE)
    assert "$" not in masked
    # every digit left in the text belongs to a sentinel id [[P3]]/[[Q12]]
    import re
    stripped = re.sub(r"\[\[[PQ]\d+\]\]", "", masked)
    assert not re.search(r"\d", stripped)
    assert " mm" not in stripped and " kV" not in stripped


def test_placeholders_and_quantities_get_distinct_prefixes():
    masked, mapping = mask_invariants("$A de 250 mm ($L(%C))")
    p = [k for k in mapping if k.startswith("P")]
    q = [k for k in mapping if k.startswith("Q")]
    assert len(p) == 2 and len(q) == 1
    assert mapping[q[0]] == "250 mm"


def test_attached_unit_masked_with_its_number():
    masked, mapping = mask_invariants("zanja de 2 m de ancho y 5 At. de presión")
    values = set(mapping.values())
    assert "2 m" in values and "5 At." in values


def test_bare_number_masked_alone():
    _, mapping = mask_invariants("2 ternas de conductos")
    assert "2" in set(mapping.values())
    assert not any("ternas" in v for v in mapping.values())


def test_codes_masked_whole():
    _, mapping = mask_invariants("hormigón HM-20 y tetratubo de 4x40 mm")
    values = set(mapping.values())
    assert "HM-20" in values and "4x40 mm" in values


def test_check_sentinels_passes_on_faithful_text():
    masked, mapping = mask_invariants(_TEMPLATE)
    check_sentinels(masked, mapping)  # no raise


def test_check_sentinels_rejects_dropped_and_duplicated():
    masked, mapping = mask_invariants("$A de 250 mm")
    some = next(iter(mapping))
    with pytest.raises(ValueError, match="sentinels_not_preserved"):
        check_sentinels(masked.replace(f"[[{some}]]", "", 1), mapping)
    with pytest.raises(ValueError, match="sentinels_not_preserved"):
        check_sentinels(masked + f" [[{some}]]", mapping)


def test_check_sentinels_rejects_unknown_sentinel():
    masked, mapping = mask_invariants("$A de 250 mm")
    with pytest.raises(ValueError, match="sentinels_not_preserved"):
        check_sentinels(masked + " [[Q99]]", mapping)
