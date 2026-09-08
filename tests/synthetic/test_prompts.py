import pytest

from synthetic.prompts import PROMPT_DIR, PROMPT_FILENAMES, load_prompt
from synthetic.taxonomy import ModificationType


_EXPECTED_PLACEHOLDERS: dict[ModificationType, set[str]] = {
    ModificationType.SYNONYM_LABEL:    {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.NUM_TO_TEXT:      {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.UNIT_CONVERSION:  {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.UNIT_EXPANSION:   {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.ABBREV_EXPANSION: {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.CODE_EXPANSION:   {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.PARAPHRASE:       {"{concept}", "{var_key}", "{fragment}", "{condition}", "{sibling_fragments}"},
    ModificationType.EXPANSION:        {"{concept}", "{var_key}", "{fragment}", "{condition}", "{sibling_fragments}"},
    ModificationType.COMPRESSION:      {"{concept}", "{var_key}", "{fragment}", "{condition}", "{sibling_fragments}"},
    ModificationType.OMISSION:         {"{concept}", "{template}", "{var_to_omit}", "{axis_label}"},
    ModificationType.REORDER:          {"{concept}", "{template}", "{constituents}"},
    ModificationType.TEMPLATE_PARAPHRASE: {"{concept}", "{field}", "{template}", "{placeholders}"},
    ModificationType.NEW_PARAM:        {"{concept}", "{existing_axes_with_labels}", "{allowlist}"},
}


_L1_TYPES = (
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
)

_L2_TYPES = (
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
)

_ALL_TYPES = tuple(ModificationType)


def test_prompt_dir_exists():
    assert PROMPT_DIR.is_dir()


def test_prompt_filenames_size_and_keys():
    # Sprint 36: TEMPLATE_PARAPHRASE brought the count to 13.
    assert len(PROMPT_FILENAMES) == 13
    assert set(PROMPT_FILENAMES) == set(ModificationType)
    for mtype, fname in PROMPT_FILENAMES.items():
        assert fname == f"{mtype.value}.txt"


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_every_prompt_file_exists(mtype):
    fname = PROMPT_FILENAMES[mtype]
    assert (PROMPT_DIR / fname).is_file()


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_load_prompt_returns_str_per_type(mtype):
    text = load_prompt(mtype)
    assert isinstance(text, str)
    assert len(text) > 0
    assert text.endswith("\n")


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_load_prompt_utf8_decode_per_type(mtype):
    fname = PROMPT_FILENAMES[mtype]
    raw = (PROMPT_DIR / fname).read_bytes()
    decoded = raw.decode("utf-8")
    assert decoded == load_prompt(mtype)


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_load_prompt_no_bom_per_type(mtype):
    fname = PROMPT_FILENAMES[mtype]
    raw = (PROMPT_DIR / fname).read_bytes()
    assert raw[0:1] != b"\xef", f"{mtype.value} starts with UTF-8 BOM byte 0xEF"
    assert not raw.startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_load_prompt_declares_json_contract_per_type(mtype):
    text = load_prompt(mtype)
    assert "JSON" in text.upper()


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_load_prompt_placeholders_per_type(mtype):
    text = load_prompt(mtype)
    expected = _EXPECTED_PLACEHOLDERS[mtype]
    missing = {slot for slot in expected if slot not in text}
    assert not missing, f"{mtype.value} missing placeholders: {missing}"


def test_load_prompt_idempotent():
    a = load_prompt(ModificationType.SYNONYM_LABEL)
    b = load_prompt(ModificationType.SYNONYM_LABEL)
    assert a == b


def test_load_prompt_raises_keyerror_on_string_input():
    with pytest.raises(KeyError):
        load_prompt("synonym_label")


def test_load_prompt_raises_filenotfound_on_missing_file(monkeypatch):
    monkeypatch.setitem(
        PROMPT_FILENAMES,
        ModificationType.SYNONYM_LABEL,
        "NOTAFILE.txt",
    )
    with pytest.raises(FileNotFoundError):
        load_prompt(ModificationType.SYNONYM_LABEL)


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_prompt_starts_with_role_line(mtype):
    text = load_prompt(mtype)
    first_nonempty = next((line for line in text.splitlines() if line.strip()), "")
    assert first_nonempty.startswith("Eres "), (
        f"{mtype.value} first non-empty line: {first_nonempty!r}"
    )


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_prompt_uses_spanish_register(mtype):
    text = load_prompt(mtype)
    markers = {"Eres", "Concepto", "Responde", "JSON"}
    assert markers & set(text.split()), f"{mtype.value} lacks Spanish-register markers"


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_prompt_contains_responder_solo_phrase_per_type(mtype):
    text = load_prompt(mtype)
    assert "Responde SOLO con un JSON" in text


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_prompt_no_unrendered_python_braces_outside_slots(mtype):
    # `new_param.txt`'s JSON literal embeds nested `{` / `}` that the
    # prefix-vs-JSON-block heuristic can't cleanly partition; exempted
    # per Sprint 12 §Task 3 case 15.
    if mtype == ModificationType.NEW_PARAM:
        pytest.skip("new_param.txt nested-JSON braces exempted by spec")
    text = load_prompt(mtype)
    marker = "Responde SOLO con un JSON"
    idx = text.find(marker)
    assert idx >= 0, f"{mtype.value} missing '{marker}' marker"
    body = text[:idx]
    expected = _EXPECTED_PLACEHOLDERS[mtype]
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "{":
            end = body.find("}", i)
            assert end > i, f"{mtype.value} unmatched '{{' at offset {i} in body"
            slot = body[i:end + 1]
            assert slot in expected, (
                f"{mtype.value} unexpected brace token {slot!r} in body "
                f"(not in declared placeholders {expected})"
            )
            i = end + 1
        elif ch == "}":
            raise AssertionError(
                f"{mtype.value} stray '}}' in body at offset {i}"
            )
        else:
            i += 1


def test_prompt_l1_six_types_share_placeholder_set():
    canonical = {"{concept}", "{axis_label}", "{value_list}"}
    for mtype in _L1_TYPES:
        assert _EXPECTED_PLACEHOLDERS[mtype] == canonical, mtype
        text = load_prompt(mtype)
        for slot in canonical:
            assert slot in text, f"{mtype.value} missing {slot}"


# Sprint 32 pin — F1_findings §5 + F2b phi4 baseline showed 33 % of L1
# outputs were meta-referential paragraphs echoing the whole item
# description. The tuned L1 prompts must carry a short-label instruction
# that (a) caps the answer length and (b) forbids restating the concept.
_L1_SHORT_LABEL_MARKER = "etiqueta corta"
_L1_NO_DESCRIPTION_MARKER = "No copies frases del campo Concepto"


@pytest.mark.parametrize("mtype", _L1_TYPES)
def test_l1_prompt_carries_short_label_instruction(mtype):
    text = load_prompt(mtype)
    assert _L1_SHORT_LABEL_MARKER in text, (
        f"{mtype.value} missing short-label instruction "
        f"({_L1_SHORT_LABEL_MARKER!r})"
    )
    assert _L1_NO_DESCRIPTION_MARKER in text, (
        f"{mtype.value} missing no-description instruction "
        f"({_L1_NO_DESCRIPTION_MARKER!r})"
    )


# Sprint 33 pin — F2c-L2. phi4's L2 compression exhibited the same
# meta-referential failure L1 did before Sprint 32: 7/15 compression
# outputs were the whole item description. The three L2 prompts must
# now carry (a) the shared anti-echo instruction, and (b) a per-type
# length constraint so the length target is unambiguous.
_L2_NO_ECHO_MARKER = "No copies frases del campo Concepto"
_L2_PER_TYPE_MARKERS: dict[ModificationType, str] = {
    ModificationType.COMPRESSION: "estrictamente más corto",
    ModificationType.PARAPHRASE: "misma longitud aproximada",
    ModificationType.EXPANSION: "centrado en el fragmento",
}


@pytest.mark.parametrize("mtype", _L2_TYPES)
def test_l2_prompt_carries_no_concept_echo_instruction(mtype):
    text = load_prompt(mtype)
    assert _L2_NO_ECHO_MARKER in text, (
        f"{mtype.value} missing anti-echo instruction "
        f"({_L2_NO_ECHO_MARKER!r})"
    )


@pytest.mark.parametrize("mtype", _L2_TYPES)
def test_l2_prompt_carries_per_type_length_constraint(mtype):
    marker = _L2_PER_TYPE_MARKERS[mtype]
    text = load_prompt(mtype)
    assert marker in text, (
        f"{mtype.value} missing per-type length marker ({marker!r})"
    )


# Sprint 34 pin — F2c-L2 review flagged phi4's `Nocturno Excepcional →
# Nocturno` collision (Nocturno already exists as sibling %B=b). L1 prompts
# already show the model every sibling value in `{value_list}`; adding an
# explicit no-collision instruction is enough to reduce the rate. The
# post-generation collision guard (Sprint 34, layer_l1/l2) is the
# belt-and-suspenders that catches whatever the prompt misses.
_L1_NO_COLLISION_MARKER = "no crees colisiones"


@pytest.mark.parametrize("mtype", _L1_TYPES)
def test_l1_prompt_carries_no_collision_instruction(mtype):
    text = load_prompt(mtype)
    assert _L1_NO_COLLISION_MARKER in text, (
        f"{mtype.value} missing no-collision instruction "
        f"({_L1_NO_COLLISION_MARKER!r})"
    )


# Sprint 34 pin — L2 prompts now receive `{sibling_fragments}` (the other
# clauses of the same text-variable). The anti-collision instruction tells
# the model to avoid producing a fragment identical to any sibling.
_L2_NO_COLLISION_MARKER = "no crees colisiones"


@pytest.mark.parametrize("mtype", _L2_TYPES)
def test_l2_prompt_declares_sibling_fragments_slot(mtype):
    text = load_prompt(mtype)
    assert "{sibling_fragments}" in text, (
        f"{mtype.value} missing {{sibling_fragments}} placeholder"
    )


@pytest.mark.parametrize("mtype", _L2_TYPES)
def test_l2_prompt_carries_no_collision_instruction(mtype):
    text = load_prompt(mtype)
    assert _L2_NO_COLLISION_MARKER in text, (
        f"{mtype.value} missing no-collision instruction "
        f"({_L2_NO_COLLISION_MARKER!r})"
    )


def test_prompt_l2_three_types_share_placeholder_set():
    # Sprint 34: {sibling_fragments} added to every L2 prompt so the model
    # can enforce no-collision against the other clauses of the same var.
    canonical = {"{concept}", "{var_key}", "{fragment}", "{condition}", "{sibling_fragments}"}
    for mtype in _L2_TYPES:
        assert _EXPECTED_PLACEHOLDERS[mtype] == canonical, mtype
        text = load_prompt(mtype)
        for slot in canonical:
            assert slot in text, f"{mtype.value} missing {slot}"


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_prompt_byte_sizes_within_bounds(mtype):
    fname = PROMPT_FILENAMES[mtype]
    size = (PROMPT_DIR / fname).stat().st_size
    assert 200 <= size <= 3000, f"{mtype.value} size={size} bytes outside [200, 3000]"
