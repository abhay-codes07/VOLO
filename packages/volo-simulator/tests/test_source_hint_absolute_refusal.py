"""ADR-0012: under the untrusted policy, an absolute source-hint path is refused.

The existing suite covers `..` traversal and missing base_dir, but not the `is_absolute()` guard —
deleting it would keep the suite green while weakening the untrusted-recording trust boundary.
"""

from __future__ import annotations

from pathlib import Path

from volo_simulator.tier2 import SourceInformedSynthesizer


def test_untrusted_absolute_path_inside_base_dir_is_refused(tmp_path: Path) -> None:
    absolute_inside = str((tmp_path / "spec.json").resolve())  # absolute, and *inside* base_dir
    untrusted = SourceInformedSynthesizer(trust_source_hints=False, base_dir=tmp_path)
    # refused purely because it is absolute — even though it resolves within base_dir
    assert untrusted._resolve_file_hint(absolute_inside) is None
    assert untrusted._resolve_file_hint("file://" + absolute_inside) is None


def test_untrusted_relative_path_inside_base_dir_is_allowed(tmp_path: Path) -> None:
    untrusted = SourceInformedSynthesizer(trust_source_hints=False, base_dir=tmp_path)
    resolved = untrusted._resolve_file_hint("spec.json")  # relative + confined -> allowed
    assert resolved is not None and resolved == (tmp_path.resolve() / "spec.json")


def test_trusted_policy_allows_absolute(tmp_path: Path) -> None:
    absolute_inside = str((tmp_path / "spec.json").resolve())
    trusted = SourceInformedSynthesizer(trust_source_hints=True, base_dir=tmp_path)
    assert trusted._resolve_file_hint(absolute_inside) == Path(absolute_inside)
