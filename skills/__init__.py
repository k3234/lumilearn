# -*- coding: utf-8 -*-
"""
LumiLearn Skills 模块
支持技能注册、加载和调用
"""

import os
import json
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path


class Skill:
    """技能类"""
    
    def __init__(self, skill_path: str):
        self.path = skill_path
        self.name = ""
        self.version = ""
        self.description = ""
        self.tags = []
        self.content = ""
        self.metadata = {}
        
        self._load()
    
    def _load(self):
        """加载技能文件"""
        skill_md = os.path.join(self.path, "SKILL.md")
        
        if not os.path.exists(skill_md):
            raise FileNotFoundError(f"技能文件不存在: {skill_md}")
        
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 解析 YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                self.metadata = frontmatter
                self.name = frontmatter.get("name", "")
                self.version = frontmatter.get("version", "")
                self.description = frontmatter.get("description", "")
                self.tags = frontmatter.get("tags", [])
                self.content = parts[2].strip()
        else:
            self.content = content
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "path": self.path,
            "metadata": self.metadata
        }


class SkillRegistry:
    """技能注册表"""
    
    def __init__(self, skills_dir: str = None):
        if skills_dir is None:
            skills_dir = os.path.dirname(os.path.abspath(__file__))
        self.skills_dir = skills_dir
        self.skills: Dict[str, Skill] = {}
        self._load_all()
    
    def _load_all(self):
        """加载所有技能"""
        for item in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, item)
            if os.path.isdir(skill_path) and not item.startswith("__"):
                try:
                    skill = Skill(skill_path)
                    self.skills[skill.name] = skill
                    print(f"[Skills] 已加载: {skill.name} v{skill.version}")
                except Exception as e:
                    print(f"[Skills] 加载失败 {item}: {e}")
    
    def get(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self.skills.get(name)
    
    def list_all(self) -> List[Dict[str, Any]]:
        """列出所有技能"""
        return [skill.to_dict() for skill in self.skills.values()]
    
    def search(self, tag: str = None, keyword: str = None) -> List[Dict[str, Any]]:
        """搜索技能"""
        results = []
        for skill in self.skills.values():
            if tag and tag not in skill.tags:
                continue
            if keyword and keyword.lower() not in skill.description.lower():
                continue
            results.append(skill.to_dict())
        return results


# 全局注册表
_registry = None

def get_registry() -> SkillRegistry:
    """获取全局技能注册表"""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry


if __name__ == "__main__":
    # 测试
    registry = get_registry()
    print("\n所有技能:")
    for skill in registry.list_all():
        print(f"  - {skill['name']}: {skill['description'][:50]}...")
