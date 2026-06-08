# -*- coding: utf-8 -*-
"""
灵学 lumilearn - Voicebox 语音合成服务
使用 Voicebox 进行语音合成和声音克隆，为agent制作专属声音

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-05
"""

import os
import requests
import tempfile
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any, Union, BinaryIO
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("lumilearn.voicebox_service")


class TTSEngine(Enum):
    """支持的TTS引擎"""
    QWEN3_TTS = "qwen3-tts"
    QWEN_CUSTOMVOICE = "qwen-customvoice"
    LUX_TTS = "lux-tts"
    CHATTERBOX_MULTILINGUAL = "chatterbox-multilingual"
    CHATTERBOX_TURBO = "chatterbox-turbo"
    TADA = "tada"
    KOKORO = "kokoro"


@dataclass
class VoiceProfile:
    """声音配置文件"""
    profile_id: str
    name: str
    description: str = ""
    language: str = "zh"
    engine: TTSEngine = TTSEngine.QWEN3_TTS
    personality: Optional[str] = None
    reference_audio_path: Optional[str] = None
    effects: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationConfig:
    """语音生成配置"""
    text: str
    profile: Union[str, VoiceProfile]  # profile_id 或 VoiceProfile对象
    language: str = "zh"
    engine: Optional[TTSEngine] = None
    seed: Optional[int] = None
    use_personality: bool = False
    max_length: int = 50000
    chunk_size: int = 1000
    crossfade_ms: int = 100


