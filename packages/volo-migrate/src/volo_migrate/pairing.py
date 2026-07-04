"""Pair recordings across a baseline (model A) and candidate (model B) corpus (newplan M16).

Re-recording a corpus under a new model keeps the file names, so pairing is by **stem**: two
single files pair directly; two directories pair ``a/foo.json`` ↔ ``b/foo.json``. Stems present
on only one side are reported as ``unpaired`` — never silently dropped.
"""

from __future__ import annotations

from pathlib import Path

from volo_core import Recording


def _load(path: Path) -> Recording:
    return Recording.from_json(path.read_text(encoding="utf-8"))


def _index(target: Path) -> dict[str, Path]:
    if target.is_dir():
        return {p.stem: p for p in sorted(target.glob("*.json")) if p.name != "index.json"}
    return {target.stem: target}


def pair_corpora(
    baseline: Path | str,
    candidate: Path | str,
) -> tuple[list[tuple[str, Recording, Recording]], list[str]]:
    """Return ``(pairs, unpaired_stems)`` for two files or two directories.

    ``pairs`` is ``[(stem, baseline_recording, candidate_recording), ...]`` in stem order.
    """
    a_path_in, b_path_in = Path(baseline), Path(candidate)
    a_index = _index(a_path_in)
    b_index = _index(b_path_in)

    # Two explicit *files* with different stems still pair — align them positionally. Single-file
    # *directories* fall through to stem matching (so disjoint stems are reported unpaired).
    if a_path_in.is_file() and b_path_in.is_file():
        (a_stem, a_path), (b_stem, b_path) = (
            next(iter(a_index.items())),
            next(iter(b_index.items())),
        )
        key = a_stem if a_stem == b_stem else f"{a_stem}->{b_stem}"
        return [(key, _load(a_path), _load(b_path))], []

    pairs: list[tuple[str, Recording, Recording]] = []
    for stem in sorted(set(a_index) & set(b_index)):
        pairs.append((stem, _load(a_index[stem]), _load(b_index[stem])))
    unpaired = sorted(set(a_index) ^ set(b_index))
    return pairs, unpaired
