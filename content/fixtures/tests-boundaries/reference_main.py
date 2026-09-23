"""P4 参考：文件流程入口。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reference_solution import count_words, format_report


def main(input_path="input.txt", output_path="report.txt"):
    try:
        with Path(input_path).open(encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print("输入文件不存在：" + Path(input_path).name)
        return
    except UnicodeDecodeError:
        print("输入文件不是有效的 UTF-8 编码，已保留旧报告。")
        return
    except OSError:
        print("读取输入文件失败，已保留旧报告。")
        return
    report = format_report(count_words(text))
    try:
        with Path(output_path).open("w", encoding="utf-8") as f:
            f.write(report)
    except OSError:
        print("写入报告失败：报告可能不完整，请检查输出文件。")
        return
    print("报告已生成：" + Path(output_path).name)


if __name__ == "__main__":
    main()
