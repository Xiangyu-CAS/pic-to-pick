# pic-to-pick

[English](./README.md) | [简体中文](./README.zh-CN.md)

把视觉灵感变成可购买的商品组合。

`pic-to-pick` 可以根据参考图片理解空间条件和风格线索，给出购买建议，在购物网站上查找匹配商品、加入购物车，并生成这些商品组合后的 AI 预览图。

兼容 OpenClaw、Claude Code 和 Codex。

## Examples

### Example 1: 从空房客厅到可购买方案

这个示例从一张空置客厅图片开始，先在 Amazon 构建真实购物车，再基于购物车商品生成受约束的最终预览图。

完整报告： [showcase/example1-success/report-project/REPORT.md](showcase/example1-success/report-project/REPORT.md)

| 平台 | 风格目标 | 购物车商品数 | 预算区间 |
| --- | --- | --- | --- |
| Amazon | Japandi / 温暖极简 | 11 | USD 880-1950 |

| 分析结果 | 优先购买 |
| --- | --- |
| 空间采光充足，拥有大面积窗户、浅木色地板和内置电视墙。右侧门洞和主要动线需要保持畅通。 | 优先补齐地毯、落地灯和窗帘/百叶。沙发、茶几和软装配件可作为下一阶段采购。 |

<table>
  <tr>
    <th width="50%">原始空间</th>
    <th width="50%">最终预览</th>
  </tr>
  <tr>
    <td>
      <img src="showcase/example1-success/report-project/images/01-base-space.jpg" alt="原始空房客厅" width="100%">
    </td>
    <td>
      <img src="showcase/example1-success/report-project/images/02-final-preview.jpg" alt="最终 AI 预览图" width="100%">
    </td>
  </tr>
</table>

<table>
  <tr>
    <th width="50%">购物车证据</th>
    <th width="50%">商品参考板</th>
  </tr>
  <tr>
    <td align="center">
      <img src="showcase/example1-success/report-project/images/04-cart-evidence.jpg" alt="Amazon 购物车截图" width="58%">
    </td>
    <td align="center">
      <img src="showcase/example1-success/report-project/images/05-product-board.jpg" alt="商品参考板" width="72%">
    </td>
  </tr>
</table>

这个示例展示了：

- 在不改变房间结构和视角的前提下完成软装方案生成。
- 预览图只使用购物车里的真实商品作为参考约束。
- 商品参考板可直接作为生图输入的一部分。
