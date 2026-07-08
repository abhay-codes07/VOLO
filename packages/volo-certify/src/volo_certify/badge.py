"""Render a Volo Certified badge (SVG + Markdown) for a certificate (M33)."""

from __future__ import annotations

from volo_certify.certificate import Certificate

_PASS = "#12b886"
_FAIL = "#fa5252"


def render_badge_svg(cert: Certificate) -> str:
    """A self-contained shields-style SVG badge: 'Volo Certified | PASS 88'."""
    status = "certified" if cert.passed else "not certified"
    color = _PASS if cert.passed else _FAIL
    right = f"{status} · {cert.volo_score}"
    label, lw = "Volo Certified", 96
    rw = 8 * len(right) + 16
    total = lw + rw
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" '
        f'role="img" aria-label="Volo Certified: {status}">'
        f'<rect width="{lw}" height="20" fill="#0A0E14"/>'
        f'<rect x="{lw}" width="{rw}" height="20" fill="{color}"/>'
        f'<g fill="#fff" font-family="ui-monospace,Menlo,monospace" font-size="11">'
        f'<text x="8" y="14">{label}</text>'
        f'<text x="{lw + 8}" y="14">{right}</text>'
        f"</g></svg>"
    )


def render_badge_markdown(cert: Certificate, *, badge_url: str = "badge.svg") -> str:
    status = "PASS" if cert.passed else "FAIL"
    return (
        f"![Volo Certified]({badge_url}) "
        f"**Volo Certified: {status}** — score {cert.volo_score}, "
        f"reliability `{cert.reliability_verdict}`, safety `{cert.safety_verdict}`"
    )
