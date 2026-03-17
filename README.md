# pic-to-pick

[English](./README.md) | [简体中文](./README.zh-CN.md)

Turn pictures into shoppable picks.

`pic-to-pick` turns a reference image into shopping recommendations, cart-ready product matches, and an AI preview.

It understands the space and style cues in the image, suggests what to buy, and helps carry the workflow from inspiration to purchase.

Compatible with OpenClaw, Claude Code, and Codex.

### Quick Brief

- `Example 1 (Home)`: Empty living room -> real Amazon cart -> structure-locked furnished preview.
- `Example 2 (OOTD)`: Kid mock photo -> real outfit/accessory cart -> cart-constrained OOTD preview.
- `Example 3 (Beauty)`: Face makeup + nails -> product-aligned edits -> cart evidence and pricing report.

## Examples

### Example 1: Empty living room to shoppable setup

This example starts from an empty living room, builds a real Amazon cart, and generates a final preview constrained to the selected products.

Full report: [showcase/example1-success/report-project/REPORT.md](showcase/example1-success/report-project/REPORT.md)

| Site | Style target | Cart items | Cart total |
| --- | --- | --- | --- |
| Amazon | Japandi / warm minimal | 11 | S$3,726.55 |

| Analysis result | Priority buys |
| --- | --- |
| Bright living room with a large window, light wood flooring, and a built-in media wall. The doorway and circulation on the right side need to stay clear. | Rug, floor lamp, curtains/blinds first. Sofa, coffee table, and soft accessories can follow later. |

<table>
  <tr>
    <th width="25%">Base</th>
    <th width="25%">Product</th>
    <th width="25%">Preview</th>
    <th width="25%">Cart Evidence</th>
  </tr>
  <tr>
    <td>
      <img src="showcase/example1-success/report-project/images/01-base-space.jpg" alt="Original empty living room" width="100%">
    </td>
    <td>
      <img src="showcase/example1-success/report-project/images/05-product-board.jpg" alt="Product reference board" width="100%">
    </td>
    <td>
      <img src="showcase/example1-success/report-project/images/02-final-preview.jpg" alt="Final AI preview" width="100%">
    </td>
    <td>
      <details>
        <summary>Show cart evidence</summary>
        <img src="showcase/example1-success/report-project/images/04-cart-evidence.jpg" alt="Amazon cart evidence" width="100%">
      </details>
    </td>
  </tr>
</table>

<details>
  <summary>Cart price breakdown</summary>

  <br>

  | # | Item | Unit price | Qty | Subtotal |
  | --- | --- | ---: | ---: | ---: |
  | 1 | Olive Trees Artificial Indoor, 5FT Tall Faux Olive Tree wit... | S$84.40 | 1 | S$ 84.40 |
  | 2 | YIICKO Khaki Throw Blanket for Couch Sofa 50x60 inches Stri... | S$12.78 | 1 | S$ 12.78 |
  | 3 | MIULEE Pack of 4 Couch Throw Pillow Covers 18x18 Inch Neutr... | S$23.01 | 1 | S$ 23.01 |
  | 4 | monohomi Wood Side Table, Tool-Free Mortise and Tenon Boho ... | S$63.94 | 1 | S$ 63.94 |
  | 5 | Baxton Studio Georgina Japandi Cream Boucle and Walnut Brow... | S$133.10 | 1 | S$ 133.10 |
  | 6 | Mordchil HF 34"(L) Cloud Coffee Table, Modern Wood Coffee T... | S$179.04 | 1 | S$ 179.04 |
  | 7 | BAMBOOHOMIE Foldable Foot Stool Ottoman, Modern Foot Rest w... | S$51.15 | 1 | S$ 51.15 |
  | 8 | GVAwood Oak, Solid Rubberwood Walnut Color Scandinavian Jap... | S$2,853.38 | 1 | S$ 2,853.38 |
  | 9 | jinchan Linen Curtains 84 Inches Long for Living Room Bedro... | S$44.41 | 1 | S$ 44.41 |
  | 10 | Bedsure 8x10 Printed Jute-Look Rug for Living Room, Machine... | S$166.25 | 1 | S$ 166.25 |
  | 11 | FLIOPIO Japanese Rice Paper Floor Lamp - 3000K Color Bulb I... | S$115.09 | 1 | S$ 115.09 |

  Cart total: `S$3,726.55`
