#!/usr/bin/env python3
"""
PPT生成器
使用 Grsai Nano Banana API 基于文档内容生成PPT图片
"""

import os
import sys
import json
import argparse
import time
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


def find_and_load_env():
    """
    智能查找并加载 .env 文件
    优先级：
    1. 当前脚本所在目录
    2. 向上查找到项目根目录（包含 .git 或 .env 的目录）
    3. 用户主目录下的 .claude/skills/ppt-generator/
    """
    current_dir = Path(__file__).parent

    # 1. 尝试当前目录
    if (current_dir / ".env").exists():
        load_dotenv(current_dir / ".env", override=True)
        print(f"✅ 已加载环境变量: {current_dir / '.env'}")
        return True

    # 2. 向上查找到项目根目录
    for parent in current_dir.parents:
        env_path = parent / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)
            print(f"✅ 已加载环境变量: {env_path}")
            return True
        # 如果找到 .git 目录，说明到达项目根目录
        if (parent / ".git").exists():
            break

    # 3. 尝试 Claude Code Skill 标准位置
    claude_skill_env = Path.home() / ".claude" / "skills" / "ppt-generator" / ".env"
    if claude_skill_env.exists():
        load_dotenv(claude_skill_env, override=True)
        print(f"✅ 已加载环境变量: {claude_skill_env}")
        return True

    # 如果都没找到，尝试默认加载（可能从系统环境变量获取）
    load_dotenv(override=True)
    print("⚠️  未找到 .env 文件，尝试使用系统环境变量")
    return False


# 智能加载环境变量
find_and_load_env()


def load_style_template(style_path):
    """加载风格模板"""
    with open(style_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取基础提示词模板部分
    start_marker = "## 基础提示词模板"
    end_marker = "## 页面类型模板"

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        print("警告: 无法解析风格模板，使用完整文件内容")
        return content

    template = content[start_idx + len(start_marker):end_idx].strip()
    return template


def generate_prompt(style_template, page_type, content_text, slide_number, total_slides):
    """生成单页提示词"""
    prompt = f"{style_template}\n\n"

    if page_type == "cover" or slide_number == 1:
        # 封面页
        prompt += f"""请根据视觉平衡美学，生成封面页。在中心放置一个巨大的复杂3D玻璃物体，并覆盖粗体大字：

{content_text}

背景有延伸的极光波浪。"""

    elif page_type == "data" or slide_number == total_slides:
        # 数据页/总结页
        prompt += f"""请生成数据页或总结页。使用分屏设计，左侧排版以下文字，右侧悬浮巨大的发光3D数据可视化图表：

{content_text}"""

    else:
        # 内容页
        prompt += f"""请生成内容页。使用Bento网格布局，将以下内容组织在模块化的圆角矩形容器中，容器材质必须是带有模糊效果的磨砂玻璃：

{content_text}"""

    return prompt


def generate_slide(prompt, slide_number, output_dir, resolution="2K"):
    """生成单页PPT图片（使用 Grsai Nano Banana API）"""

    # 获取API密钥
    api_key = os.environ.get("GRSAI_API_KEY")
    if not api_key:
        print("错误: 未设置 GRSAI_API_KEY 环境变量")
        print("请在 .env 文件中设置: GRSAI_API_KEY=your-api-key")
        sys.exit(1)

    # API 配置
    host = os.environ.get("GRSAI_HOST", "https://grsai.dakka.com.cn")
    model = os.environ.get("GRSAI_MODEL", "nano-banana-pro")
    url = f"{host}/v1/draw/nano-banana"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "aspectRatio": "16:9",
        "imageSize": resolution
    }

    print(f"正在生成第 {slide_number} 页...")

    try:
        # 发送请求（使用流式响应，等待完成）
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=300)
        response.raise_for_status()

        # 解析 SSE 流式响应
        image_url = None
        error_msg = None
        last_progress = 0

        for line in response.iter_lines():
            if not line:
                continue

            # 解码行
            line_text = line.decode('utf-8').strip()

            # SSE 格式：每行以 "data: " 开头
            if line_text.startswith('data: '):
                json_str = line_text[6:]  # 去掉 "data: " 前缀
            else:
                json_str = line_text

            if not json_str:
                continue

            try:
                data = json.loads(json_str)

                # 获取进度
                progress = data.get("progress", 0)
                status = data.get("status", "")

                # 打印进度
                if progress > last_progress:
                    print(f"  进度: {progress}%", end='\r')
                    last_progress = progress

                # 检查是否完成
                if status == "succeeded" or progress == 100:
                    results = data.get("results", [])
                    if results and len(results) > 0:
                        image_url = results[0].get("url")
                    print()  # 换行
                    break
                elif status == "failed":
                    error_msg = data.get("error", "") or data.get("failure_reason", "未知错误")
                    print()  # 换行
                    break

            except json.JSONDecodeError:
                continue

        if not image_url:
            error_detail = error_msg or "未收到图片数据"
            print(f"✗ 第 {slide_number} 页生成失败: {error_detail}")
            return None

        # 下载图片
        image_path = os.path.join(output_dir, "images", f"slide-{slide_number:02d}.png")
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()

        with open(image_path, 'wb') as f:
            f.write(img_response.content)

        print(f"✓ 第 {slide_number} 页已保存: {image_path}")
        return image_path

    except requests.exceptions.Timeout:
        print(f"✗ 第 {slide_number} 页生成失败: 请求超时")
        return None
    except requests.exceptions.RequestException as e:
        print(f"✗ 第 {slide_number} 页生成失败: 网络错误 - {e}")
        return None
    except Exception as e:
        print(f"✗ 第 {slide_number} 页生成失败: {e}")
        return None


