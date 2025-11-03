import enum
from pathlib import Path
import random
import av
import cv2
import numpy as np
from typing import Tuple, Optional, List
from skimage.metrics import structural_similarity as ssim


class VideoFormat(enum.Enum):
    sbs = "SBS"
    tab = "TAB"
    notsure = "NOT_SURE"


def get_video_format(width: int, height: int) -> VideoFormat:
    """判断视频格式是SBS还是TAB"""
    aspect_ratio = width / height
    sbs_ratios = [
        32 / 9,  # 标准SBS（16:9原始比例分屏）
        16 / 4.5,  # 等效32:9（避免浮点数精度问题）
        2.39 * 2 / 9,  # 宽银幕原始比例（2.39:1）分屏后 ≈2.655
        1.85 * 2 / 9,  # 普通宽银幕（1.85:1）分屏后 ≈2.055
        4 / 3 * 2 / 9 * 9,  # 4:3原始比例分屏后 ≈2.666（兼容旧规格）
    ]
    tab_ratios = [
        16 / 18,  # 标准TAB（16:9原始比例分屏）
        8 / 9,  # 等效16:18（简化比例）
        2.39 / (9 * 2) * 16,  # 宽银幕原始比例（2.39:1）分屏后 ≈1.327
        1.85 / (9 * 2) * 16,  # 普通宽银幕（1.85:1）分屏后 ≈1.027
        4 / 3 / (9 * 2) * 16,  # 4:3原始比例分屏后 ≈1.185（兼容旧规格）
    ]

    def calculate_tolerance(target_ratio: float, actual_ratio: float) -> float:
        ratio_diff = abs(actual_ratio - target_ratio)
        base_tolerance = 0.15
        return min(base_tolerance + (ratio_diff * 0.5), 0.3)

    min_sbs_diff = float("inf")
    for sbs_ratio in sbs_ratios:
        tolerance = calculate_tolerance(sbs_ratio, aspect_ratio)
        diff = abs(aspect_ratio - sbs_ratio)
        if diff <= tolerance and diff < min_sbs_diff:
            min_sbs_diff = diff

    min_tab_diff = float("inf")
    for tab_ratio in tab_ratios:
        tolerance = calculate_tolerance(tab_ratio, aspect_ratio)
        diff = abs(aspect_ratio - tab_ratio)
        if diff <= tolerance and diff < min_tab_diff:
            min_tab_diff = diff

    sbs_candidate = False
    if min_sbs_diff != float("inf") and aspect_ratio >= 2.0:
        sbs_candidate = True

    tab_candidate = False
    if min_tab_diff != float("inf") and 0.6 <= aspect_ratio <= 1.5:
        tab_candidate = True

    if sbs_candidate and tab_candidate:
        if min_sbs_diff < min_tab_diff:
            return VideoFormat.sbs
        elif min_tab_diff < min_sbs_diff:
            return VideoFormat.tab
        else:
            print(f"无法根据宽高比判断视频格式")
            return VideoFormat.notsure
    elif sbs_candidate:
        return VideoFormat.sbs
    elif tab_candidate:
        return VideoFormat.tab
    else:
        print(f"无法根据宽高比判断视频格式")
        return VideoFormat.notsure


