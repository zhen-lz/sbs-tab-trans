from typing import Dict
import av
import numpy as np
import os
import tempfile
import shutil


def sbs_to_tab(
    input_path: str,
    output_path: str,
    width: int,
    height: int,
    frames: int,
    split: float,
    progress_callback=None,
) -> None:
    """将SBS格式转换为TAB格式"""

    with av.open(input_path, mode="r") as in_container:
        left_width = int(width * split)
        right_width = width - left_width

        tab_width = max(left_width, right_width)
        tab_height = height * 2

        with av.open(output_path, mode="w") as out_container:
            stream_map = {}

            for in_stream in in_container.streams:
                if in_stream.type == "video":
                    out_stream = out_container.add_stream(
                        codec_name=in_stream.codec_context.codec.name,
                        rate=in_stream.average_rate,
                        options={
                            "width": str(tab_width),
                            "height": str(tab_height),
                            "pix_fmt": str(in_stream.pix_fmt),
                            "bit_rate": str(in_stream.bit_rate),
                            "time_base": str(in_stream.time_base),
                            "bit_rate_tolerance": str(
                                in_stream.codec_context.bit_rate_tolerance
                            ),
                        },
                    )
                elif in_stream.type == "audio":
                    out_stream = out_container.add_stream(
                        codec_name=in_stream.codec_context.codec.name,
                        rate=in_stream.sample_rate,
                        options={
                            "channels": str(in_stream.channels),
                            "layout": str(in_stream.codec_context.layout),
                            "bit_rate": str(in_stream.bit_rate),
                            "time_base": str(in_stream.time_base),
                            "bit_rate_tolerance": str(
                                in_stream.codec_context.bit_rate_tolerance
                            ),
                        },
                    )
                else:
                    out_stream = out_container.add_stream(
                        codec_name=in_stream.codec_context.codec.name,
                        options={
                            "time_base": str(in_stream.time_base),
                        },
                    )
                stream_map[in_stream.index] = out_stream

            processed_frames = 0

            for packet in in_container.demux():
                in_stream_idx = packet.stream.index
                out_stream = stream_map.get(in_stream_idx)
                if out_stream is None:
                    continue

                if packet.stream.type == "video":
                    for frame in packet.decode():
                        if frame.format.name.startswith("yuv"):
                            frame = frame.reformat(width, height, "rgb24")
                        img = frame.to_ndarray()

                        left_part = img[:, :left_width, :]
                        right_part = img[:, left_width:, :]

                        tab_img = np.vstack([left_part, right_part])

                        out_frame = av.VideoFrame.from_ndarray(tab_img, format="rgb24")
                        out_frame = out_frame.reformat(
                            tab_width, tab_height, out_stream.pix_fmt
                        )
                        out_frame.pts = frame.pts
                        out_frame.time_base = frame.time_base

                        for out_packet in out_stream.encode(out_frame):
                            out_packet.stream = out_stream
                            out_container.mux(out_packet)

                        if progress_callback and frames > 0:
                            processed_frames += 1
                            progress = min(processed_frames / frames, 1.0)
                            progress_callback(progress)

                else:
                    packet.stream = out_stream

                    out_container.mux(packet)

            for out_stream in stream_map.values():
                for out_packet in out_stream.encode():
                    out_packet.stream = out_stream
                    out_container.mux(out_packet)


def tab_to_sbs(
    input_path: str,
    output_path: str,
    width: int,
    height: int,
    frames: int,
    split: float,
    progress_callback=None,
) -> None:
    """将SBS格式转换为TAB格式"""

    with av.open(input_path, mode="r") as in_container:
        top_height = int(height * split)
        bottom_height = height - top_height

        tab_width = width * 2
        tab_height = max(top_height, bottom_height)

        with av.open(output_path, mode="w") as out_container:
            stream_map = {}

            for in_stream in in_container.streams:
                if in_stream.type == "video":
                    out_stream = out_container.add_stream(
                        codec_name=in_stream.codec_context.codec.name,
                        rate=in_stream.average_rate,
                        options={
                            "width": str(tab_width),
                            "height": str(tab_height),
                            "pix_fmt": str(in_stream.pix_fmt),
                            "bit_rate": str(in_stream.bit_rate),
                            "time_base": str(in_stream.time_base),
                            "bit_rate_tolerance": str(
                                in_stream.codec_context.bit_rate_tolerance
                            ),
                        },
                    )
                elif in_stream.type == "audio":
                    out_stream = out_container.add_stream(
                        codec_name=in_stream.codec_context.codec.name,
                        rate=in_stream.sample_rate,
                        options={
                            "channels": str(in_stream.channels),
                            "layout": str(in_stream.codec_context.layout),
                            "bit_rate": str(in_stream.bit_rate),
                            "time_base": str(in_stream.time_base),
                            "bit_rate_tolerance": str(
                                in_stream.codec_context.bit_rate_tolerance
                            ),
                        },
                    )
                else:
                    out_stream = out_container.add_stream(
                        codec_name=in_stream.codec_context.codec.name,
                        options={
                            "time_base": str(in_stream.time_base),
                        },
                    )

                stream_map[in_stream.index] = out_stream

            processed_frames = 0

            for packet in in_container.demux():
                in_stream_idx = packet.stream.index
                out_stream = stream_map.get(in_stream_idx)
                if out_stream is None:
                    continue

                if packet.stream.type == "video":
                    for frame in packet.decode():
                        if frame.format.name.startswith("yuv"):
                            frame = frame.reformat(width, height, "rgb24")
                        img = frame.to_ndarray()

                        top_part = img[:top_height, :, :]
                        bottom_part = img[top_height:, :, :]

                        tab_img = np.hstack([top_part, bottom_part])

                        out_frame = av.VideoFrame.from_ndarray(tab_img, format="rgb24")
                        out_frame = out_frame.reformat(
                            tab_width, tab_height, out_stream.pix_fmt
                        )
                        out_frame.pts = frame.pts
                        out_frame.time_base = frame.time_base

                        for out_packet in out_stream.encode(out_frame):
                            out_packet.stream = out_stream
                            out_container.mux(out_packet)

                        if progress_callback and frames > 0:
                            processed_frames += 1
                            progress = min(processed_frames / frames * 100, 100)
                            progress_callback(progress)

                else:
                    packet.stream = out_stream

                    out_container.mux(packet)

            for out_stream in stream_map.values():
                for out_packet in out_stream.encode():
                    out_packet.stream = out_stream
                    out_container.mux(out_packet)