def generate_viewer_html(output_dir, slide_count, template_path):
    """生成播放网页"""
    # 读取HTML模板
    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()

    # 生成图片列表
    slides_list = [f"'images/slide-{i:02d}.png'" for i in range(1, slide_count + 1)]

    # 替换占位符
    html_content = html_template.replace(
        "/* IMAGE_LIST_PLACEHOLDER */",
        ",\n            ".join(slides_list)
    )

    # 保存HTML文件
    html_path = os.path.join(output_dir, "index.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✓ 播放网页已生成: {html_path}")
    return html_path


def save_prompts(output_dir, prompts_data):
    """保存所有提示词到JSON文件"""
    prompts_path = os.path.join(output_dir, "prompts.json")
    with open(prompts_path, 'w', encoding='utf-8') as f:
        json.dump(prompts_data, f, ensure_ascii=False, indent=2)
    print(f"✓ 提示词已保存: {prompts_path}")


def main():
    parser = argparse.ArgumentParser(
        description='PPT生成器 - 使用 Grsai Nano Banana API 生成PPT图片',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python generate_ppt.py --plan slides_plan.json --style styles/gradient-glass.md --resolution 2K

环境变量:
  GRSAI_API_KEY: Grsai API密钥（必需）
  GRSAI_HOST: API主机地址（可选，默认: https://grsai.dakka.com.cn）
  GRSAI_MODEL: 模型名称（可选，默认: nano-banana-pro）
"""
    )

    parser.add_argument(
        '--plan',
        required=True,
        help='slides规划JSON文件路径（由Skill生成）'
    )
    parser.add_argument(
        '--style',
        required=True,
        help='风格模板文件路径'
    )
    parser.add_argument(
        '--resolution',
        choices=['2K', '4K'],
        default='2K',
        help='图片分辨率 (默认: 2K)'
    )
    parser.add_argument(
        '--output',
        help='输出目录路径（默认: outputs/TIMESTAMP）'
    )
    parser.add_argument(
        '--template',
        default='templates/viewer.html',
        help='HTML模板路径（默认: templates/viewer.html）'
    )

    args = parser.parse_args()

    # 读取slides规划
    with open(args.plan, 'r', encoding='utf-8') as f:
        slides_plan = json.load(f)

    # 加载风格模板
    style_template = load_style_template(args.style)

    # 创建输出目录
    if args.output:
        output_dir = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"outputs/{timestamp}"

    os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)

    print("=" * 60)
    print("PPT生成器启动")
    print("=" * 60)
    print(f"风格: {args.style}")
    print(f"分辨率: {args.resolution}")
    print(f"页数: {len(slides_plan['slides'])}")
    print(f"输出目录: {output_dir}")
    print("=" * 60)
    print()

    # 生成每一页
    prompts_data = {
        "metadata": {
            "title": slides_plan.get("title", "未命名演示"),
            "total_slides": len(slides_plan['slides']),
            "resolution": args.resolution,
            "style": args.style,
            "generated_at": datetime.now().isoformat()
        },
        "slides": []
    }

    total_slides = len(slides_plan['slides'])

    # 统计信息
    success_count = 0
    failed_slides = []

    for idx, slide_info in enumerate(slides_plan['slides']):
        slide_number = slide_info['slide_number']
        page_type = slide_info.get('page_type', 'content')
        content_text = slide_info['content']

        # 生成提示词
        prompt = generate_prompt(
            style_template,
            page_type,
            content_text,
            slide_number,
            total_slides
        )

        # 生成图片
        image_path = generate_slide(prompt, slide_number, output_dir, args.resolution)

        # 统计结果
        if image_path:
            success_count += 1
        else:
            failed_slides.append(slide_number)

        # 记录提示词
        prompts_data['slides'].append({
            "slide_number": slide_number,
            "page_type": page_type,
            "content": content_text,
            "prompt": prompt,
            "image_path": image_path
        })

        # 调用间隔：如果不是最后一张，等待3秒
        if idx < len(slides_plan['slides']) - 1:
            print("等待 3 秒后继续...")
            time.sleep(3)

        print()

    # 保存提示词
    save_prompts(output_dir, prompts_data)

    # 生成播放网页
    generate_viewer_html(output_dir, total_slides, args.template)

    print()
    print("=" * 60)
    print("生成完成！")
    print("=" * 60)
    print(f"成功: {success_count}/{total_slides} 页")
    if failed_slides:
        print(f"失败: {len(failed_slides)} 页")
        print(f"失败列表: 第 {', '.join(map(str, failed_slides))} 页")
    print()
    print(f"输出目录: {output_dir}")
    print(f"播放网页: {os.path.join(output_dir, 'index.html')}")
    print()
    print("打开播放网页查看PPT:")
    print(f"  open {os.path.join(output_dir, 'index.html')}")
    print()


if __name__ == "__main__":
    main()
