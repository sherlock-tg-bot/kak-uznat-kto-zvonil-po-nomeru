#!/usr/bin/env python3
"""Small, dependency-free content and HTML validation for this repository."""
from __future__ import annotations

import json
import re
import sys
import html as html_module
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["metadata.json", "README.md", "FAQ.md", "SECURITY.md", "index.html", ".github/workflows/validate.yml"]
CTA_LABEL = "Открыть в Telegram"
FORBIDDEN_URLS = ("sherlockbot.is", "glazboga.is", "t.me", "telegram.me")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1 = []
        self.links = []
        self._in_h1 = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self._in_h1 = True
        if tag == "a":
            self.links.append((attrs.get("href", ""), ""))

    def handle_data(self, data):
        if self._in_h1:
            self.h1.append(data)

    def handle_endtag(self, tag):
        if tag == "h1":
            self._in_h1 = False


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            fail(f"missing required file: {relative}", errors)
    if errors:
        print("\n".join(f"ERROR: {e}" for e in errors))
        return 1

    metadata = json.loads((ROOT / "metadata.json").read_text(encoding="utf-8"))
    keyword = metadata.get("keyword", "")
    target = metadata.get("target_url", "")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    faq = (ROOT / "FAQ.md").read_text(encoding="utf-8")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    html_normalized = html_module.unescape(html)
    workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")

    if keyword.casefold() not in readme.casefold() or keyword.casefold() not in faq.casefold() or keyword.casefold() not in html.casefold():
        fail("keyword is missing from README, FAQ, or index.html", errors)
    if not readme[:1400].find(target) >= 0:
        fail("target_url must occur near the beginning of README.md", errors)
    if target not in readme[readme.rfind("## Итог"):]:
        fail("target_url must occur in the final README block", errors)
    if target not in html_normalized or CTA_LABEL not in html:
        fail("index.html must contain target_url and the CTA label", errors)
    for name, content in (("README.md", readme), ("FAQ.md", faq), ("SECURITY.md", security), ("index.html", html_normalized)):
        for forbidden in FORBIDDEN_URLS:
            if forbidden in content and target not in content:
                fail(f"forbidden direct URL in {name}: {forbidden}", errors)
    if readme.count("![") > 1 or "actions/workflows/validate.yml/badge.svg" not in readme:
        fail("README must contain only the workflow badge", errors)
    if "python3 scripts/validate.py" not in workflow or "Content validation" not in workflow:
        fail("workflow must be named Content validation and run the validator", errors)
    parser = PageParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        fail(f"index.html is not parseable: {exc}", errors)
    if keyword.casefold() not in "".join(parser.h1).casefold() or len(parser.h1) == 0:
        fail("index.html h1 must contain the exact keyword", errors)
    if re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']https://(go\.|www\.)?sherlockbot', html, re.I):
        fail("canonical must not point to CTA/service domain", errors)
    if "analytics" in html.lower() or "metrika" in html.lower():
        fail("analytics code or text is not allowed", errors)
    if errors:
        print("\n".join(f"ERROR: {e}" for e in errors))
        return 1
    print("OK: content, CTA, workflow, and HTML checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
