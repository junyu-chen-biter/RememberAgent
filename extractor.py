import json
from pypdf import PdfReader

from llm_client import chat_json

def read_pdf(file):
    """
    从 PDF 文件对象中读取文本内容。
    """
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def read_markdown(file):
    """
    从上传的 Markdown / 文本文件中读取内容。
    """
    content = file.read()
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8")
        except Exception:
            content = content.decode("utf-8", errors="ignore")
    return content


def read_document(file):
    """
    支持 PDF 与 Markdown 等文本格式的统一读取入口。
    会根据 MIME type 和文件扩展名自动判断。
    """
    file_name = getattr(file, "name", "") or ""
    file_type = getattr(file, "type", "") or ""
    lower_name = file_name.lower()

    # 优先判断 PDF
    if "pdf" in file_type or lower_name.endswith(".pdf"):
        return read_pdf(file)

    # 其他情况按 Markdown/纯文本处理
    return read_markdown(file)


def _summarize_to_points(raw_text: str):
    """
    第一步：将原始长文本整理为「条目化的知识点列表」。
    返回一个字符串列表，每个元素是一条独立的知识点描述。
    """
    try:
        data = chat_json(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个擅长整理教材的助教。"
                        "现在给你一大段原始教材内容，请你把它整理成一系列「知识点条目」。"
                        "每个知识点条目应该是完整的一句话或几句话，表达一个清晰的概念、结论或规则，"
                        "避免太碎或者太长。"
                        "请以 JSON 对象形式返回，结构为："
                        "{'points': ['知识点1', '知识点2', ...]}。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "请从下面的教材内容中，提炼出尽量完整、清晰的知识点条目：\n\n"
                        f"{raw_text[:15000]}"
                    ),
                },
            ],
        )

        if isinstance(data, dict) and "points" in data and isinstance(
            data["points"], list
        ):
            # 只保留非空字符串
            return [str(p).strip() for p in data["points"] if str(p).strip()]

        # Fallback：如果模型没按 points 返回，但给了列表
        if isinstance(data, dict):
            for _, value in data.items():
                if isinstance(value, list):
                    return [str(p).strip() for p in value if str(p).strip()]

        return []

    except Exception as e:
        print(f"Error summarizing to points: {e}")
        return []

def extract_knowledge(text):
    """
    两步法提取可作为背记点的“挖空题”：
    1）先把原始长文本整理为「知识点条目列表」；
    2）再基于这些条目，生成挖空题。
    返回格式为 [{'q': '挖空后的句子（包含 ____）', 'a': '被挖掉的知识点'}, ...]
    """
    # 第一步：长文本 → 知识点条目
    points = _summarize_to_points(text)
    if not points:
        return []

    # 将知识点条目整理成编号列表，方便模型理解
    points_text = "\n".join(f"{idx + 1}. {p}" for idx, p in enumerate(points))

    try:
        data = chat_json(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个助教，负责为学生生成背诵用的填空题（挖空题）。"
                        "现在给你的是已经整理好的「知识点条目列表」，而不是原始教材。"
                        "请在这些条目中识别出最适合作为记忆/背诵的关键片段（术语、概念、结论、公式中的关键部分等），"
                        "对每个知识点条目进行适度的挖空："
                        "1）保证每道题只有真正需要背记的关键部分被替换为连续的下划线 '____'；"
                        "2）上下文尽量保留原句，便于学生通过语境回忆；"
                        "3）返回 JSON 对象，其中有一个键为 'knowledge_points'，"
                        "   值是列表，列表中的每个元素为对象："
                        "   {'q': '挖空后的句子（包含 ____）', 'a': '被挖掉的知识点原文'}。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "下面是根据教材整理出的知识点条目列表，请你在这些条目基础上生成若干条挖空题：\n\n"
                        f"{points_text}"
                    ),
                },
            ],
        )

        if isinstance(data, dict) and "knowledge_points" in data:
            return data["knowledge_points"]

        # Fallback: 如果模型没有用指定的 key，但仍然返回了列表，则直接使用
        if isinstance(data, dict):
            for _, value in data.items():
                if isinstance(value, list):
                    return value

        return []

    except Exception as e:
        print(f"Error extracting knowledge: {e}")
        return []
