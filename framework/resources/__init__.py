# -*- coding: utf-8 -*-
"""
LumiLearn 资料管线包（framework/resources）
===========================================
为「数据库成长」与「资料共享」提供：
- importer：本地教材 / 教师上传（PPT/HTML/md/txt）/ 网络采集 → 统一解析、去重、入库 training_data
- 支撑 draft → reviewed → published 评审发布流

设计原则：
- 纯规则解析，不依赖重外部库（HTML 用内置正则、PPT 仅可选依赖 python-pptx，缺库时报错提示转 md）
- 网络采集默认关闭（resources.web_import_enabled=False），需管理员显式开启
"""
from .importer import ResourceImporter, parse_upload, import_web  # noqa: F401

importer = ResourceImporter()  # 全局资料导入单例

__all__ = ["ResourceImporter", "parse_upload", "import_web", "importer"]