def sample_frames(
    video_path: str,
    num_frames: int = 10,
    random_seed: Optional[int] = None,
    middle_ratio: float = 0.8,
) -> List[np.ndarray]:
    """内部函数：用AV抽取帧"""

    if num_frames < 1:
        raise ValueError(f"抽取帧数必须为正数，当前：{num_frames}")
    if not (0 < middle_ratio <= 1):
        raise ValueError(f"中间区域占比必须在(0,1]，当前：{middle_ratio}")

    try:
        with av.open(video_path) as container:
            video_stream = container.streams.video[0]
            total_frames = (
                int(video_stream.duration * video_stream.time_base * video_stream.rate)
                if video_stream.duration and video_stream.time_base
                else 0
            )

            if total_frames <= 0:
                raise ValueError("无法获取视频帧数")

            actual_num = min(num_frames, total_frames)

            edge_ratio = (1 - middle_ratio) / 2
            start = max(0, int(total_frames * edge_ratio))
            end = min(total_frames - 1, int(total_frames * (1 - edge_ratio)))

            if end - start + 1 < actual_num:
                start, end = 0, total_frames - 1

            if random_seed is not None:
                random.seed(random_seed)
            frame_indices = sorted(random.sample(range(start, end + 1), actual_num))

            frames: List[np.ndarray] = []
            frame_idx = 0
            for frame in container.decode(video_stream):
                if frame_idx in frame_indices:
                    img = frame.to_ndarray(format="bgr24")
                    frames.append(img)
                    if len(frames) >= actual_num:
                        break
                frame_idx += 1

            if not frames:
                raise ValueError("AV未成功抽取任何帧")
            return frames

    except Exception as e:
        raise RuntimeError(f"AV抽取帧失败：{str(e)}")


def detect_split_direction_and_position(
    frames: list[np.ndarray], threshold_sim=0.65
) -> Tuple[VideoFormat, float]:
    """检测分割线方向（横向/竖向）及位置比例"""
    if not frames:
        return VideoFormat.notsure, 0

    vertical_candidates = []
    horizontal_candidates = []
    frame_height, frame_width = frames[0].shape[:2]

    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. 检测竖向分割（SBS）：滑动窗口找左右最相似的竖直线
        best_v_sim = -1
        best_v_x = -1

        for x in range(int(frame_width * 0.3), int(frame_width * 0.7)):
            left = gray[:, :x]
            right = gray[:, x:]

            right_resized = cv2.resize(right, (left.shape[1], left.shape[0]))
            sim = ssim(left, right_resized, win_size=11)
            if sim > best_v_sim:  # type: ignore
                best_v_sim = sim
                best_v_x = x

        # 2. 检测横向分割（TB）：滑动窗口找上下最相似的水平线
        best_h_sim = -1
        best_h_y = -1

        for y in range(int(frame_height * 0.3), int(frame_height * 0.7)):
            top = gray[:y, :]
            bottom = gray[y:, :]

            bottom_resized = cv2.resize(bottom, (top.shape[1], top.shape[0]))
            sim = ssim(top, bottom_resized, win_size=11)
            if sim > best_h_sim:  # type: ignore
                best_h_sim = sim
                best_h_y = y

        if best_v_sim > threshold_sim:  # type: ignore
            vertical_candidates.append(best_v_x)
        if best_h_sim > threshold_sim:  # type: ignore
            horizontal_candidates.append(best_h_y)

    if len(vertical_candidates) > len(horizontal_candidates):
        avg_x = np.mean(vertical_candidates)
        ratio = avg_x / frame_width
        return VideoFormat.sbs, float(round(ratio, 1))
    elif len(horizontal_candidates) > len(vertical_candidates):
        avg_y = np.mean(horizontal_candidates)
        ratio = avg_y / frame_height
        return VideoFormat.tab, float(round(ratio, 1))
    else:
        return VideoFormat.notsure, 0


def get_video_info(
    input_path: str,
) -> Tuple[int, int, int]:
    """内部函数：通过AV获取视频信息"""

    container = None
    try:
        container = av.open(input_path)
        video_stream = next(
            (stream for stream in container.streams if stream.type == "video"), None
        )
        if not video_stream:
            raise RuntimeError("视频无有效视频流，无法获取信息")

        codec_ctx = video_stream.codec_context
        if not codec_ctx:
            raise RuntimeError("无法获取视频流的编码器上下文")

        width = codec_ctx.width  # type: ignore
        height = codec_ctx.height  # type: ignore
        total_frames = 100

        if video_stream.frames > 0:
            total_frames = video_stream.frames

        return width, height, total_frames

    except Exception as e:
        raise RuntimeError(f"AV获取视频信息失败：{str(e)}")
    finally:
        if container is not None:
            try:
                container.close()
            except Exception:
                pass
