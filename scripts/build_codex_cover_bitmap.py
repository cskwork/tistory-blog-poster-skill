#!/usr/bin/env python3
"""Build a post-specific Codex bitmap cover from a Tistory package."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


PALETTES = {
    "on_device": ("#07111F", "#22D3EE", "#A7F3D0", "#F8FAFC", "#172033"),
    "browser_wasm": ("#10111F", "#A78BFA", "#38BDF8", "#F8FAFC", "#1E1B4B"),
    "api": ("#08111E", "#34D399", "#F59E0B", "#F8FAFC", "#12233A"),
    "hardware": ("#111827", "#F97316", "#60A5FA", "#F9FAFB", "#1F2937"),
    "tools": ("#10201C", "#2DD4BF", "#FACC15", "#ECFEFF", "#18332E"),
    "webllm": ("#0C1222", "#38BDF8", "#C084FC", "#F8FAFC", "#1D2440"),
    "transformers": ("#14111F", "#F472B6", "#60A5FA", "#FDF2F8", "#2A1E35"),
    "ollama": ("#0E1A13", "#86EFAC", "#FDE68A", "#F7FEE7", "#193124"),
    "rag": ("#0F172A", "#22D3EE", "#A78BFA", "#F8FAFC", "#18243A"),
    "gguf": ("#171717", "#FACC15", "#34D399", "#FAFAFA", "#262626"),
}

LABELS = {
    "on_device": "ON-DEVICE LLM",
    "browser_wasm": "BROWSER LLM / WASM",
    "api": "LOCAL OPENAI API",
    "hardware": "LOCAL LLM HARDWARE",
    "tools": "LOCAL LLM TOOLKIT",
    "webllm": "WEBLLM + WEBGPU",
    "transformers": "TRANSFORMERS.JS",
    "ollama": "OLLAMA LOCAL STACK",
    "rag": "OFFLINE RAG",
    "gguf": "GGUF QUANTIZATION",
}

PROFILE_KEYWORDS = [
    ("on_device", ["온디바이스", "모바일", "엣지", "MLC"]),
    ("api", ["OpenAI 호환", "OpenAI-compatible", "API", "/v1", "엔드포인트"]),
    ("hardware", ["하드웨어", "GPU", "VRAM", "메모리", "NPU"]),
    ("tools", ["도구", "비교", "LM Studio", "llama.cpp"]),
    ("webllm", ["WebLLM", "WebGPU 브라우저", "웹 LLM"]),
    ("transformers", ["Transformers.js", "transformers.js", "토크나이저", "파이프라인"]),
    ("ollama", ["Ollama", "올라마"]),
    ("rag", ["RAG", "벡터", "임베딩"]),
    ("browser_wasm", ["브라우저", "WASM", "WebGPU", "WebAssembly"]),
    ("gguf", ["GGUF", "양자화", "quantization"]),
]


def stable_int(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = ["Arial Bold.ttf", "Arial.ttf", "Helvetica.ttc"]
    roots = [Path("/System/Library/Fonts/Supplemental"), Path("/System/Library/Fonts")]
    for root in roots:
        for name in names:
            candidate = root / name
            if candidate.exists():
                try:
                    return ImageFont.truetype(str(candidate), size=size)
                except OSError:
                    continue
    return ImageFont.load_default()


def draw_gradient(draw: ImageDraw.ImageDraw, size: tuple[int, int], start: str, end: str) -> None:
    a, b = hex_rgb(start), hex_rgb(end)
    width, height = size
    for y in range(height):
        mix = y / max(height - 1, 1)
        color = tuple(int(a[i] * (1 - mix) + b[i] * mix) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)


def add_soft_glow(image: Image.Image, center: tuple[int, int], radius: int, color: str, alpha: int) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x, y = center
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*hex_rgb(color), alpha))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius / 2))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def add_vignette(image: Image.Image) -> Image.Image:
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    pixels = overlay.load()
    cx, cy = width / 2, height / 2
    max_distance = math.hypot(cx, cy)
    for y in range(height):
        for x in range(width):
            distance = math.hypot(x - cx, y - cy) / max_distance
            alpha = max(0, min(105, int((distance - 0.36) * 210)))
            if alpha:
                pixels[x, y] = (0, 0, 0, alpha)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def add_grain(image: Image.Image) -> Image.Image:
    noise = Image.effect_noise(image.size, 10).convert("L")
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    overlay.putalpha(noise.point(lambda value: 8 if value > 142 else 0))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def paint_premium_background(image: Image.Image, seed: int, colors: tuple[str, str, str, str, str]) -> Image.Image:
    _, primary, secondary, _, panel = colors
    image = add_soft_glow(image, (210 + seed % 180, 145), 280, primary, 90)
    image = add_soft_glow(image, (820 + seed % 230, 430), 340, secondary, 70)
    image = add_soft_glow(image, (1040, 120 + seed % 180), 220, panel, 85)
    return image


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], fill: str, width: int = 5) -> None:
    draw.line([start, end], fill=fill, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    wing = 16
    points = [
        end,
        (end[0] - wing * math.cos(angle - 0.45), end[1] - wing * math.sin(angle - 0.45)),
        (end[0] - wing * math.cos(angle + 0.45), end[1] - wing * math.sin(angle + 0.45)),
    ]
    draw.polygon(points, fill=fill)


def draw_chip(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], primary: str, secondary: str) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=18, fill=secondary, outline=primary, width=5)
    for x in range(x1 - 24, x2 + 25, 28):
        draw.line((x, y1 - 16, x, y1), fill=primary, width=3)
        draw.line((x, y2, x, y2 + 16), fill=primary, width=3)
    for y in range(y1 + 18, y2, 26):
        draw.line((x1 - 16, y, x1, y), fill=primary, width=3)
        draw.line((x2, y, x2 + 16, y), fill=primary, width=3)
    draw.text((x1 + 24, y1 + 38), "LLM", fill="#FFFFFF", font=font(36, True))


def draw_database(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], primary: str, panel: str) -> None:
    x1, y1, x2, y2 = box
    draw.ellipse((x1, y1, x2, y1 + 42), fill=primary)
    draw.rectangle((x1, y1 + 20, x2, y2 - 22), fill=panel)
    draw.ellipse((x1, y2 - 44, x2, y2), fill=panel, outline=primary, width=4)
    for y in range(y1 + 76, y2 - 34, 46):
        draw.arc((x1, y, x2, y + 44), start=0, end=180, fill=primary, width=3)


def center_label(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, fill: str, size: int = 26) -> None:
    label_font = font(size, True)
    text_box = draw.textbbox((0, 0), text, font=label_font)
    width = text_box[2] - text_box[0]
    height = text_box[3] - text_box[1]
    x = box[0] + (box[2] - box[0] - width) / 2
    y = box[1] + (box[3] - box[1] - height) / 2
    draw.text((x, y), text, fill=fill, font=label_font)


def package_text(data: dict[str, object]) -> str:
    parts = [str(data.get("title", "")), str(data.get("summary", "")), " ".join(data.get("tags", []))]
    body_path = data.get("body_markdown")
    if body_path and Path(str(body_path)).exists():
        parts.append(Path(str(body_path)).read_text(encoding="utf-8")[:6000])
    return " ".join(parts)


def choose_profile(data: dict[str, object]) -> str:
    title = str(data.get("title", ""))
    summary = str(data.get("summary", ""))
    tags = " ".join(data.get("tags", []))
    primary = " ".join([title, summary, tags])
    title_rules = [
        ("tools", ["도구 비교", "Ollama vs", "LM Studio"]),
        ("on_device", ["온디바이스", "모바일", "엣지"]),
        ("ollama", ["Ollama", "올라마"]),
        ("api", ["OpenAI", "API"]),
        ("hardware", ["하드웨어", "VRAM", "RAM", "Apple Silicon"]),
        ("webllm", ["WebLLM"]),
        ("transformers", ["transformers.js", "Transformers.js"]),
        ("rag", ["RAG", "벡터", "임베딩"]),
        ("browser_wasm", ["브라우저", "WASM", "WebGPU", "WebAssembly"]),
        ("gguf", ["GGUF", "양자화"]),
    ]
    for profile, keywords in title_rules:
        if any(keyword in title for keyword in keywords):
            return profile
    for profile, keywords in PROFILE_KEYWORDS:
        if any(keyword in primary for keyword in keywords):
            return profile
    text = package_text(data)
    for profile, keywords in PROFILE_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return profile
    return "rag"


def draw_topic_header(draw: ImageDraw.ImageDraw, profile: str, ink: str, primary: str) -> None:
    draw.text((70, 58), LABELS[profile], fill=ink, font=font(44, True))
    draw.text((72, 114), "SEO MACHINE / CODEX VISUAL", fill=primary, font=font(18, True))


def draw_on_device(draw: ImageDraw.ImageDraw, seed: int, colors: tuple[str, str, str, str, str]) -> None:
    _, primary, secondary, ink, panel = colors
    draw.rounded_rectangle((120, 190, 355, 555), radius=42, fill=panel, outline=primary, width=8)
    draw.rounded_rectangle((155, 250, 320, 450), radius=24, fill="#0F172A")
    draw_chip(draw, (510, 210, 725, 405), primary, "#164E63")
    for index in range(7):
        angle = (seed % 90 + index * 52) * math.pi / 180
        x = 830 + math.cos(angle) * 165
        y = 325 + math.sin(angle) * 130
        draw.ellipse((x - 24, y - 24, x + 24, y + 24), fill=secondary)
        draw.line((618, 307, x, y), fill=primary, width=3)
    draw.rounded_rectangle((820, 170, 1045, 255), radius=22, fill=panel, outline=secondary, width=4)
    center_label(draw, (820, 170, 1045, 255), "EDGE", ink)
    draw.rounded_rectangle((812, 420, 1075, 505), radius=24, fill=panel, outline=primary, width=4)
    center_label(draw, (812, 420, 1075, 505), "PRIVATE", ink)


def draw_browser_wasm(draw: ImageDraw.ImageDraw, seed: int, colors: tuple[str, str, str, str, str]) -> None:
    _, primary, secondary, ink, panel = colors
    draw.rounded_rectangle((110, 170, 1070, 545), radius=28, fill="#F8FAFC")
    draw.rectangle((110, 170, 1070, 235), fill=panel)
    for x in (150, 188, 226):
        draw.ellipse((x, 194, x + 18, 212), fill=secondary)
    cards = [("web-llm", 175), ("wllama", 410), ("tf.js", 645)]
    for label, x in cards:
        draw.rounded_rectangle((x, 295, x + 180, 420), radius=20, fill=panel, outline=primary, width=4)
        center_label(draw, (x, 295, x + 180, 350), label, ink, 22)
        draw.rounded_rectangle((x + 30, 365, x + 150, 392), radius=10, fill=secondary)
    draw_arrow(draw, (825, 358), (910, 358), secondary, 6)
    draw_chip(draw, (910, 285, 1035, 430), primary, "#312E81")
    draw.rounded_rectangle((250, 455, 625, 505), radius=18, fill=panel, outline=secondary, width=3)
    center_label(draw, (250, 455, 625, 505), "WASM + COOP/COEP", ink, 21)


def draw_api(draw: ImageDraw.ImageDraw, seed: int, colors: tuple[str, str, str, str, str]) -> None:
    _, primary, secondary, ink, panel = colors
    for index in range(3):
        y = 250 + index * 76
        draw.rounded_rectangle((125, y, 315, y + 54), radius=14, fill=panel, outline=primary, width=3)
        center_label(draw, (125, y, 315, y + 54), ["APP", "BOT", "CLI"][index], ink, 22)
        draw_arrow(draw, (315, y + 27), (455, 342), secondary, 5)
    draw.rounded_rectangle((455, 245, 755, 440), radius=24, fill=panel, outline=secondary, width=6)
    draw.text((495, 290), "/v1/chat", fill=ink, font=font(36, True))
    draw.text((495, 342), "OpenAI-compatible", fill=primary, font=font(22, True))
    draw_arrow(draw, (755, 342), (875, 342), secondary, 7)
    draw_database(draw, (875, 238, 1060, 462), primary, panel)
    center_label(draw, (875, 305, 1060, 390), "LOCAL", ink, 24)


def draw_hardware(draw: ImageDraw.ImageDraw, seed: int, colors: tuple[str, str, str, str, str]) -> None:
    _, primary, secondary, ink, panel = colors
    draw.rounded_rectangle((160, 250, 780, 445), radius=28, fill=panel, outline=primary, width=6)
    draw.ellipse((210, 288, 350, 428), outline=secondary, width=12)
    draw.ellipse((390, 288, 530, 428), outline=secondary, width=12)
    for index in range(8):
        x = 570 + (index % 4) * 46
        y = 292 + (index // 4) * 68
        draw.rounded_rectangle((x, y, x + 34, y + 48), radius=7, fill=primary)
    draw.rounded_rectangle((830, 205, 1045, 515), radius=26, fill=panel, outline=secondary, width=5)
    center_label(draw, (830, 225, 1045, 290), "VRAM", ink, 34)
    for index, label in enumerate(["8GB", "16GB", "24GB"]):
        y = 325 + index * 58
        draw.rounded_rectangle((875, y, 1005, y + 30), radius=15, fill=primary if index != seed % 3 else secondary)
        draw.text((905, y + 4), label, fill="#111827", font=font(18, True))


def draw_tools(draw: ImageDraw.ImageDraw, seed: int, colors: tuple[str, str, str, str, str]) -> None:
    _, primary, secondary, ink, panel = colors
    x_positions = [150, 415, 680, 945]
    labels = ["CLI", "GUI", "API", "SERVER"]
    for x, label in zip(x_positions, labels):
        draw.rounded_rectangle((x, 210, x + 170, 495), radius=22, fill=panel, outline=primary, width=4)
        center_label(draw, (x, 235, x + 170, 285), label, ink, 26)
        for row in range(4):
            y = 325 + row * 38
            fill = secondary if (seed + row + x) % 3 else primary
            draw.rounded_rectangle((x + 28, y, x + 142, y + 18), radius=9, fill=fill)
    for start, end in zip(x_positions, x_positions[1:]):
        draw_arrow(draw, (start + 172, 352), (end - 20, 352), secondary, 4)


def draw_transformers(draw: ImageDraw.ImageDraw, seed: int, colors: tuple[str, str, str, str, str]) -> None:
    _, primary, secondary, ink, panel = colors
    boxes = [(130, 285, 300, 405), (390, 240, 610, 450), (700, 260, 880, 430), (965, 285, 1090, 405)]
    names = ["TOKENS", "MODEL", "VECTORS", "OUTPUT"]
    for box, name in zip(boxes, names):
        draw.rounded_rectangle(box, radius=24, fill=panel, outline=primary, width=5)
        center_label(draw, box, name, ink, 24)
    for start, end in [((300, 345), (390, 345)), ((610, 345), (700, 345)), ((880, 345), (965, 345))]:
        draw_arrow(draw, start, end, secondary, 6)
    for index in range(9):
        x1 = 425 + index * 18
        draw.line((x1, 285, 575 - index * 10, 405), fill=secondary, width=2)


def draw_webllm(draw: ImageDraw.ImageDraw, seed: int, colors: tuple[str, str, str, str, str]) -> None:
    _, primary, secondary, ink, panel = colors
    draw.rounded_rectangle((120, 165, 1085, 545), radius=30, fill="#F8FAFC")
    draw.rectangle((120, 165, 1085, 228), fill=panel)
    for x in (160, 198, 236):
        draw.ellipse((x, 188, x + 18, 206), fill=secondary)
    draw.rounded_rectangle((175, 270, 470, 485), radius=24, fill="#E0F2FE", outline=primary, width=4)
    for index in range(4):
        y = 305 + index * 38
        draw.rounded_rectangle((210, y, 420 - index * 25, y + 21), radius=6, fill=primary)
    draw_arrow(draw, (470, 378), (585, 378), secondary, 6)
    draw.rounded_rectangle((585, 290, 760, 465), radius=24, fill=panel, outline=secondary, width=5)
    center_label(draw, (585, 305, 760, 355), "MLCEngine", ink, 18)
    center_label(draw, (585, 375, 760, 425), "Worker", ink, 22)
    draw_arrow(draw, (760, 378), (875, 378), secondary, 6)
    draw_chip(draw, (875, 290, 1025, 465), primary, "#312E81")
    draw.arc((895, 118, 1070, 248), start=35, end=325, fill=primary, width=7)
    draw.line((930, 233, 1050, 133), fill=primary, width=7)


def draw_ollama(draw: ImageDraw.ImageDraw, seed: int, colors: tuple[str, str, str, str, str]) -> None:
    _, primary, secondary, ink, panel = colors
    draw.rounded_rectangle((130, 205, 610, 500), radius=26, fill="#050A08", outline=primary, width=4)
    draw.text((170, 255), "$ ollama run model", fill=secondary, font=font(29, True))
    draw.text((170, 315), "localhost:11434", fill=primary, font=font(25, True))
    draw.text((170, 370), "streaming tokens...", fill=ink, font=font(24))
    for index in range(4):
        draw_database(draw, (735 + index * 58, 235 + index * 22, 880 + index * 58, 395 + index * 22), primary, panel)
    draw_arrow(draw, (610, 350), (735, 350), secondary, 7)


def draw_rag(draw: ImageDraw.ImageDraw, seed: int, colors: tuple[str, str, str, str, str]) -> None:
    _, primary, secondary, ink, panel = colors
    draw.rounded_rectangle((125, 230, 335, 420), radius=20, fill=panel, outline=secondary, width=5)
    for index in range(4):
        draw.line((160, 278 + index * 28, 300, 278 + index * 28), fill=ink, width=4)
    draw_arrow(draw, (335, 325), (505, 325), secondary, 6)
    draw_chip(draw, (505, 245, 705, 405), primary, "#312E81")
    draw_arrow(draw, (705, 325), (855, 325), secondary, 6)
    draw_database(draw, (855, 220, 1040, 450), primary, panel)
    for index in range(8):
        angle = (seed + index * 45) * math.pi / 180
        x = 620 + math.cos(angle) * 220
        y = 325 + math.sin(angle) * 130
        draw.ellipse((x - 11, y - 11, x + 11, y + 11), fill=secondary)


def draw_gguf(draw: ImageDraw.ImageDraw, seed: int, colors: tuple[str, str, str, str, str]) -> None:
    _, primary, secondary, ink, panel = colors
    draw.rounded_rectangle((135, 230, 370, 455), radius=26, fill=panel, outline=primary, width=5)
    center_label(draw, (135, 230, 370, 455), "FP16", ink, 34)
    draw_arrow(draw, (370, 342), (555, 342), secondary, 7)
    draw.polygon([(555, 245), (735, 320), (735, 365), (555, 440)], fill=panel, outline=secondary)
    center_label(draw, (565, 282, 720, 398), "PACK", ink, 26)
    draw_arrow(draw, (735, 342), (870, 342), secondary, 7)
    for index, label in enumerate(["Q8", "Q5", "Q4"]):
        y = 235 + index * 90
        draw.rounded_rectangle((870, y, 1035, y + 64), radius=18, fill=primary if index != 1 else secondary)
        center_label(draw, (870, y, 1035, y + 64), label, "#111827", 28)


SCENES = {
    "on_device": draw_on_device,
    "browser_wasm": draw_browser_wasm,
    "api": draw_api,
    "hardware": draw_hardware,
    "tools": draw_tools,
    "webllm": draw_webllm,
    "transformers": draw_transformers,
    "ollama": draw_ollama,
    "rag": draw_rag,
    "gguf": draw_gguf,
}


def build_cover(package_path: Path, output: Path) -> None:
    data = json.loads(package_path.read_text(encoding="utf-8"))
    seed = stable_int(str(data.get("title", "")))
    profile = choose_profile(data)
    colors = PALETTES[profile]
    bg, primary, _, ink, _ = colors
    image = Image.new("RGB", (1200, 630), bg)
    draw = ImageDraw.Draw(image)
    draw_gradient(draw, image.size, bg, "#020617")
    image = paint_premium_background(image, seed, colors)
    draw = ImageDraw.Draw(image)
    for index in range(0, 1200, 60):
        draw.line((index, 0, index - 240, 630), fill="#111827", width=1)
    draw_topic_header(draw, profile, ink, primary)
    SCENES[profile](draw, seed, colors)
    draw.text((970, 568), "unique cover", fill=primary, font=font(18, True))
    image = add_grain(add_vignette(image))
    image = image.filter(ImageFilter.UnsharpMask(radius=1.0, percent=135))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    data["cover_png"] = str(output)
    data["cover_codex"] = str(output)
    data["cover_profile"] = profile
    data["cover_generation_mode"] = "local_topic_preview_fallback"
    package_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a topic-specific Codex bitmap cover for a Tistory package.")
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.package.parent / "cover.codex.png"
    build_cover(args.package, output)
    print(output)


if __name__ == "__main__":
    main()
