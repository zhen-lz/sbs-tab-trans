import os
import sys
import av
import cv2
import argparse

import transformer_av
import path_check
import video_info


def test_open(file_path: str) -> bool:
    """测试文件能否被 av 打开"""

    container = None
    try:
        container = av.open(file_path, mode="r")

        video_stream = next(
            (stream for stream in container.streams if stream.type == "video"), None
        )
        if not video_stream:
            print(f"警告：文件{file_path}无有效视频流")
            return False

        if not video_stream.codec_context:
            print(f"警告：文件{file_path}无法获取编码器上下文，无法解码")
            return False

        return True

    except Exception as e:
        print(f"失败：处理文件{file_path}时发生未知错误 - {str(e)}")
        return False
    finally:
        if container is not None:
            try:
                container.close()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="3D视频格式转换器：支持SBS与TAB互相转换"
    )

    parser.add_argument("input", help="输入视频文件路径")

    parser.add_argument("-o", "--output", help="输出视频文件路径")

    parser.add_argument(
        "-m",
        "--mode",
        choices=["sbs2tab", "tab2sbs"],
        help="转换模式：sbs2tab(SBS转TAB) 或 tab2sbs(TAB转SBS)",
    )

    parser.add_argument(
        "-a",
        "--autodetect-nonstandard",
        action="store_true",
        help="启用非标准分割线检测（适用于非对称分割的视频）",
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细转换进度")

    args = parser.parse_args()
    # args = parser.parse_args(["test.mp4", "-m", "sbs2tab"])  # 测试用

    try:
        input_path = path_check.validate_input_path(args.input)

        if not args.output:
            input_dir = os.path.dirname(args.input)
            input_name = os.path.basename(args.input)
            name, ext = os.path.splitext(input_name)
            default_output = os.path.join(input_dir, f"{name}_converted{ext}")
            args.output = default_output
        output_path = path_check.validate_output_dir(args.output)

        if os.path.abspath(input_path) == os.path.abspath(output_path):
            raise ValueError("输入文件和输出文件不能相同")

        def progress_callback(percent: float) -> None:
            if args.verbose:
                print(f"转换进度: {percent:.1f}%", end="\r", file=sys.stderr)

        width, height, total_frames = video_info.get_video_info(input_path)

        if not args.mode:
            detected_format = video_info.get_video_format(width, height)
            if detected_format == video_info.VideoFormat.sbs:
                args.mode = "sbs2tab"
            elif detected_format == video_info.VideoFormat.tab:
                args.mode = "tab2sbs"
            else:
                args.autodetect_nonstandard = True

        split = 0.5
        if args.autodetect_nonstandard and not args.mode:
            frames = video_info.sample_frames(input_path)
            format, split = video_info.detect_split_direction_and_position(frames)
            if format is video_info.VideoFormat.sbs:
                args.mode = "sbs2tab"
            elif format is video_info.VideoFormat.tab:
                args.mode = "tab2sbs"

        if not args.mode:
            raise ValueError("无法自动检测视频格式，请手动指定转换模式（--mode）")

        if args.mode == "sbs2tab":
            transformer_av.sbs_to_tab(
                input_path,
                output_path,
                width,
                height,
                total_frames,
                split,
                progress_callback if args.verbose else None,
            )
        else:
            transformer_av.tab_to_sbs(
                input_path,
                output_path,
                width,
                height,
                total_frames,
                split,
                progress_callback if args.verbose else None,
            )

        print(f"\n转换完成！输出文件: {output_path}", file=sys.stderr)

    except Exception as e:
        print(f"转换失败: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
