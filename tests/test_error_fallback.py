#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试异常降级通用机制 framework/core/fallback.py（FallbackHandler）

覆盖：
  - safe_json_parse：合法 JSON / markdown 包裹 / 无效 JSON
  - run_with_fallback：成功 / 异常降级（友好提示，不崩溃）/ JSONDecodeError 重试
  - friendly_message：友好提示不包含 Traceback 等堆栈信息

完全离线可运行：仅依赖标准库。
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.core.fallback import FallbackHandler


class TestSafeJsonParse(unittest.TestCase):
    """safe_json_parse 安全解析测试"""

    def setUp(self):
        self.handler = FallbackHandler()

    def test_safe_json_parse_valid(self):
        data, err = self.handler.safe_json_parse('{"topic": "函数", "level": 3}')
        self.assertIsNone(err)
        self.assertEqual(data["topic"], "函数")
        self.assertEqual(data["level"], 3)

    def test_safe_json_parse_markdown_wrapped(self):
        raw = '```json\n{"topic": "牛顿第二定律", "ok": true}\n```'
        data, err = self.handler.safe_json_parse(raw)
        self.assertIsNone(err)
        self.assertEqual(data["topic"], "牛顿第二定律")
        self.assertTrue(data["ok"])

    def test_safe_json_parse_invalid(self):
        data, err = self.handler.safe_json_parse("这不是 JSON { 内容")
        self.assertIsNone(data)
        self.assertIsNotNone(err)
        self.assertIn("JSON", err)
        self.assertNotIn("Traceback", err)


class TestRunWithFallback(unittest.TestCase):
    """run_with_fallback 降级执行测试"""

    def setUp(self):
        self.handler = FallbackHandler()

    def test_run_with_fallback_success(self):
        result, err = self.handler.run_with_fallback(
            lambda topic: {"topic": topic, "ok": True}, topic="勾股定理")
        self.assertIsNone(err)
        self.assertTrue(result["ok"])
        self.assertEqual(result["topic"], "勾股定理")

    def test_run_with_fallback_error(self):
        def boom():
            raise TimeoutError("model timed out after 60s")

        result, err = self.handler.run_with_fallback(boom)
        self.assertIsNone(result)
        self.assertIsNotNone(err)
        # 返回友好提示而非抛异常，且不泄露堆栈
        self.assertIn("超时", err)
        self.assertNotIn("Traceback", err)

    def test_run_with_fallback_json_decode_retry(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise json.JSONDecodeError("Expecting value", "{bad", 0)
            return {"ok": True}

        result, err = self.handler.run_with_fallback(flaky, max_retries=2)
        self.assertIsNone(err)
        self.assertTrue(result["ok"])
        self.assertEqual(calls["n"], 2)  # 失败 1 次后重试成功


class TestFriendlyMessage(unittest.TestCase):
    """friendly_message 友好提示测试"""

    def test_friendly_message_contains_no_stacktrace(self):
        handler = FallbackHandler()
        for err_type in ("JSONDecodeError", "TimeoutError", "ConnectionError",
                         "ValueError", "KeyError", "UnknownError"):
            msg = handler.friendly_message(err_type)
            self.assertTrue(msg)  # 非空
            for banned in ("Traceback", "File \"", "line ", "raise ", " at "):
                self.assertNotIn(banned, msg,
                                 f"{err_type} 的提示不应包含 {banned!r}: {msg}")


if __name__ == "__main__":
    unittest.main()
