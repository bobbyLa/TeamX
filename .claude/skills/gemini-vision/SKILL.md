---
name: gemini-vision
description: 按场景自动路由 Gemini 视觉模型来分析图片。适用于图片问答、OCR、小字和文档提取、图表理解、快速识别与低成本打标。无需 Chrome，直接调用 Google AI REST API，支持 PNG/JPG/WEBP/GIF/BMP，并允许通过 --scene 或 --model 显式覆盖。
---

# gemini-vision Skill

通过 Gemini 视觉 API 做图片理解，默认按场景自动选模，也支持显式指定模型。

默认路由：

- `detail` -> `gemini-3-flash-preview`
- `general` -> `gemini-2.5-flash`
- `fast` -> `gemini-3.1-flash-lite-preview`
- `basic` -> `gemini-2.5-flash-lite`

## 依赖

- Python 3（项目 `.venv` 中有）
- `GEMINI_API_KEY`，可从进程环境变量或仓库根目录 `.env` 读取
- 本地配置约定见 `.claude/local-config.md`

## 使用方式

### 兼容旧调用

```bash
./.venv/Scripts/python .claude/skills/gemini-vision/gemini_vision.py <图片路径> <问题> [输出JSON路径]
```

### 新调用方式

```bash
./.venv/Scripts/python .claude/skills/gemini-vision/gemini_vision.py <图片路径> <问题> \
  [--scene auto|detail|general|fast|basic] \
  [--model <model-id>] \
  [--media-resolution auto|low|medium|high|ultra-high] \
  [--dry-run] \
  [--no-fallback] \
  [--output <输出JSON路径>]
```

### 示例

默认自动路由：

```bash
./.venv/Scripts/python .claude/skills/gemini-vision/gemini_vision.py "runs/screenshot.png" "描述这张截图并回答里面的问题"
```

显式高精度细节提取：

```bash
./.venv/Scripts/python .claude/skills/gemini-vision/gemini_vision.py "runs/invoice.png" "识别这张发票上的小字和金额" --scene detail --output "runs/gemini-vision-detail.json"
```

显式低延迟识别：

```bash
./.venv/Scripts/python .claude/skills/gemini-vision/gemini_vision.py "runs/animal.png" "快速看看这是什么动物" --scene fast
```

只看路由结果，不发请求：

```bash
./.venv/Scripts/python .claude/skills/gemini-vision/gemini_vision.py "runs/screenshot.png" "识别图表细节" --dry-run
```

显式指定模型，跳过场景路由：

```bash
./.venv/Scripts/python .claude/skills/gemini-vision/gemini_vision.py "runs/screenshot.png" "描述图片内容" --model gemini-2.5-flash
```

## 场景说明

- `auto`: 根据问题中的关键词自动判断
- `detail`: OCR、小字、合同、发票、手写、图表、细节提取
- `general`: 常规图片问答、描述、打标、一般视觉理解
- `fast`: 快速看一眼、粗略总结、简单分类、低延迟识别
- `basic`: 显式低成本档，只做基础视觉识别；不会被自动命中

## 与 ask-gemini 的分工

TeamX 对 Gemini 有两条通道，分工明确：

- **`ask-gemini`**（浏览器端 / chrome-devtools）：图片生成、复杂理解、需要深度推理的任务。底层是 Gemini 大模型，支持 Deep Research，适合需要强理解力和创造力的场景。
- **`gemini-vision`**（API 端 / REST）：日常轻量级任务，主要作为当前文本模型的眼睛——截图问答、发票 OCR、图表提取、批量图片打标等不需要大模型推理的视觉辅助任务。

简单说：**需要 Gemini 帮你想的时候用 ask-gemini，需要它帮你看的时候用 gemini-vision。**

## 输出格式

成功、失败和 `--dry-run` 都输出统一 JSON 结构；如果没有指定输出路径，普通成功场景仍直接打印答案文本。

```json
{
  "source": "gemini-vision",
  "model": "gemini-2.5-flash",
  "requested_scene": "auto",
  "resolved_scene": "general",
  "selection_reason": "Auto-detected general scene because no detail or fast keywords matched.",
  "image_path": "E:/.../screenshot.png",
  "question": "描述这张截图",
  "request_config": {
    "route_models": [
      "gemini-2.5-flash",
      "gemini-3-flash-preview",
      "gemini-3.1-flash-lite-preview"
    ],
    "media_resolution": "auto",
    "temperature": 0.2,
    "max_output_tokens": 2048,
    "fallback_enabled": true,
    "dry_run": false
  },
  "attempts": [
    {
      "model": "gemini-2.5-flash",
      "media_resolution": "auto",
      "status": "success"
    }
  ],
  "answer": "这是一张...",
  "error": null
}
```

失败时返回非零退出码；如果指定了输出路径，也会把错误写进 JSON，`attempts` 会记录每次模型尝试和失败原因。

## 实现说明

- 使用 Google AI REST API：`v1beta/models/{model}:generateContent`
- 认证方式：HTTP header `x-goog-api-key`
- 不依赖 `curl`，仅使用 Python 标准库
- `detail` 默认高分辨率，`fast/basic` 默认低分辨率，`general` 默认自动分辨率

## 参考文档

- Gemini 3 guide: https://ai.google.dev/gemini-api/docs/gemini-3
- Models page: https://ai.google.dev/gemini-api/docs/models
- Media resolution: https://ai.google.dev/gemini-api/docs/media-resolution
- Gemini API reference: https://ai.google.dev/api

## GEMINI_API_KEY 获取

1. 访问 https://aistudio.google.com/app/apikey
2. 点击 `Create API Key`
3. 将密钥加入环境变量或仓库根目录 `.env`:
   `GEMINI_API_KEY=your_key_here`
