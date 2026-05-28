"""
LumiLearn 直播助手 - 抖音/斗鱼/快手 弹幕 AI 互动系统
AI 角色"小澍"实时回复直播间弹幕

依赖安装:
  pip install websocket-client requests pyaudio gtts Pillow openaiEdge-TTS

配合 OBS 使用:
  1. 运行 python live_anchor.py
  2. 在 OBS 中添加"浏览器源"，URL=http://localhost:8765
  3. 调整大小覆盖在直播画面上
"""

import asyncio
import json
import os
import random
import threading
import time
import uuid
from datetime import datetime
from queue import Queue, Empty
from dataclasses import dataclass, field
from typing import Optional, Callable
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================
API_BASE = "http://192.168.2.63:18080"  # LumiLearn 推理服务器
API_TIMEOUT = 30
MAX_RESPONSE_LENGTH = 200

AI_PERSONA = {
    "name": "小澍",
    "avatar": "🌿",
    "personality": "亲切、专业、有趣的中文教育AI助手，喜欢用生动的例子解释知识",
    "greeting": "大家好！我是小澍，AI学习规划师！有什么学习问题都可以问我哦～",
    "system_prompt": """你是「小澍」，一个专业又亲切的中文AI学习规划师助手。
你的特点：
- 回答简洁有趣，适合中小学生理解
- 擅长用比喻和例子解释复杂概念
- 会适当鼓励用户，保持积极向上的态度
- 回答控制在50字以内，简洁有力
- 遇到不懂的问题，诚实说不知道"""
}

# ============================================================
# 数据模型
# ============================================================
@dataclass
class Danmu:
    id: str
    user: str
    text: str
    platform: str
    timestamp: datetime = field(default_factory=datetime.now)
    replied: bool = False
    reply_text: str = ""

@dataclass
class AIBotConfig:
    name: str = "小澍"
    avatar_emoji: str = "🌿"
    response_delay_ms: int = 2000
    max_queue_size: int = 20
    enable_tts: bool = True
    enable_danmu_filter: bool = True

# ============================================================
# 弹幕来源适配器（抽象接口）
# ============================================================
from abc import ABC, abstractmethod

class DanmuSource(ABC):
    @abstractmethod
    def start(self, on_danmu: Callable[[Danmu], None]):
        pass

    @abstractmethod
    def stop(self):
        pass

# --- 模拟弹幕源（用于测试）---
class MockDanmuSource(DanmuSource):
    """测试用模拟弹幕源，替换为真实平台源"""

    TEST_MESSAGES = [
        "老师好！", "这个怎么做", "听不懂", "太难了", "哈哈",
        "1+1等于几", "三角形面积公式", "英语怎么说", "帮忙讲题",
        "好厉害", "小澍加油", "支持你", "👍", "666",
        "能教教我吗", "下一题", "这道题", "讲详细点",
        "明白了", "谢谢老师", "再来一遍", "懂了！",
        "小澍最棒", "教教我数学", "英语语法", "写作文",
        "推荐学习计划", "怎么学英语", "记忆力差怎么办",
    ]

    def __init__(self, interval_range=(3, 10)):
        self.interval_range = interval_range
        self.running = False
        self._thread = None
        self._on_danmu = None

    def start(self, on_danmu: Callable[[Danmu], None]):
        self._on_danmu = on_danmu
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("[Mock] 模拟弹幕源已启动")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        while self.running:
            delay = random.uniform(*self.interval_range)
            time.sleep(delay)
            if self.running and self._on_danmu:
                msg = random.choice(self.TEST_MESSAGES)
                danmu = Danmu(
                    id=str(uuid.uuid4())[:8],
                    user=f"用户{random.randint(1000,9999)}",
                    text=msg,
                    platform="mock"
                )
                self._on_danmu(danmu)


