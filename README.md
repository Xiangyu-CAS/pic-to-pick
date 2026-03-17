# pic-to-pick

> Focused skill for one reliable flow: home-space image -> Amazon cart -> cart-only AI preview -> report project.  
> 聚焦型技能：从家居空间图到 Amazon 购物车，再到购物车白名单预览图与图文报告。

## 能做什么 (What This Skill Can Do)

### 中文

- 识别“精装完成但缺家居”的空间状态，给出可执行的家居采购方向
- 生成分层购买建议（保留 / 立即购买 / 延后购买）
- 在 Amazon 场景中完成加购链路
- 基于“空间图 + 购物车真实商品图”生成 AI 家居预览图
- 严格约束预览图：
  - 结构不变（门/窗/墙/内置结构/视角）
  - 仅允许出现购物车内商品
- 产出可分享的项目报告（图文 + 对比 + 数据索引）

### English

- Diagnose an unfurnished finished home space and produce an actionable shopping direction
- Build layered decisions (keep / buy now / buy later)
- Execute Amazon cart actions for the selected categories
- Generate AI preview from base room + real cart product images
- Enforce strict preview constraints:
  - structure lock (door/window/walls/built-ins/viewpoint)
  - cart-only purchasable objects
- Produce a shareable project report (visuals + comparison + data index)

## Showcase

- Showcase report: `showcase/example1-success/report-project/REPORT.md`

### Final Preview

![final-preview](showcase/example1-success/report-project/images/02-final-preview.jpg)

### Structure Consistency

![structure-compare](showcase/example1-success/report-project/images/03-structure-compare.jpg)

### Before vs After

| Base Space | Final Preview |
|---|---|
| ![base](showcase/example1-success/report-project/images/01-base-space.jpg) | ![preview](showcase/example1-success/report-project/images/02-final-preview.jpg) |

## 输出与交付 (Outputs)

### 中文

- 轻量展示版（适合 GitHub）：`showcase/example1-success/report-project/`
- 完整原始产物（本地保留）：`output/example1/`

### English

- Lightweight showcase (GitHub-friendly): `showcase/example1-success/report-project/`
- Full raw output (kept locally): `output/example1/`

## 适用范围 (Scope)

### 中文

当前版本只保留一条稳定主线：
`home-space -> Amazon -> cart-only preview -> report project`

### English

This version intentionally focuses on one stable production path:
`home-space -> Amazon -> cart-only preview -> report project`

## 隐私与开源安全 (Privacy)

- 展示版文件使用相对路径，不包含本机绝对目录
- 完整原始输出放在 `output/`，默认被 `.gitignore` 忽略
