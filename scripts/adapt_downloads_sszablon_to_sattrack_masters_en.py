#!/usr/bin/env python3
"""
Adapt the WiR sample ``SszablonPracyInzMgr.docx`` into an English Master's thesis **template**
for the SATTRACK project.

The template is read from the repository root (``SszablonPracyInzMgr.docx``) if present;
otherwise from ``~/Downloads/SszablonPracyInzMgr.docx``. The modified file is **always saved**
under ``docs/SszablonPracyInzMgr_SATTRACK_masters_EN.docx`` in this project folder.

Rules:
* Keeps the first body block unchanged structurally: title paragraphs (0–10), TOC ``w:sdt``
  (11), spacer paragraph (12) — only **replaces visible text** inside those nodes where needed.
* Removes sample thesis content from body index 13 through the element before ``w:sectPr``
  (tables, paragraphs, etc.) without altering styles in ``styles.xml``.
* Appends new English guidance sections using the **same** paragraph styles as the rest of
  the template (Heading 1–3, Normal, Akapitzlist, Streszczenie, …).

Creates a one-time backup next to the target file before overwriting.

Usage::
    python scripts/adapt_downloads_sszablon_to_sattrack_masters_en.py

Requires: pip install python-docx
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from docx import Document
except ImportError:
    print("Install: pip install python-docx", file=sys.stderr)
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUTPUT = DOCS / "SszablonPracyInzMgr_SATTRACK_masters_EN.docx"
OUTPUT_PREVIOUS = DOCS / "SszablonPracyInzMgr_SATTRACK_masters_EN_previous.docx"

_SOURCE_CANDIDATES = (
    ROOT / "SszablonPracyInzMgr.docx",
    Path.home() / "Downloads" / "SszablonPracyInzMgr.docx",
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
TITLE_PARA_COUNT = 11
TOC_SDT_INDEX = 11
AFTER_TOC_SPACER_INDEX = 12
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

TOC_ENTRIES = [
    ("1. Introduction", "Introduction", "Spistreci1"),
    ("1.1 Aim of the Thesis", "Aim of the Thesis", "Spistreci2"),
    ("1.2 Scope of the Thesis", "Scope of the Thesis", "Spistreci2"),
    (
        "1.3 Research Questions and Hypotheses",
        "Research Questions and Hypotheses",
        "Spistreci2",
    ),
    ("2. Materials and Methods", "Materials and Methods", "Spistreci1"),
    ("2.1 SATTRACK Application Description", "SATTRACK Application Description", "Spistreci2"),
    ("3. Research and Analysis", "Research and Analysis", "Spistreci1"),
    ("4. Results", "Results", "Spistreci1"),
    ("5. Discussion", "Discussion", "Spistreci1"),
    ("6. Conclusions", "Conclusions", "Spistreci1"),
    ("7. References", "References", "Spistreci1"),
]


def _merge_paragraph_text_to_first_wt(p_el, new_text: str) -> None:
    """Set paragraph visible text; clear other ``w:t`` nodes (preserves runs / breaks)."""
    texts = p_el.findall(f".//{W}t")
    if not texts:
        return
    texts[0].text = new_text
    for t in texts[1:]:
        t.text = ""


def _patch_toc_sdt_title(sdt_el) -> None:
    for t in sdt_el.findall(f".//{W}t"):
        if t.text and "Spis treści" in t.text:
            t.text = t.text.replace("Spis treści", "Table of contents")


def _apply_english_title_page(body) -> None:
    lines = [
        "AGH University of Science and Technology",
        "Faculty of Space Technologies",
        "",
        "",
        "MASTER'S THESIS",
        "Thesis topic: Satellite Trajectory Prediction and Weather-Aware Observation Planning System (SATTRACK)",
        "[The title page must comply with the current requirements of the Dean's Office. Replace all bracketed placeholders.]",
        "Field of study: [official programme name]",
        "Supervisor: [title, first name, surname]",
        "Kraków, [year]",
    ]
    for i, line in enumerate(lines):
        p = body[i]
        if not p.tag.endswith("p"):
            continue
        if i == TITLE_PARA_COUNT - 1:
            # Page-break paragraph: keep layout; only clear stray text if any.
            _merge_paragraph_text_to_first_wt(p, "")
            continue
        _merge_paragraph_text_to_first_wt(p, line)


def _strip_body_from_index(body, start_index: int) -> None:
    """Remove all body children from ``start_index`` up to (but not including) ``sectPr``."""
    children = list(body)
    sect = children[-1]
    if not sect.tag.endswith("sectPr"):
        raise RuntimeError("Last body child is not w:sectPr.")
    for ch in children[start_index:-1]:
        body.remove(ch)


def _note(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic = True


def _p(doc: Document, text: str, *, style: str | None = None) -> None:
    if style:
        doc.add_paragraph(text, style=style)
    else:
        doc.add_paragraph(text)


def _h1(doc: Document, text: str) -> None:
    doc.add_heading(text, level=1)


def _h2(doc: Document, text: str) -> None:
    doc.add_heading(text, level=2)


def _bullet(doc: Document, items: list[str]) -> None:
    for t in items:
        doc.add_paragraph(t, style="Akapitzlist")


def _ref(doc: Document, text: str) -> None:
    doc.add_paragraph(text, style="literatura numerowana")


def _append_sattrack_template_body(doc: Document) -> None:
    """English guidance matching the required chapter structure (SATTRACK)."""
    _p(doc, "Abstract", style="Streszczenie")
    _note(
        doc,
        "[150–300 words. Summarise the problem (satellite trajectory prediction, weather-aware observation planning), "
        "the SATTRACK system, methods, key quantitative outcomes, and conclusions. No citations; define acronyms on first use.]",
    )
    _p(
        doc,
        "[Write the abstract here as a continuous narrative. Motivate Earth observation and pass prediction, state the role "
        "of SATTRACK, describe the evaluation methodology (e.g., case study, benchmarks, user tasks), and end with the "
        "main empirical takeaway.]",
    )
    doc.add_paragraph()
    p = doc.add_paragraph()
    r = p.add_run("Keywords: ")
    r.bold = True
    p.add_run(
        "[keyword 1], [keyword 2], SATTRACK, satellite tracking, weather-aware planning, [add further terms]"
    )

    _p(doc, "List of figures", style="TTP Section Heading")
    _p(
        doc,
        "[Insert References → Insert Table of Figures after captioning all figures with References → Insert Caption "
        "(Caption / “Legenda” style).]",
    )
    _p(doc, "[Automatic list appears here.]")

    _p(doc, "List of tables", style="TTP Section Heading")
    _p(doc, "[Same as figures for tables; use consistent numbering, e.g., Table 3.2.]")
    _p(doc, "[Automatic list appears here.]")

    doc.add_page_break()

    _note(
        doc,
        "[Use Heading 1–3 only for numbered sections. Update the Table of contents field after editing headings "
        "(right-click → Update field). Literature discovery tools (e.g., scite.ai, Web of Science) may help screening "
        "but do not replace reading primary sources.]",
    )

    _h1(doc, "Introduction")
    _p(
        doc,
        "[Opening narrative: move from the broader context—growth of small-sat and EO missions, need for reliable pass "
        "prediction and field observation planning—to the concrete gap your thesis addresses. Avoid bullet-only exposition; "
        "each paragraph should advance the argument toward SATTRACK.]",
    )
    _p(
        doc,
        "[State of the art / literature review: synthesise peer-reviewed work and technical reports on orbit propagation "
        "with public ephemerides, scheduling and weather constraints, web-based geospatial workflows, and comparable tools. "
        "Contrast assumptions (TLE accuracy, latency budgets) across studies.]",
    )
    _p(
        doc,
        "[Problem domain: satellite tracking, visibility windows, data latency, and operational safety for ground users. "
        "Highlight why integrating trajectory prediction with weather-aware planning matters.]",
    )
    _p(
        doc,
        "[Research gaps: e.g., weak coupling between prediction services and structured observation logs, limited "
        "repeatability of published evaluations, or lack of documented workflows for student/research use cases.]",
    )
    _p(
        doc,
        "This thesis aims to [complete the sentence: e.g., design, implement, and empirically evaluate the SATTRACK system "
        "for satellite trajectory prediction and weather-aware observation planning, demonstrating utility and performance "
        "through a documented case study].",
    )
    _p(doc, "[Close the introduction with a short roadmap describing Chapters 2–7.]")

    _h2(doc, "Aim of the Thesis")
    _note(doc, "[One primary objective; optional secondary objectives tied to measurable outcomes.]")
    _p(
        doc,
        "This thesis aims to [restate succinctly—implementation + evaluation + contribution boundary]. [Expand with 1–2 "
        "paragraphs on sub-goals, e.g., accuracy targets, usability criteria, or deployment constraints.]",
    )

    _h2(doc, "Scope of the Thesis")
    _note(doc, "[Explicit inclusions and exclusions strengthen defensibility.]")
    _p(doc, "Included within scope:")
    _bullet(
        doc,
        [
            "[The SATTRACK application as implemented in the repository version under evaluation.]",
            "[Satellite sets, ephemeris sources, and environmental data actually consumed.]",
            "[Functional scope: accounts, events/areas, observation logging, APIs relevant to your build.]",
            "[Evaluation scope: hardware, software versions, datasets, and ethics (personal data).]",
        ],
    )
    _p(doc, "Explicitly excluded (non-goals):")
    _bullet(
        doc,
        [
            "[Items outside the thesis agreement—e.g., mission-critical certification, proprietary mission APIs not used.]",
        ],
    )
    _p(
        doc,
        "[Assumptions and limitations: TLE age, omitted atmospheric or terrain models, single-site deployment, sample size "
        "for any user study.]",
    )

    _h2(doc, "Research Questions and Hypotheses")
    _note(doc, "[Prefer 2–4 focused, falsifiable questions.]")
    _p(doc, "RQ1: [How does SATTRACK perform relative to … under … conditions?]")
    _p(doc, "RQ2: [Does weather-aware planning improve … compared to …?]")
    _p(doc, "RQ3: [What are the dominant error sources or bottlenecks in …?]")
    _p(doc, "[Optional hypothesis H1, e.g., prediction residuals remain within ±X s for mission Y under assumption Z.]")
    doc.add_page_break()

    _h1(doc, "Materials and Methods")
    _note(
        doc,
        "[Reproducibility: record versions, archived URLs, seeds, hardware, and institutional review if personal data are processed.]",
    )
    _p(
        doc,
        "[Research methodology: justify design-science, case study, controlled experiment, or mixed methods against the RQs.]",
    )
    _p(
        doc,
        "[Data sources: TLE/catalogue providers, mission APIs, meteorological inputs, geospatial layers—list only what the "
        "system uses.]",
    )
    _p(
        doc,
        "[Technologies and code: programming languages, Django (or other) services, Skyfield or propagator libraries, "
        "databases, front-end stack, deployment tooling.]",
    )
    _p(doc, "[Research environment: OS, Python version, dependency lockfile, version control, CI, hosting topology.]")
    _p(doc, "[Figure placeholder: system architecture with components and trust boundaries.]")

    _h2(doc, "SATTRACK Application Description")
    _p(
        doc,
        "Purpose: [Narrative paragraph on the user problem—who benefits, from what workflow, under which operational assumptions.]",
    )
    _p(
        doc,
        "Functionalities: [Describe pass/trajectory prediction, map or UI interactions, event or area definitions, satellite "
        "selection, observation logging, administration, exports.]",
    )
    _p(
        doc,
        "Architecture: [Explain browser, application server, persistence, background tasks, authentication, and external services.]",
    )
    _p(
        doc,
        "[Figure placeholder: sequence diagram for a representative path (plan → compute → record observation).]",
    )
    doc.add_page_break()

    _h1(doc, "Research and Analysis")
    _note(doc, "[Link each analysis to an RQ; pre-register metrics where applicable.]")
    _p(
        doc,
        "[Case study narrative: scenario, geography, time window, satellites, participants or roles, and success criteria.]",
    )
    _p(
        doc,
        "[What was done: experiments, benchmarks, logging protocols, questionnaires.]",
    )
    _p(
        doc,
        "[What was measured: define each metric symbol, unit, instrument, and repetition count.]",
    )
    _p(
        doc,
        "[How the system was evaluated: baselines, statistical tests, threat-to-validity discussion and mitigations.]",
    )
    doc.add_page_break()

    _h1(doc, "Results")
    _note(doc, "[Report facts; reserve interpretation for Discussion.]")
    _p(doc, "[Table placeholder: configuration matrix (machine, OS, library versions, datasets).]")
    _p(doc, "[Table placeholder: numerical outcomes with dispersion or confidence intervals.]")
    _p(doc, "[Figure placeholder: latency, error vs TLE age, or throughput charts.]")
    _p(doc, "[Figure placeholder: SATTRACK UI screenshots with numbered call-outs matching the caption.]")
    _p(doc, "[Analytical commentary limited to patterns visible in the data—no literature comparison here.]")
    doc.add_page_break()

    _h1(doc, "Discussion")
    _note(doc, "[Interpret results against §1; discuss mechanisms and surprises.]")
    _p(
        doc,
        "[Compare magnitudes and behaviours with prior work; explain agreements and discrepancies. Discuss practical vs "
        "statistical significance.]",
    )
    _p(doc, "[Implications for operators, researchers, or maintainers of SATTRACK.]")
    doc.add_page_break()

    _h1(doc, "Conclusions")
    _p(doc, "[Concise summary of contributions in past tense.]")
    _p(doc, "[Explicit answers to each research question.]")
    _p(doc, "[Limitations tied to scope and data.]")
    _p(
        doc,
        "[Future work: ranked improvements—dynamics fidelity, additional weather products, scalability, UX studies, "
        "integration with institutional identity systems.]",
    )
    doc.add_page_break()

    _h1(doc, "References")
    _note(doc, "[Choose IEEE or APA and apply it consistently; verify every entry against primary sources.]")
    _p(doc, "IEEE-style placeholders:")
    _ref(doc, "[1] D. A. Vallado, Fundamentals of Astrodynamics and Applications, 4th ed. Microcosm Press, 2013.")
    _ref(
        doc,
        "[2] A. N. Author, “Title of paper,” in Proc. Conference Name, City, Year, pp. xx–yy.",
    )
    _ref(doc, "[3] Project or documentation page. URL (accessed YYYY-MM-DD).]")
    doc.add_paragraph()
    _p(doc, "APA-style placeholders (if required):")
    doc.add_paragraph(
        "Author, A. A. (Year). Title of work. Publisher. https://…",
        style="literatura nienumerowana",
    )
    doc.add_page_break()

    _h1(doc, "Appendix (optional)")
    _p(doc, "[Long tables, questionnaires, extra plots, API listings—only material referenced in the main text.]")
    doc.add_page_break()

    _p(doc, "Official statements and declarations", style="Zakonczenie")
    _note(
        doc,
        "[Insert the faculty’s official declaration of authorship, plagiarism statement, data availability, and funding "
        "acknowledgements without altering mandatory legal wording.]",
    )
    _p(doc, "[Dean’s forms go here.]")


def _resolve_source_template() -> Path:
    for p in _SOURCE_CANDIDATES:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "No WiR template found. Place ``SszablonPracyInzMgr.docx`` in the project root or in ~/Downloads/."
    )


def _iter_paragraphs(root):
    body = root.find(f"./{W}body")
    if body is None:
        return []
    return body.findall(f"./{W}p")


def _paragraph_text(p_el) -> str:
    return "".join(t.text or "" for t in p_el.findall(f".//{W}t"))


def _make_bookmark_start(bookmark_id: int, name: str):
    return ET.Element(f"{W}bookmarkStart", {f"{W}id": str(bookmark_id), f"{W}name": name})


def _make_bookmark_end(bookmark_id: int):
    return ET.Element(f"{W}bookmarkEnd", {f"{W}id": str(bookmark_id)})


def _make_text_run(text: str):
    run = ET.Element(f"{W}r")
    text_el = ET.SubElement(run, f"{W}t")
    if text.startswith(" ") or text.endswith(" "):
        text_el.set(XML_SPACE, "preserve")
    text_el.text = text
    return run


def _clone_ppr_from_sdt(sdt_content, style_id: str):
    for p_el in sdt_content.findall(f"./{W}p"):
        p_style = p_el.find(f"./{W}pPr/{W}pStyle")
        if p_style is not None and p_style.get(f"{W}val") == style_id:
            ppr = p_el.find(f"./{W}pPr")
            if ppr is not None:
                return ET.fromstring(ET.tostring(ppr, encoding="utf-8"))
    raise RuntimeError(f"Could not find TOC paragraph style template {style_id!r} in SDT content.")


def _build_toc_entry_paragraph(ppr_template, entry_text: str, anchor: str):
    p_el = ET.Element(f"{W}p")
    p_el.append(ET.fromstring(ET.tostring(ppr_template, encoding="utf-8")))
    hyperlink = ET.SubElement(
        p_el,
        f"{W}hyperlink",
        {f"{W}anchor": anchor, f"{W}history": "1"},
    )
    hyperlink.append(_make_text_run(entry_text))
    return p_el


def _postprocess_toc_and_bookmarks(docx_path: Path) -> None:
    with zipfile.ZipFile(docx_path, "r") as zin:
        xml_bytes = zin.read("word/document.xml")
        root = ET.fromstring(xml_bytes)

        bookmark_ids = [
            int(bm.get(f"{W}id"))
            for bm in root.findall(f".//{W}bookmarkStart")
            if bm.get(f"{W}id", "").isdigit()
        ]
        next_bookmark_id = (max(bookmark_ids) + 1) if bookmark_ids else 1

        anchor_by_heading = {}
        for _, heading_text, _ in TOC_ENTRIES:
            for p_el in _iter_paragraphs(root):
                if _paragraph_text(p_el).strip() != heading_text:
                    continue
                if p_el.findall(f"./{W}bookmarkStart"):
                    bm = p_el.find(f"./{W}bookmarkStart")
                    anchor_by_heading[heading_text] = bm.get(f"{W}name")
                    break

                anchor = f"_SATTRACK_Toc_{next_bookmark_id}"
                ppr = p_el.find(f"./{W}pPr")
                insert_at = 1 if ppr is not None else 0
                p_el.insert(insert_at, _make_bookmark_start(next_bookmark_id, anchor))
                p_el.append(_make_bookmark_end(next_bookmark_id))
                anchor_by_heading[heading_text] = anchor
                next_bookmark_id += 1
                break
            else:
                raise RuntimeError(f"Heading not found while building TOC: {heading_text!r}")

        body = root.find(f"./{W}body")
        if body is None:
            raise RuntimeError("document.xml has no body.")

        sdt = body.find(f"./{W}sdt")
        if sdt is None:
            raise RuntimeError("Could not find Table of contents SDT block.")
        sdt_content = sdt.find(f"./{W}sdtContent")
        if sdt_content is None:
            raise RuntimeError("TOC SDT block has no sdtContent.")

        heading_ppr = _clone_ppr_from_sdt(sdt_content, "Nagwekspisutreci")
        level1_ppr = _clone_ppr_from_sdt(sdt_content, "Spistreci1")
        level2_ppr = _clone_ppr_from_sdt(sdt_content, "Spistreci2")

        for child in list(sdt_content):
            sdt_content.remove(child)

        toc_heading = ET.Element(f"{W}p")
        toc_heading.append(heading_ppr)
        toc_heading.append(_make_text_run("Table of contents"))
        sdt_content.append(toc_heading)

        for entry_text, heading_text, style_id in TOC_ENTRIES:
            ppr = level1_ppr if style_id == "Spistreci1" else level2_ppr
            sdt_content.append(
                _build_toc_entry_paragraph(ppr, entry_text, anchor_by_heading[heading_text])
            )

        updated_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            temp_docx = Path(tmp.name)

        with zipfile.ZipFile(docx_path, "r") as zin, zipfile.ZipFile(
            temp_docx, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            for item in zin.infolist():
                data = updated_xml if item.filename == "word/document.xml" else zin.read(item.filename)
                zout.writestr(item, data)

    shutil.move(temp_docx, docx_path)


def main() -> None:
    try:
        source = _resolve_source_template()
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    DOCS.mkdir(parents=True, exist_ok=True)
    if OUTPUT.is_file():
        shutil.copy2(OUTPUT, OUTPUT_PREVIOUS)
        print(f"Previous output saved as: {OUTPUT_PREVIOUS}")

    shutil.copy2(source, OUTPUT)
    print(f"Copied template from: {source}")

    doc = Document(str(OUTPUT))
    body = doc.element.body

    _apply_english_title_page(body)
    sdt = body[TOC_SDT_INDEX]
    if sdt.tag.endswith("sdt"):
        _patch_toc_sdt_title(sdt)

    _strip_body_from_index(body, AFTER_TOC_SPACER_INDEX + 1)
    _append_sattrack_template_body(doc)
    doc.save(str(OUTPUT))
    _postprocess_toc_and_bookmarks(OUTPUT)
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()