# --- 抖音直播弹幕源（通过抖音直播伴侣 + 本地端口转发）---
class DouyinDanmuSource(DanmuSource):
    """
    抖音弹幕抓取方案：
    方案A: 抖音直播伴侣开启「弹幕助手」功能，设置本地端口转发
    方案B: 使用 Fiddler/Charles 抓包抖音直播 ws:// 或 HTTP 接口
    方案C: 使用 xxdouyin 等开源项目

    此模块等待真实弹幕数据接入
    """

    def __init__(self, ws_url: str = None):
        self.ws_url = ws_url
        self.running = False
        self._thread = None
        self._on_danmu = None
        self._ws_client = None

    def start(self, on_danmu: Callable[[Danmu], None]):
        self._on_danmu = on_danmu
        if not self.ws_url:
            logger.warning("[Douyin] 未配置弹幕源，请使用 MockDanmuSource 测试")
            return
        self.running = True
        self._thread = threading.Thread(target=self._ws_loop, daemon=True)
        self._thread.start()
        logger.info(f"[Douyin] 弹幕源已连接: {self.ws_url}")

    def stop(self):
        self.running = False
        if self._ws_client:
            try:
                self._ws_client.close()
            except:
                pass

    def _ws_loop(self):
        try:
            import websocket
            self._ws_client = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=lambda ws, e: logger.error(f"[Douyin] WS错误: {e}"),
                on_close=lambda ws, c, m: logger.warning("[Douyin] WS关闭"),
            )
            self._ws_client.run_forever(ping_interval=30)
        except Exception as e:
            logger.error(f"[Douyin] 连接失败: {e}")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            # 解析抖音弹幕格式
            if data.get("type") == "chat":
                danmu = Danmu(
                    id=str(data.get("id", uuid.uuid4()))[:8],
                    user=data.get("user", {}).get("nickname", "匿名"),
                    text=data.get("content", ""),
                    platform="douyin"
                )
                self._on_danmu(danmu)
        except Exception as e:
            logger.debug(f"[Douyin] 解析失败: {e}")


# ============================================================
# AI 回复引擎（使用智能混合管道）
# ============================================================
from smart_reply_engine import LiveTutor

class AIResponder:
    """AI 回复生成器 - 包装 LiveTutor"""

    def __init__(self, config: AIBotConfig):
        self.config = config
        self._lock = threading.Lock()
        self.tutor = LiveTutor(api_base=API_BASE)

    def reply(self, danmu: Danmu, context: list[str] = None) -> str:
        """生成 AI 回复"""
        start = time.time()
        text = self.tutor.respond(danmu.text, danmu.user)
        elapsed = (time.time() - start) * 1000
        logger.info(f"[AI] @{danmu.user}: '{danmu.text}' → '{text[:50]}...' ({elapsed:.0f}ms)")
        return text


# ============================================================
# TTS 语音合成（可选）
# ============================================================
class TTSEngine:
    """TTS 语音合成引擎"""

    def __init__(self, enable: bool = True):
        self.enable = enable
        self._audio_queue = Queue()
        self._playing = False

    def speak(self, text: str):
        """将文字转为语音并播放"""
        if not self.enable:
            return
        self._audio_queue.put(text)
        if not self._playing:
            threading.Thread(target=self._play_loop, daemon=True).start()

    def _play_loop(self):
        self._playing = True
        while True:
            try:
                text = self._audio_queue.get(timeout=2)
            except Empty:
                self._playing = False
                break
            self._synthesize_and_play(text)

    def _synthesize_and_play(self, text: str):
        """实际合成语音"""
        try:
            from gtts import gTTS
            import io, pygame, tempfile
            pygame.mixer.init()

            mp3_fp = io.BytesIO()
            tts = gTTS(text=text, lang='zh', tld='com')
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(mp3_fp.read())
                fname = f.name

            pygame.mixer.music.load(fname)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.unload()
            os.unlink(fname)

        except ImportError:
            logger.warning("[TTS] gtts/pygame 未安装，语音功能不可用")
        except Exception as e:
            logger.warning(f"[TTS] 播放失败: {e}")


# ============================================================
# 弹幕过滤
# ============================================================
DANMU_BLOCKLIST = {
    "抖音粉丝团", "抖音", "关注", "粉丝", "加入粉丝团",
    "66666", "......", "啊啊啊啊", "哈哈哈哈哈哈",
    "哒哒哒", "~~~", "..........", "1111",
}

DANMU_MIN_LENGTH = 2
DANMU_MAX_LENGTH = 100

def is_valid_danmu(text: str) -> bool:
    """过滤无意义弹幕"""
    if len(text) < DANMU_MIN_LENGTH or len(text) > DANMU_MAX_LENGTH:
        return False
    if any(k in text for k in DANMU_BLOCKLIST):
        return False
    if text.count(text[0]) == len(text):  # 全相同字符
        return False
    return True