</details>

What this example shows:

- The room layout and camera angle stay locked to the original image.
- The preview is generated from real items that were added to the shopping cart.
- The product board provides the visual references used during image generation.
- The report includes real cart amounts per item and the cart total.

### Example 2: OOTD (Outfit Of The Day)

This run starts from a mock 9:16 full-body kid photo, builds a real Amazon cart for outfit/accessory items, and generates a cart-constrained final preview.

Full report: [showcase/example2-ootd/report-project/REPORT.md](showcase/example2-ootd/report-project/REPORT.md)

| Site | Scenario | Cart items | Cart total |
| --- | --- | --- | --- |
| Amazon | Kids casual OOTD | 7 | S$179.41 |

<table>
  <tr>
    <th width="25%">Base</th>
    <th width="25%">Product</th>
    <th width="25%">Preview</th>
    <th width="25%">Cart Evidence</th>
  </tr>
  <tr>
    <td>
      <img src="showcase/example2-ootd/report-project/images/01-base-space.jpg" alt="Example2 original" width="100%">
    </td>
    <td>
      <img src="showcase/example2-ootd/report-project/images/05-product-board.jpg" alt="Example2 product board" width="100%">
    </td>
    <td>
      <img src="showcase/example2-ootd/report-project/images/02-final-preview.jpg" alt="Example2 final preview" width="100%">
    </td>
    <td>
      <details>
        <summary>Show cart evidence</summary>
        <img src="showcase/example2-ootd/report-project/images/04-cart-evidence.jpg" alt="Example2 cart evidence" width="100%">
      </details>
    </td>
  </tr>
</table>

### Example 3: Beauty (Face + Nails)

This example is split into two successful runs with the same standards as Example 1:
- real Amazon cart
- real product image pull
- cart-constrained preview generation
- report with per-item real amount and cart total

Face makeup report: [showcase/example3-beauty-face/report-project/REPORT.md](showcase/example3-beauty-face/report-project/REPORT.md)  
Nail design report: [showcase/example3-beauty-nail/report-project/REPORT.md](showcase/example3-beauty-nail/report-project/REPORT.md)

| Sub-case | Cart items | Cart total |
| --- | --- | --- |
| Beauty face | 3 | S$35.80 |
| Beauty nail | 1 | $9.99 |

#### Beauty Face

<table>
  <tr>
    <th width="25%">Base</th>
    <th width="25%">Product</th>
    <th width="25%">Preview</th>
    <th width="25%">Cart Evidence</th>
  </tr>
  <tr>
    <td>
      <img src="showcase/example3-beauty-face/report-project/images/01-base-space.jpg" alt="Beauty face original" width="100%">
    </td>
    <td>
      <img src="showcase/example3-beauty-face/report-project/images/05-product-board.jpg" alt="Beauty face product board" width="100%">
    </td>
    <td>
      <img src="showcase/example3-beauty-face/report-project/images/02-final-preview.jpg" alt="Beauty face final preview" width="100%">
    </td>
    <td>
      <details>
        <summary>Show cart evidence</summary>
        <img src="showcase/example3-beauty-face/report-project/images/04-cart-evidence.jpg" alt="Beauty face cart evidence" width="100%">
      </details>
    </td>
  </tr>
</table>

#### Beauty Nail

<table>
  <tr>
    <th width="25%">Base</th>
    <th width="25%">Product</th>
    <th width="25%">Preview</th>
    <th width="25%">Cart Evidence</th>
  </tr>
  <tr>
    <td>
      <img src="showcase/example3-beauty-nail/report-project/images/01-base-space.jpg" alt="Beauty nail original" width="100%">
    </td>
    <td>
      <img src="showcase/example3-beauty-nail/report-project/images/05-product-board.jpg" alt="Beauty nail product board" width="100%">
    </td>
    <td>
      <img src="showcase/example3-beauty-nail/report-project/images/02-final-preview.jpg" alt="Beauty nail final preview" width="100%">
    </td>
    <td>
      <details>
        <summary>Show cart evidence</summary>
        <img src="showcase/example3-beauty-nail/report-project/images/04-cart-evidence.jpg" alt="Beauty nail cart evidence" width="100%">
      </details>
    </td>
  </tr>
</table>
