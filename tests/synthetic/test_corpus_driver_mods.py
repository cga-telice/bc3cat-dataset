"""_per_rewrite_modifications — counts APPLIED modifications only."""
from __future__ import annotations

from synthetic.corpus_driver import _per_rewrite_modifications
from synthetic.pantry import ApprovedRewrite
from synthetic.taxonomy import Modification, ModificationType, TYPE_TO_LAYER

TP = ModificationType.TEMPLATE_PARAPHRASE
PA = ModificationType.PARAPHRASE


def _rw(t):
    return ApprovedRewrite(mtype=t, dedup_key=("k",), canonical="c",
                           candidate_index=0, payload={"original": "a", "new": "b"},
                           usages=())


def _mod(t, status="applied"):
    return Modification(type=t, layer=TYPE_TO_LAYER[t], status=status)


def test_rewrite_without_applied_record_is_not_counted():
    # a paraphrase rewrite the sampler planned but that failed to splice
    # (list-form var) contributes no applied record -> excluded, not counted.
    out = _per_rewrite_modifications((_rw(TP), _rw(PA)), (_mod(TP),))
    assert tuple(m.type for m in out) == (TP,)
    assert len(out) == 1  # modification_count == applied count


def test_one_applied_record_per_rewrite():
    out = _per_rewrite_modifications((_rw(TP), _rw(TP)), (_mod(TP), _mod(TP)))
    assert len(out) == 2


def test_non_applied_materialized_records_are_ignored():
    out = _per_rewrite_modifications((_rw(TP),), (_mod(TP, status="skipped"),))
    assert out == ()