# ============================================================
# OBS 网页叠加层生成器
# ============================================================
class OBSOverlay:
    """
    生成 OBS 浏览器源可用的 HTML 叠加层
    在 OBS 中添加「浏览器源」，URL 设为 http://localhost:8765
    """

    def __init__(self, port: int = 8765):
        self.port = port
        self.danmu_list: list[dict] = []
        self.current_reply: str = ""
        self._lock = threading.Lock()

    def add_danmu(self, danmu: Danmu):
        with self._lock:
            entry = {
                "id": danmu.id,
                "user": danmu.user,
                "text": danmu.text,
                "time": danmu.timestamp.strftime("%H:%M"),
                "reply": danmu.reply_text,
                "is_new": True
            }
            self.danmu_list.insert(0, entry)
            self.danmu_list = self.danmu_list[:50]
            self.current_reply = danmu.reply_text

    def generate_html(self) -> str:
        """生成完整的 HTML 叠加页面"""
        with self._lock:
            danmu_html = ""
            for i, dm in enumerate(self.danmu_list[:8]):
                reply_html = ""
                if dm["reply"]:
                    reply_html = f"""
                    <div class="reply-box">
                        <span class="reply-label">🌿 {AI_PERSONA['name']} 回复：</span>
                        <span class="reply-text">{self._esc(dm['reply'])}</span>
                    </div>"""
                bg = "#1a3a2a" if i == 0 else ("#0f2a1a" if i % 2 == 0 else "#152a1f")
                danmu_html += f"""
                <div class="danmu-item" style="background:{bg}; animation-delay:{i*0.05}s">
                    <div class="dm-header">
                        <span class="dm-user">{self._esc(dm['user'])}</span>
                        <span class="dm-time">{dm['time']}</span>
                    </div>
                    <div class="dm-text">{self._esc(dm['text'])}</div>
                    {reply_html}
                </div>"""

        html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI小澍直播助手</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: transparent;
    font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
    width: 420px;
    min-height: 600px;
    padding: 10px;
  }}
  .header {{
    background: linear-gradient(135deg, #1a4d1a, #2d7a2d);
    border-radius: 12px 12px 0 0;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 2px;
  }}
  .avatar {{
    font-size: 32px;
    animation: pulse 2s ease-in-out infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ transform: scale(1); }}
    50% {{ transform: scale(1.1); }}
  }}
  .header-info h3 {{
    color: #7fff7f;
    font-size: 16px;
    font-weight: bold;
  }}
  .header-info p {{
    color: #aaffaa;
    font-size: 11px;
  }}
  .reply-panel {{
    background: linear-gradient(180deg, #0f2a1a 0%, #1a3a2a 100%);
    border-left: 3px solid #4ade80;
    padding: 10px 14px;
    min-height: 60px;
    margin-bottom: 2px;
  }}
  .reply-panel-label {{
    color: #4ade80;
    font-size: 11px;
    margin-bottom: 4px;
  }}
  .reply-panel-text {{
    color: #ffffff;
    font-size: 14px;
    line-height: 1.5;
    animation: fadeIn 0.3s ease;
  }}
  @keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(5px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  .danmu-list {{
    background: rgba(10, 20, 10, 0.7);
    border-radius: 0 0 12px 12px;
    overflow: hidden;
  }}
  .danmu-item {{
    padding: 8px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    animation: slideIn 0.3s ease;
  }}
  @keyframes slideIn {{
    from {{ opacity: 0; transform: translateX(-20px); }}
    to {{ opacity: 1; transform: translateX(0); }}
  }}
  .dm-header {{
    display: flex;
    justify-content: space-between;
    margin-bottom: 3px;
  }}
  .dm-user {{
    color: #86efac;
    font-size: 11px;
    font-weight: bold;
  }}
  .dm-time {{
    color: #4b5563;
    font-size: 10px;
  }}
  .dm-text {{
    color: #e5e7eb;
    font-size: 13px;
    line-height: 1.4;
  }}
  .reply-box {{
    margin-top: 6px;
    padding: 6px 8px;
    background: rgba(74, 222, 128, 0.1);
    border-radius: 6px;
    border-left: 2px solid #4ade80;
  }}
  .reply-label {{
    color: #4ade80;
    font-size: 10px;
  }}
  .reply-text {{
    color: #bbf7d0;
    font-size: 12px;
    margin-left: 4px;
  }}
</style>
</head>
<body>
<div class="header">
  <div class="avatar">{AI_PERSONA["avatar"]}</div>
  <div class="header-info">
    <h3>AI {AI_PERSONA["name"]} 学习助手</h3>
    <p>🌿 实时互动 · 已回复 {len(self.danmu_list)} 条弹幕</p>
  </div>
</div>
<div class="reply-panel">
  <div class="reply-panel-label">🌿 小澍 回复：</div>
  <div class="reply-panel-text">{self._esc(self.current_reply) if self.current_reply else "等待弹幕..."}</div>
</div>
<div class="danmu-list">
  {danmu_html if danmu_html else '<div style="padding:20px;color:#666;text-align:center;">暂无弹幕</div>'}
</div>
<script>
  // 自动刷新显示最新内容
  setTimeout(() => location.reload(), 30000);
</script>
</body>
</html>"""
        return html

    def _esc(self, s: str) -> str:
        return (s.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    def run_server(self):
        """启动本地 HTTP 服务器供 OBS 浏览器源访问"""
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(self.server.generator.generate_html().encode("utf-8"))

            def log_message(self, format, *args):
                pass

        server = HTTPServer(("0.0.0.0", self.port), Handler)
        server.generator = self
        logger.info(f"[OBS] 叠加层 HTTP 服务器启动: http://localhost:{self.port}")
        server.serve_forever()


# ============================================================
# 主程序
# ============================================================
class LiveAnchor:
    """直播 AI 助手主类"""

    def __init__(self, config: AIBotConfig = None):
        self.config = config or AIBotConfig()
        self.danmu_queue: Queue[Danmu] = Queue(maxsize=self.config.max_queue_size)
        self.context: list[str] = []
        self.responder = AIResponder(self.config)
        self.tts = TTSEngine(enable=self.config.enable_tts)
        self.overlay = OBSOverlay()
        self.running = False

    def on_danmu(self, danmu: Danmu):
        """收到弹幕时的回调"""
        if not is_valid_danmu(danmu.text):
            return
        logger.info(f"[Danmu] {danmu.user}: {danmu.text}")
        self.danmu_queue.put(danmu)

    def start(self, source: DanmuSource = None):
        """启动所有组件"""
        self.running = True

        # 启动弹幕源
        if source:
            source.start(self.on_danmu)

        # 启动 OBS 叠加层服务器
        overlay_thread = threading.Thread(target=self.overlay.run_server, daemon=True)
        overlay_thread.start()

        # 启动 AI 回复处理循环
        reply_thread = threading.Thread(target=self._reply_loop, daemon=True)
        reply_thread.start()

        # 启动状态监控
        monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        monitor_thread.start()

        logger.info("=" * 50)
        logger.info(f"  🌿 LumiLearn 直播助手「{AI_PERSONA['name']}」已启动！")
        logger.info(f"  OBS 叠加层: http://localhost:{self.overlay.port}")
        logger.info(f"  按 Ctrl+C 停止")
        logger.info("=" * 50)

        # 先发一条问候语
        time.sleep(3)
        greeting_dm = Danmu(
            id="init", user="系统",
            text="[开播]", platform="system"
        )
        greeting_dm.reply_text = AI_PERSONA["greeting"]
        self.overlay.add_danmu(greeting_dm)
        self.tts.speak(AI_PERSONA["greeting"])

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def _reply_loop(self):
        """AI 回复处理循环"""
        while self.running:
            try:
                danmu = self.danmu_queue.get(timeout=1)
            except Empty:
                continue

            # 延迟回复，模拟思考
            time.sleep(self.config.response_delay_ms / 1000)

            # 生成回复
            reply_text = self.responder.reply(danmu, self.context)

            # 更新上下文
            self.context.append(f"用户: {danmu.text} | 小澍: {reply_text}")
            if len(self.context) > 10:
                self.context = self.context[-10:]

            # 更新弹幕对象
            danmu.replied = True
            danmu.reply_text = reply_text

            # 更新叠加层显示
            self.overlay.add_danmu(danmu)

            # TTS 语音（仅回复较短的）
            if len(reply_text) <= 30:
                self.tts.speak(reply_text)

    def _monitor(self):
        """状态监控"""
        while self.running:
            time.sleep(30)
            logger.info(f"[Monitor] 队列: {self.danmu_queue.qsize()}, "
                        f"上下文: {len(self.context)} 条")

    def stop(self):
        self.running = False
        logger.info("停止直播助手...")


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LumiLearn 直播 AI 助手")
    parser.add_argument("--source", choices=["mock", "douyin"], default="mock",
                        help="弹幕来源: mock=测试, douyin=真实抖音")
    parser.add_argument("--tts", action="store_true", default=False,
                        help="启用 TTS 语音")
    parser.add_argument("--port", type=int, default=8765,
                        help="OBS 叠加层端口")
    parser.add_argument("--delay", type=int, default=2000,
                        help="AI 回复延迟(ms)")
    args = parser.parse_args()

    config = AIBotConfig(
        enable_tts=args.tts,
        response_delay_ms=args.delay
    )

    bot = LiveAnchor(config)

    if args.source == "mock":
        source = MockDanmuSource(interval_range=(2, 8))
    else:
        source = DouyinDanmuSource()

    bot.start(source)
