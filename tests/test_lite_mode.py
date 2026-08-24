"""
测试 lite 模式（轻量自学模式）
覆盖 LiteModeManager 参数解析、模式判断与服务开关
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.lite_mode import LiteModeManager

# ------------------------------------------------------------
# 学生端学习平台 lite 模式渲染测试准备（保持完全离线）
# 1) 先把数据库指向系统临时目录，避免 import goai_web 时在项目根创建 lumilearn.db
# 2) goai_web 模块顶层会实例化 LumiLearnAgent 并探测 Ollama（requests.get），
#    用 mock 阻断外部网络调用
if "LUMILEARN_DB_PATH" not in os.environ:
    os.environ["LUMILEARN_DB_PATH"] = os.path.join(
        tempfile.gettempdir(), "lumilearn_test_lite_mode.db")

with mock.patch("requests.get", side_effect=ConnectionError("offline")):
    from goai_web import app  # noqa: E402


class TestLiteMode(unittest.TestCase):
    """LiteModeManager 单元测试"""

    def test_parse_args_lite(self):
        """--mode lite → "lite" """
        manager = LiteModeManager()
        self.assertEqual(manager.parse_args(["--mode", "lite"]), "lite")

    def test_parse_args_default(self):
        """无参数 → "" """
        manager = LiteModeManager()
        self.assertEqual(manager.parse_args([]), "")

    def test_is_lite(self):
        """LiteModeManager("lite").is_lite() == True"""
        self.assertTrue(LiteModeManager("lite").is_lite())
        self.assertFalse(LiteModeManager("").is_lite())
        self.assertFalse(LiteModeManager("full").is_lite())

    def test_get_enabled_services_lite(self):
        """lite 下仅核心服务 enabled"""
        port_settings = {
            "terminal": {"enabled": True, "port": 18080},
            "api": {"enabled": True, "port": 18081},
            "models": {"enabled": True, "port": 18082},
            "goai_web": {"enabled": True, "port": 5000},
            "teacher_portal": {"enabled": True, "port": 5001},
            "student_portal": {"enabled": True, "port": 5010},
            "analytics_dashboard": {"enabled": True, "port": 18090},
        }
        result = LiteModeManager("lite").get_enabled_services(port_settings)
        core = ("terminal", "api", "student_portal")
        for name, cfg in result.items():
            if name in core:
                self.assertTrue(cfg["enabled"], f"{name} 应为核心服务（enabled=True）")
            else:
                self.assertFalse(cfg["enabled"], f"{name} 在 lite 模式应关闭（enabled=False）")
            # 端口等其余字段保持不变
            self.assertEqual(cfg["port"], port_settings[name]["port"])

    def test_get_enabled_services_full(self):
        """默认模式全 enabled"""
        port_settings = {
            "terminal": {"enabled": True, "port": 18080},
            "api": {"enabled": True, "port": 18081},
            "models": {"enabled": True, "port": 18082},
            "goai_web": {"enabled": True, "port": 5000},
            "teacher_portal": {"enabled": True, "port": 5001},
            "student_portal": {"enabled": True, "port": 5010},
            "analytics_dashboard": {"enabled": True, "port": 18090},
        }
        result = LiteModeManager().get_enabled_services(port_settings)
        for name, cfg in result.items():
            self.assertTrue(cfg["enabled"], f"{name} 默认模式应启用")


class TestLiteModeDashboard(unittest.TestCase):
    """学习平台首页 lite / 完整模式渲染差异（Flask test client，不启动真实服务）"""

    def setUp(self):
        self.client = app.test_client()
        self._orig_lite_mode = app.config.get("LITE_MODE")

    def tearDown(self):
        # 恢复 LITE_MODE 配置，避免测试间相互影响
        if self._orig_lite_mode is None:
            app.config.pop("LITE_MODE", None)
        else:
            app.config["LITE_MODE"] = self._orig_lite_mode

    def test_dashboard_lite_hides_quick_links(self):
        """LITE_MODE=True：隐藏「快速参考」，显示「轻量自学模式」"""
        app.config["LITE_MODE"] = True
        with mock.patch("goai_web.check_port", return_value=False):
            resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertNotIn("快速参考", body)
        self.assertIn("轻量自学模式", body)

    def test_dashboard_full_shows_quick_links(self):
        """LITE_MODE=False（或未设置）：显示「快速参考」"""
        app.config.pop("LITE_MODE", None)
        with mock.patch("goai_web.check_port", return_value=False):
            resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("快速参考", body)


if __name__ == "__main__":
    unittest.main()
