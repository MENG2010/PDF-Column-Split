#!/usr/bin/env python
"""
split_columns.py — Split a two-column PDF paper into one-column-per-page.

Each source page becomes (up to) two output pages of the SAME page size:
  * Page L: left column at its original position + all column-spanning
    elements (figures, tables, title block, ...) kept full-width.
  * Page R: right column only (spanning elements are blanked out here).
The unused half of each page stays blank for handwritten notes.

Spanning elements are detected automatically from text blocks, images,
and vector drawings that cross the inter-column gap.

Usage:
    python split_columns.py input.pdf [output.pdf]

Requires: pip install pymupdf

Author:
    MENG2010
"""

import sys
import fitz  # PyMuPDF

TOL = 8          # pt: how far a box must reach past the gap to count as spanning
PAD = 3          # pt: padding added around spanning bands
MIN_DRAW_AREA = 400   # ignore tiny vector marks (rules, bullets)


def content_boxes(page):
    """Collect bounding boxes of text blocks, images, and vector drawings."""
    boxes = []
    for b in page.get_text("blocks"):
        r = fitz.Rect(b[:4])
        if not r.is_empty:
            boxes.append(r)
    for info in page.get_image_info():
        r = fitz.Rect(info["bbox"])
        if not r.is_empty:
            boxes.append(r)
    try:
        for d in page.get_drawings():
            r = fitz.Rect(d["rect"])
            if not r.is_empty and r.get_area() >= MIN_DRAW_AREA:
                boxes.append(r)
    except Exception:
        pass
    return boxes


def estimate_gap(page, boxes):
    """Estimate the x-center of the inter-column gap from non-spanning text."""
    mid = page.rect.width / 2
    left_edges, right_edges = [], []
    for r in boxes:
        if r.x1 < mid + TOL:           # entirely in left column
            left_edges.append(r.x1)
        elif r.x0 > mid - TOL:         # entirely in right column
            right_edges.append(r.x0)
    if left_edges and right_edges:
        gap_l = max(left_edges)
        gap_r = min(right_edges)
        est = (gap_l + gap_r) / 2
        # sanity: a real column gap sits near the page center
        if gap_l < gap_r and abs(est - mid) < 0.06 * page.rect.width:
            return est
    return mid


def spanning_bands(boxes, gap_x):
    """Merged y-intervals of boxes that cross the column gap."""
    bands = []
    for r in boxes:
        if r.x0 < gap_x - TOL and r.x1 > gap_x + TOL:
            bands.append([r.y0 - PAD, r.y1 + PAD])
    bands.sort()
    merged = []
    for y0, y1 in bands:
        if merged and y0 <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], y1)
        else:
            merged.append([y0, y1])
    return merged


def complement(bands, height):
    """y-intervals of the page NOT covered by spanning bands."""
    out, cur = [], 0.0
    for y0, y1 in bands:
        if y0 > cur:
            out.append((cur, y0))
        cur = max(cur, y1)
    if cur < height:
        out.append((cur, height))
    return out


def has_content(boxes, gap_x, bands, side):
    """Does this column contain anything outside the spanning bands?"""
    for r in boxes:
        if side == "L" and not (r.x1 <= gap_x + TOL):
            continue
        if side == "R" and not (r.x0 >= gap_x - TOL):
            continue
        cy = (r.y0 + r.y1) / 2
        if not any(y0 <= cy <= y1 for y0, y1 in bands):
            return True
    return False


import re

BACKMATTER_PAT = re.compile(
    r"^\s*(references|bibliography|appendix(\s+[a-z0-9])?|appendices)\b", re.I)


def find_backmatter(src):
    """Return (page_index, heading_rect) of the first References/Appendix
    heading, or (None, None) if not found."""
    for pno in range(len(src)):
        for b in src[pno].get_text("blocks"):
            text = b[4].strip()
            if len(text) < 40 and BACKMATTER_PAT.match(text):
                return pno, fitz.Rect(b[:4])
    return None, None


def white_out(page, rect):
    if rect.height > 0.5 and rect.width > 0.5:
        page.draw_rect(rect, color=None, fill=(1, 1, 1))


def split(src_path, dst_path):
    src = fitz.open(src_path)
    dst = fitz.open()

    bm_page, bm_rect = find_backmatter(src)
    if bm_page is not None:
        print(f"back matter heading found on source page {bm_page + 1}")

    for pno in range(len(src)):
        spage = src[pno]

        # Pages entirely in the back matter (references/appendices): copy as-is.
        # The boundary page itself is copied as-is only if the heading sits
        # near the top of the LEFT column (i.e. the page has no body text);
        # otherwise it still contains body content and is split normally.
        if bm_page is not None and (
            pno > bm_page
            or (pno == bm_page
                and bm_rect.x0 < spage.rect.width / 2
                and bm_rect.y0 < 0.2 * spage.rect.height)
        ):
            p = dst.new_page(width=spage.rect.width, height=spage.rect.height)
            p.show_pdf_page(p.rect, src, pno)
            print(f"page {pno+1}: back matter, kept as-is")
            continue
        W, H = spage.rect.width, spage.rect.height
        boxes = content_boxes(spage)
        gap_x = estimate_gap(spage, boxes)
        bands = spanning_bands(boxes, gap_x)
        free = complement(bands, H)

        # ---- Page L: left column + spanning elements ----
        pL = dst.new_page(width=W, height=H)
        pL.show_pdf_page(pL.rect, src, pno)
        for y0, y1 in free:  # blank the right column in non-spanning regions
            white_out(pL, fitz.Rect(gap_x, y0, W, y1))

        # ---- Page R: right column only ----
        if has_content(boxes, gap_x, bands, "R"):
            pR = dst.new_page(width=W, height=H)
            pR.show_pdf_page(pR.rect, src, pno)
            for y0, y1 in free:  # blank left column
                white_out(pR, fitz.Rect(0, y0, gap_x, y1))
            for y0, y1 in bands:  # blank spanning bands entirely
                white_out(pR, fitz.Rect(0, y0, W, y1))

        print(f"page {pno+1}: gap_x={gap_x:.1f}, spanning bands={len(bands)}")

    dst.save(dst_path, garbage=4, deflate=True)
    print(f"\nSaved {len(dst)} pages -> {dst_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp.replace(".pdf", "_split.pdf")
    split(inp, out)
