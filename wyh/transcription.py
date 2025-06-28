import re

def rewrite_text(text: str) -> str:
    # 移除 emoji（匹配常见 emoji 字符范围）
    emoji_pattern = re.compile(
        "[" 
        "\U0001F600-\U0001F64F"  # 表情符号
        "\U0001F300-\U0001F5FF"  # 符号和图形
        "\U0001F680-\U0001F6FF"  # 交通工具和地图
        "\U0001F1E0-\U0001F1FF"  # 旗帜
        "\U00002700-\U000027BF"  # 杂项符号
        "\U0001F900-\U0001F9FF"  # 补充符号
        "\U00002600-\U000026FF"  # 各种符号
        "\U00002500-\U00002BEF"  # 汉字部件与符号扩展
        "]+", 
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)

    # 处理 markdown 链接 [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # 移除粗体、斜体、删除线等：**text**、*text*、__text__、_text_、~~text~~
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)
    text = re.sub(r'~~(.*?)~~', r'\1', text)

    # 移除标题（# 开头）
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # 移除引用（> 开头）
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # 移除无序/有序列表项符号
    text = re.sub(r'^\s*([-*+]|\d+\.)\s+', '', text, flags=re.MULTILINE)

    # 移除代码块 ``` 和行内代码 `
    text = re.sub(r'```[\s\S]*?```', '', text)  # 多行代码块
    text = re.sub(r'`([^`]*)`', r'\1', text)    # 行内代码

    # 去除多余空白行和空格
    text = re.sub(r'\n{2,}', '\n', text).strip()

    return text


if __name__ == "__main__":
    # 测试基本文本
    print("测试1 - 基本文本:")
    print(rewrite_text("你好,我是小新智能体,期待与你对话"))
    print()

    # 测试 emoji 移除
    print("测试2 - Emoji 移除:")
    print(rewrite_text("你好👋，我是小新智能体🤖，很高兴见到你😊"))
    print()

    # 测试 markdown 格式
    print("测试3 - Markdown 格式:")
    print(rewrite_text("**粗体文本** 和 *斜体文本* 以及 ~~删除线~~"))
    print()

    # 测试链接
    print("测试4 - Markdown 链接:")
    print(rewrite_text("这是一个[链接文本](https://example.com)的测试"))
    print()

    # 测试标题和引用
    print("测试5 - 标题和引用:")
    print(rewrite_text("# 一级标题\n> 这是一段引用文本\n## 二级标题"))
    print()

    # 测试列表
    print("测试6 - 列表:")
    print(rewrite_text("- 无序列表项1\n- 无序列表项2\n1. 有序列表项1\n2. 有序列表项2"))
    print()

    # 测试代码块
    print("测试7 - 代码块:")
    print(rewrite_text("这是`行内代码`和\n```\n多行代码块\n```"))
    print()

    # 测试组合场景
    print("测试8 - 组合场景:")
    print(rewrite_text("# 标题\n> 引用中的**粗体**和[链接](url)\n- 列表项中的`代码`和😊表情"))