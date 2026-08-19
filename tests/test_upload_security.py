# -*- coding: utf-8 -*-
"""文件上传安全校验测试（M-7）

覆盖：路径穿越、非法扩展名、空文件名、超大小、伪造扩展名（魔数不符）、
服务层 recognize_file/transcribe_file 的校验拒绝路径（不触发模型加载）。
"""
import os
import sys
import tempfile
import unittest
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.datastructures import FileStorage

from framework.security.uploads import (
    validate_upload_file, check_file_magic,
    ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES,
    ALLOWED_AUDIO_EXTENSIONS, MAX_AUDIO_BYTES,
)
from framework.services.ocr_service import get_ocr_service
from framework.services.speech_service import get_speech_service

PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
PHP_PAYLOAD = b"<?php system($_GET['c']); ?>"


def _fs(data: bytes, filename: str) -> FileStorage:
    fs = FileStorage(stream=BytesIO(data), filename=filename)
    try:
        fs.content_length = len(data)
    except Exception:
        pass
    return fs


class TestValidateUploadFile(unittest.TestCase):
    def test_valid_png_passes(self):
        ok, err = validate_upload_file(_fs(PNG_HEADER, "photo.png"),
                                       ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
        self.assertTrue(ok, err)

    def test_valid_wav_passes(self):
        ok, err = validate_upload_file(_fs(b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 20, "voice.wav"),
                                       ALLOWED_AUDIO_EXTENSIONS, MAX_AUDIO_BYTES)
        self.assertTrue(ok, err)

    def test_none_file_rejected(self):
        ok, err = validate_upload_file(None, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
        self.assertFalse(ok)
        self.assertIn("未收到文件", err)

    def test_empty_filename_rejected(self):
        ok, err = validate_upload_file(_fs(b"x", ""), ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
        self.assertFalse(ok)

    def test_path_traversal_rejected(self):
        for name in ["../../etc/passwd", "..\\..\\secret.png", "a/b.png", "a\\b.png"]:
            ok, err = validate_upload_file(_fs(b"x", name),
                                           ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
            self.assertFalse(ok, f"应拒绝路径穿越: {name}")

    def test_bad_extension_rejected(self):
        for name in ["shell.php", "evil.exe", "note.txt", "x.py"]:
            ok, err = validate_upload_file(_fs(b"x", name),
                                           ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
            self.assertFalse(ok, f"应拒绝非法扩展名: {name}")

    def test_no_extension_rejected(self):
        ok, err = validate_upload_file(_fs(b"x", "README"), ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
        self.assertFalse(ok)

    def test_oversize_rejected(self):
        # content_length 属性只读（由 stream 计算），用超大流直接构造
        fs = FileStorage(stream=BytesIO(b"x" * (MAX_IMAGE_BYTES + 1)), filename="big.png")
        ok, err = validate_upload_file(fs, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
        self.assertFalse(ok)
        self.assertIn("过大", err)


class TestCheckFileMagic(unittest.TestCase):
    def _tmp(self, data: bytes, ext: str) -> str:
        f = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        f.write(data)
        f.close()
        return f.name

    def test_valid_png_magic(self):
        path = self._tmp(PNG_HEADER, ".png")
        try:
            self.assertTrue(check_file_magic(path, ".png"))
        finally:
            os.unlink(path)

    def test_php_disguised_as_png_rejected(self):
        path = self._tmp(PHP_PAYLOAD, ".png")
        try:
            self.assertFalse(check_file_magic(path, ".png"))
        finally:
            os.unlink(path)

    def test_php_disguised_as_mp3_rejected(self):
        path = self._tmp(PHP_PAYLOAD, ".mp3")
        try:
            self.assertFalse(check_file_magic(path, ".mp3"))
        finally:
            os.unlink(path)

    def test_wav_and_webp_riff_differentiated(self):
        wav = self._tmp(b"RIFF\x00\x00\x00\x00WAVEfmt ", ".wav")
        webp = self._tmp(b"RIFF\x00\x00\x00\x00WEBPVP8 ", ".webp")
        try:
            self.assertTrue(check_file_magic(wav, ".wav"))
            self.assertFalse(check_file_magic(wav, ".webp"), "WAV 不应被当作 WEBP")
            self.assertTrue(check_file_magic(webp, ".webp"))
            self.assertFalse(check_file_magic(webp, ".wav"), "WEBP 不应被当作 WAV")
        finally:
            os.unlink(wav)
            os.unlink(webp)

    def test_m4a_skipped(self):
        path = self._tmp(b"not-a-real-format", ".m4a")
        try:
            self.assertTrue(check_file_magic(path, ".m4a"), "m4a 无固定魔数，应跳过")
        finally:
            os.unlink(path)


class TestServiceFileGuards(unittest.TestCase):
    """服务层校验拒绝路径（不触发模型加载：校验在模型调用前完成）"""

    def test_ocr_rejects_php_disguised_as_png(self):
        svc = get_ocr_service()
        with self.assertRaises(ValueError):
            svc.recognize_file(_fs(PHP_PAYLOAD, "evil.png"))

    def test_ocr_rejects_path_traversal(self):
        svc = get_ocr_service()
        with self.assertRaises(ValueError):
            svc.recognize_file(_fs(PNG_HEADER, "../../evil.png"))

    def test_ocr_rejects_bad_extension(self):
        svc = get_ocr_service()
        with self.assertRaises(ValueError):
            svc.recognize_file(_fs(PNG_HEADER, "evil.php"))

    def test_speech_rejects_php_disguised_as_mp3(self):
        svc = get_speech_service()
        with self.assertRaises(ValueError):
            svc.transcribe_file(_fs(PHP_PAYLOAD, "evil.mp3"))


if __name__ == "__main__":
    unittest.main()
