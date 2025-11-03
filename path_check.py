import os


def validate_input_path(path: str) -> str:
    """验证输入文件有效性"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"输入文件不存在: {path}")
    if not os.path.isfile(path):
        raise IsADirectoryError(f"输入路径不是文件: {path}")
    if not os.access(path, os.R_OK):
        raise PermissionError(f"没有读取文件的权限: {path}")
    return path


def validate_output_dir(path: str) -> str:
    """验证输出目录有效性"""
    dir_path = os.path.dirname(path)
    if not dir_path:
        dir_path = os.getcwd()

    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
        except PermissionError:
            raise PermissionError(f"没有创建目录的权限: {dir_path}")

    if not os.access(dir_path, os.W_OK):
        raise PermissionError(f"没有写入目录的权限: {dir_path}")

    return path
