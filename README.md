# pic-to-pick

[English](./README.md) | [简体中文](./README.zh-CN.md)

Turn pictures into shoppable picks.

`pic-to-pick` turns a reference image into shopping recommendations, cart-ready product matches, and an AI preview.

It understands the space and style cues in the image, suggests what to buy, and helps carry the workflow from inspiration to purchase.

Compatible with OpenClaw, Claude Code, and Codex.

## Examples

### Example 1: Empty living room to shoppable setup

This example starts from an empty living room, builds a real Amazon cart, and generates a final preview constrained to the selected products.

Full report: [showcase/example1-success/report-project/REPORT.md](showcase/example1-success/report-project/REPORT.md)

| Site | Style target | Cart items | Estimated budget |
| --- | --- | --- | --- |
| Amazon | Japandi / warm minimal | 11 | USD 880-1950 |

| Analysis result | Priority buys |
| --- | --- |
| Bright living room with a large window, light wood flooring, and a built-in media wall. The doorway and circulation on the right side need to stay clear. | Rug, floor lamp, curtains/blinds first. Sofa, coffee table, and soft accessories can follow later. |

<table>
  <tr>
    <th width="50%">Original space</th>
    <th width="50%">Final preview</th>
  </tr>
  <tr>
    <td>
      <img src="showcase/example1-success/report-project/images/01-base-space.jpg" alt="Original empty living room" width="100%">
    </td>
    <td>
      <img src="showcase/example1-success/report-project/images/02-final-preview.jpg" alt="Final AI preview" width="100%">
    </td>
  </tr>
</table>

<table>
  <tr>
    <th width="50%">Cart evidence</th>
    <th width="50%">Product board</th>
  </tr>
  <tr>
    <td align="center">
      <img src="showcase/example1-success/report-project/images/04-cart-evidence.jpg" alt="Amazon cart evidence" width="58%">
    </td>
    <td align="center">
      <img src="showcase/example1-success/report-project/images/05-product-board.jpg" alt="Product reference board" width="72%">
    </td>
  </tr>
</table>

What this example shows:

- The room layout and camera angle stay locked to the original image.
- The preview is generated from real items that were added to the shopping cart.
- The product board provides the visual references used during image generation.
- The report includes real cart amounts per item and the cart total.