class VoiceboxService:
    """
    Voicebox 语音合成服务
    
    功能：
    - 通过Voicebox API进行语音合成
    - 声音克隆和声音配置文件管理
    - 支持多个TTS引擎
    - 为agent制作专属声音
    """

    DEFAULT_BASE_URL = "http://127.0.0.1:17493"
    
    def __init__(self, base_url: str = None):
        self._base_url = base_url or os.environ.get("VOICEBOX_URL", self.DEFAULT_BASE_URL)
        self._profiles: Dict[str, VoiceProfile] = {}
        self._default_profile: Optional[str] = None
        
        # 初始化默认agent声音配置
        self._init_default_agent_voices()

    def _init_default_agent_voices(self):
        """初始化默认agent声音配置"""
        # AI老师声音
        self._profiles["ai_teacher"] = VoiceProfile(
            profile_id="ai_teacher",
            name="AI老师",
            description="耐心、温和的AI老师声音",
            language="zh",
            engine=TTSEngine.QWEN3_TTS,
            personality="你是一位耐心、温和、专业的AI老师，说话清晰、语速适中，善于引导学生思考。"
        )
        
        # AI同学声音
        self._profiles["ai_classmate"] = VoiceProfile(
            profile_id="ai_classmate",
            name="AI同学",
            description="活泼、友好的AI同学声音",
            language="zh",
            engine=TTSEngine.KOKORO,
            personality="你是一位活泼、友好、积极向上的AI同学，说话轻松有趣，喜欢和同学交流学习心得。"
        )
        
        # AI助手声音
        self._profiles["ai_assistant"] = VoiceProfile(
            profile_id="ai_assistant",
            name="AI助手",
            description="专业、高效的AI助手声音",
            language="zh",
            engine=TTSEngine.LUX_TTS,
            personality="你是一位专业、高效、有条理的AI助手，说话清晰准确，能够快速理解和解决问题。"
        )
        
        self._default_profile = "ai_teacher"

    def is_available(self) -> bool:
        """检查Voicebox服务是否可用"""
        try:
            response = requests.get(f"{self._base_url}/health", timeout=2)
            return response.status_code in [200, 404]  # 404表示服务可能运行但无此端点
        except requests.exceptions.RequestException:
            return False

    def generate_speech(self, config: GenerationConfig, output_path: Optional[str] = None) -> str:
        """
        生成语音
        
        参数：
            config: 生成配置
            output_path: 输出文件路径，None则返回临时文件路径
            
        返回：
            生成的音频文件路径
        """
        profile_id = config.profile.profile_id if isinstance(config.profile, VoiceProfile) else config.profile
        
        payload = {
            "text": config.text,
            "profile_id": profile_id,
            "language": config.language,
        }
        
        if config.engine:
            payload["engine"] = config.engine.value
        if config.seed:
            payload["seed"] = config.seed
        if config.use_personality:
            payload["personality"] = True
        
        try:
            response = requests.post(
                f"{self._base_url}/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            # 保存音频
            if output_path is None:
                suffix = ".wav"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(response.content)
                    output_path = tmp.name
            else:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
            
            logger.info(f"语音生成成功: {output_path}")
            return output_path
            
        except requests.exceptions.RequestException as e:
            logger.error(f"语音生成失败: {e}")
            raise Exception(f"语音生成失败: {e}")

    def speak(self, text: str, profile: Optional[str] = None, language: str = "zh") -> bool:
        """
        让Voicebox直接播放语音（不保存文件）
        
        参数：
            text: 要朗读的文本
            profile: 声音配置文件ID
            language: 语言代码
            
        返回：
            是否成功
        """
        profile_id = profile or self._default_profile
        
        payload = {
            "text": text,
            "profile": profile_id,
            "language": language,
        }
        
        try:
            response = requests.post(
                f"{self._base_url}/speak",
                json=payload,
                headers={"X-Voicebox-Client-Id": "lumilearn-agent"},
                timeout=60
            )
            response.raise_for_status()
            logger.info(f"语音播放成功: {text[:30]}...")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"语音播放失败: {e}")
            return False

    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        获取所有声音配置文件列表
        
        返回：
            声音配置文件列表
        """
        # 先尝试从Voicebox获取
        try:
            response = requests.get(f"{self._base_url}/profiles", timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException:
            pass
        
        # 失败则返回本地配置
        return [
            {
                "profile_id": p.profile_id,
                "name": p.name,
                "description": p.description,
                "language": p.language,
                "engine": p.engine.value,
                "has_personality": p.personality is not None
            }
            for p in self._profiles.values()
        ]

    def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """获取声音配置文件"""
        if profile_id in self._profiles:
            return self._profiles[profile_id]
        
        # 尝试从Voicebox获取
        try:
            response = requests.get(f"{self._base_url}/profiles/{profile_id}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return VoiceProfile(
                    profile_id=data.get("profile_id", profile_id),
                    name=data.get("name", profile_id),
                    description=data.get("description", ""),
                    language=data.get("language", "zh"),
                    engine=TTSEngine(data.get("engine", "qwen3-tts")),
                    personality=data.get("personality")
                )
        except requests.exceptions.RequestException:
            pass
        
        return None

    def create_profile(
        self,
        profile_id: str,
        name: str,
        description: str = "",
        language: str = "zh",
        engine: TTSEngine = TTSEngine.QWEN3_TTS,
        reference_audio_path: Optional[str] = None,
        personality: Optional[str] = None
    ) -> VoiceProfile:
        """
        创建新的声音配置文件
        
        参数：
            profile_id: 配置文件ID
            name: 名称
            description: 描述
            language: 语言
            engine: TTS引擎
            reference_audio_path: 参考音频文件路径（用于克隆）
            personality: 人格描述
            
        返回：
            创建的VoiceProfile对象
        """
        profile = VoiceProfile(
            profile_id=profile_id,
            name=name,
            description=description,
            language=language,
            engine=engine,
            reference_audio_path=reference_audio_path,
            personality=personality
        )
        
        self._profiles[profile_id] = profile
        
        # 如果有参考音频，上传到Voicebox进行克隆
        if reference_audio_path and os.path.exists(reference_audio_path):
            self._clone_voice(profile_id, reference_audio_path)
        
        return profile

    def _clone_voice(self, profile_id: str, audio_path: str):
        """上传音频进行声音克隆"""
        try:
            with open(audio_path, "rb") as f:
                files = {"audio": f}
                data = {"profile_id": profile_id}
                response = requests.post(
                    f"{self._base_url}/clone",
                    files=files,
                    data=data,
                    timeout=120
                )
                response.raise_for_status()
                logger.info(f"声音克隆成功: {profile_id}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"声音克隆失败（可能Voicebox未运行）: {e}")

    def transcribe(self, audio_path: str, model: str = "whisper-turbo") -> Dict[str, Any]:
        """
        语音转文字
        
        参数：
            audio_path: 音频文件路径
            model: Whisper模型名称
            
        返回：
            转录结果
        """
        try:
            with open(audio_path, "rb") as f:
                files = {"audio": f}
                data = {"model": model}
                response = requests.post(
                    f"{self._base_url}/transcribe",
                    files=files,
                    data=data,
                    timeout=60
                )
                response.raise_for_status()
                return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"语音转录失败: {e}")
            raise Exception(f"语音转录失败: {e}")

    def set_default_profile(self, profile_id: str):
        """设置默认声音配置文件"""
        if profile_id in self._profiles:
            self._default_profile = profile_id
        else:
            logger.warning(f"声音配置文件不存在: {profile_id}")

    def get_agent_speech_generator(self, agent_type: str = "teacher"):
        """
        获取Agent语音生成器
        
        参数：
            agent_type: agent类型 (teacher/classmate/assistant)
            
        返回：
            一个可调用的函数，用于生成该agent的语音
        """
        profile_map = {
            "teacher": "ai_teacher",
            "classmate": "ai_classmate",
            "assistant": "ai_assistant"
        }
        
        profile_id = profile_map.get(agent_type, self._default_profile)
        
        def generator(text: str, output_path: Optional[str] = None) -> str:
            config = GenerationConfig(
                text=text,
                profile=profile_id,
                language="zh",
                use_personality=True
            )
            return self.generate_speech(config, output_path)
        
        return generator


_voicebox_service_instance: Optional[VoiceboxService] = None


def get_voicebox_service(base_url: str = None) -> VoiceboxService:
    """获取VoiceboxService单例"""
    global _voicebox_service_instance
    if _voicebox_service_instance is None:
        _voicebox_service_instance = VoiceboxService(base_url)
    return _voicebox_service_instance
