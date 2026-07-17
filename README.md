This script splits a two-column PDF into one-column-per-page while preserving the layout of column-spanning elements. It is based on PyMuPDF and supports processing the back matter of a document.

Each source page becomes (up to) two output pages of the **same** page size:

- **Page L:** Left column at its original position, with all column-spanning elements (e.g., figures, tables, title block, etc.) preserved at their original full width.
- **Page R:** Right column only; column-spanning elements are blanked out.
- The unused half of each page is left blank for handwritten notes.

Column-spanning elements are detected automatically from text blocks, images, and vector drawings that cross the inter-column gap.

> **The default settings work well for most commonly used academic paper templates, with negligible issues in handling column-spanning elements (typically figures and tables).**

## Requirements

Install the required library:

```shell
pip install pymupdf
```

## Usage

```shell
python split_columns.py input.pdf [output.pdf]
```

> **If you find this project helpful, please consider giving it a GitHub Star ⭐. Thank you for your support.**
>
> **Contributions are welcome! If you improve this tool, please preserve the original attribution. I appreciate your contributions.**

## Example

<table>
<tr>
<td align="center" width="49%">
<img src="before.png"><br>
<b>(a) Before</b>
</td>

<td align="center" width="49%">
<img src="after.png"><br>
<b>(b) After</b>
</td>
</tr>
</table>
