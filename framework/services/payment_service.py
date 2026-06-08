"""
LumiLearn 支付服务模块
基于 alipay-payment-integration skill

支持产品：
- 电脑网站支付（alipay.trade.page.pay）：用于一次性购买
- 商家扣款（alipay.trade.app.pay）：用于会员订阅/周期扣款

参考文档：
- 电脑网站支付：https://ideservice.alipay.com/cms/site/0iztfv
- 商家扣款：https://ideservice.alipay.com/cms/site/0j0g6k
"""

import os
import json
import time
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PayType(Enum):
    """支付类型"""
    WEB_PAGE = "page_pay"          # 电脑网站支付
    APP_PAY = "app_pay"            # App支付
    BAR_CODE = "bar_code"          # 当面付（条码支付）
    SCAN = "scan"                  # 当面付（扫码支付）
    SIGNING = "signing"            # 商家扣款（签约）


class PaymentService:
    """支付宝支付服务"""

    # 沙箱环境
    SANDBOX_GATEWAY = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
    # 正式环境
    PRODUCTION_GATEWAY = "https://openapi.alipay.com/gateway.do"

    def __init__(
        self,
        app_id: str = "",
        private_key: str = "",
        alipay_public_key: str = "",
        sandbox: bool = True,
        notify_url: str = "",
        return_url: str = ""
    ):
        """
        初始化支付服务

        Args:
            app_id: 支付宝应用ID
            private_key: 应用私钥
            alipay_public_key: 支付宝公钥
            sandbox: 是否使用沙箱环境
            notify_url: 异步通知地址
            return_url: 同步返回地址
        """
        self.app_id = app_id or os.getenv("ALIPAY_APP_ID", "")
        self.private_key = private_key or os.getenv("ALIPAY_PRIVATE_KEY", "")
        self.alipay_public_key = alipay_public_key or os.getenv("ALIPAY_PUBLIC_KEY", "")
        self.sandbox = sandbox
        self.gateway = self.SANDBOX_GATEWAY if sandbox else self.PRODUCTION_GATEWAY
        self.notify_url = notify_url or os.getenv("ALIPAY_NOTIFY_URL", "")
        self.return_url = return_url or os.getenv("ALIPAY_RETURN_URL", "")

        self._sdk = None

    def _get_sdk(self):
        """延迟初始化SDK"""
        if self._sdk is None:
            try:
                from alipay import AliPay
                self._sdk = AliPay(
                    appid=self.app_id,
                    app_notify_url=self.notify_url,
                    app_private_key_string=self.private_key,
                    alipay_public_key_string=self.alipay_public_key,
                    sign_type="RSA2",
                    debug=self.sandbox
                )
            except ImportError:
                logger.warning("alipay-sdk-python 未安装，将使用模拟模式")
                self._sdk = None
        return self._sdk

    # ============================================================
    # 支付接口
    # ============================================================

    def create_web_page_pay(
        self,
        out_trade_no: str,
        subject: str,
        total_amount: float,
        body: str = "",
        timeout_express: str = "15m"
    ) -> Dict[str, Any]:
        """
        电脑网站支付（alipay.trade.page.pay）

        适用场景：用户通过网页购买会员、付费内容等

        Args:
            out_trade_no: 商户订单号（需保证唯一性）
            subject: 订单标题
            total_amount: 订单金额（元）
            body: 订单描述
            timeout_express: 支付超时时间

        Returns:
            包含支付表单的字典，可直接返回给前端
        """
        if not self.app_id:
            return self._mock_response(
                "web_page_pay",
                out_trade_no,
                f"沙箱模拟电脑网站支付：{subject}，金额：{total_amount}元"
            )

        sdk = self._get_sdk()
        if sdk is None:
            return self._mock_response(
                "web_page_pay",
                out_trade_no,
                f"SDK不可用，模拟支付：{subject}，金额：{total_amount}元"
            )

        try:
            biz_content = {
                "out_trade_no": out_trade_no,
                "product_code": "FAST_INSTANT_TRADE_PAY",
                "total_amount": total_amount,
                "subject": subject,
                "body": body or subject,
                "timeout_express": timeout_express,
            }

            # 调用SDK
            pay_url = f"{self.gateway}?{sdk.api_alipay_trade_page_pay(biz_content)}"
            return {
                "success": True,
                "pay_url": pay_url,
                "out_trade_no": out_trade_no,
                "qr_code": f"https://qr.alipay.com/{out_trade_no}"  # 模拟二维码
            }
        except Exception as e:
            logger.error(f"创建网页支付失败: {e}")
            return {"success": False, "error": str(e)}

    def create_qr_code(
        self,
        out_trade_no: str,
        subject: str,
        total_amount: float,
        timeout_express: str = "15m"
    ) -> Dict[str, Any]:
        """
        订单码支付（alipay.trade.precreate）

        适用场景：生成二维码，用户扫码支付

        Args:
            out_trade_no: 商户订单号
            subject: 订单标题
            total_amount: 订单金额（元）
            timeout_express: 支付超时时间

        Returns:
            包含二维码链接的字典
        """
        if not self.app_id:
            return self._mock_response(
                "qr_code",
                out_trade_no,
                f"沙箱模拟二维码支付：{subject}，金额：{total_amount}元"
            )

        sdk = self._get_sdk()
        if sdk is None:
            return self._mock_response(
                "qr_code",
                out_trade_no,
                f"SDK不可用，模拟二维码：{subject}，金额：{total_amount}元"
            )

        try:
            biz_content = {
                "out_trade_no": out_trade_no,
                "total_amount": total_amount,
                "subject": subject,
                "timeout_express": timeout_express,
            }

            response = sdk.alipay_trade_precreate(biz_content)
            return {
                "success": True,
                "qr_code": response.get("qr_code", ""),
                "out_trade_no": out_trade_no
            }
        except Exception as e:
            logger.error(f"创建二维码支付失败: {e}")
            return {"success": False, "error": str(e)}

    def bar_code_pay(
        self,
        out_trade_no: str,
        subject: str,
        total_amount: float,
        auth_code: str,
        timeout_express: str = "15m"
    ) -> Dict[str, Any]:
        """
        当面付-条码支付（alipay.trade.pay）

        适用场景：商家用扫码枪扫描用户付款码

        Args:
            out_trade_no: 商户订单号
            subject: 订单标题
            total_amount: 订单金额（元）
            auth_code: 用户付款码
            timeout_express: 支付超时时间

        Returns:
            支付结果
        """
        if not self.app_id:
            return self._mock_response(
                "bar_code",
                out_trade_no,
                f"沙箱模拟条码支付：{subject}，金额：{total_amount}元"
            )

        sdk = self._get_sdk()
        if sdk is None:
            return self._mock_response(
                "bar_code",
                out_trade_no,
                f"SDK不可用，模拟条码：{subject}，金额：{total_amount}元"
            )

        try:
            biz_content = {
                "out_trade_no": out_trade_no,
                "scene": "bar_code",
                "auth_code": auth_code,
                "product_code": "FACE_TO_FACE_PAYMENT",
                "total_amount": total_amount,
                "subject": subject,
                "timeout_express": timeout_express,
            }

            response = sdk.alipay_trade_pay(biz_content)
            return {
                "success": True,
                "trade_no": response.get("trade_no", ""),
                "out_trade_no": out_trade_no,
                "trade_status": response.get("trade_status", "")
            }
        except Exception as e:
            logger.error(f"条码支付失败: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================
    # 商家扣款（会员订阅）
    # ============================================================

    def create_signing_url(
        self,
        out_trade_no: str,
        subject: str,
        total_amount: float,
        agreement_sign_products: Dict[str, Any],
        return_url: str = ""
    ) -> Dict[str, Any]:
        """
        商家扣款签约（alipay.user.agreement.page.sign）

        适用场景：会员订阅、周期扣款

        Args:
            out_trade_no: 商户订单号
            subject: 订单标题
            total_amount: 首次支付金额
            agreement_sign_products: 签约产品参数
            return_url: 签约成功返回地址

        Returns:
            签约URL
        """
        if not self.app_id:
            return self._mock_response(
                "signing",
                out_trade_no,
                f"沙箱模拟签约：{subject}，首次金额：{total_amount}元"
            )

        sdk = self._get_sdk()
        if sdk is None:
            return self._mock_response(
                "signing",
                out_trade_no,
                f"SDK不可用，模拟签约URL：{subject}"
            )

        try:
            biz_content = {
                "product_code": "GENERAL_WITHHOLDING",
                "personal_product_code": "CYCLE_PAY_AUTH_P",
                "sign_scene": "INDUSTRY|CARTOON",
                "external_agreement_no": out_trade_no,
                "product_name": subject,
                "amount": total_amount,
                "agreement_sign_properties": json.dumps({
                    "period_type": "DAY",
                    "period": 30,
                    "execute_time": "07:00"
                }),
                "return_url": return_url or self.return_url,
            }

            sign_url = sdk.api_alipay_user_agreement_page_sign(biz_content)
            return {
                "success": True,
                "sign_url": sign_url,
                "out_trade_no": out_trade_no
            }
        except Exception as e:
            logger.error(f"创建签约URL失败: {e}")
            return {"success": False, "error": str(e)}

    def execute_deduct(
        self,
        out_trade_no: str,
        agreement_no: str,
        amount: float,
        subject: str = ""
    ) -> Dict[str, Any]:
        """
        执行周期扣款（alipay.trade.app.pay）

        注意：商家扣款暂不支持沙箱调试

        Args:
            out_trade_no: 商户扣款订单号
            agreement_no: 签约协议号
            amount: 扣款金额
            subject: 扣款主题

        Returns:
            扣款结果
        """
        if self.sandbox:
            return {
                "success": False,
                "error": "商家扣款暂不支持沙箱调试，请使用正式环境"
            }

        if not self.app_id:
            return self._mock_response(
                "deduct",
                out_trade_no,
                f"模拟扣款：{subject}，金额：{amount}元"
            )

        sdk = self._get_sdk()
        if sdk is None:
            return {
                "success": False,
                "error": "SDK不可用"
            }

        try:
            biz_content = {
                "out_trade_no": out_trade_no,
                "agreement_no": agreement_no,
                "pay_amount": amount,
                "product_code": "GENERAL_WITHHOLDING",
                "subject": subject or "会员订阅扣款",
                "body": f"代扣：{agreement_no}",
            }

            response = sdk.alipay_trade_app_pay(biz_content)
            return {
                "success": True,
                "trade_no": response.get("trade_no", ""),
                "out_trade_no": out_trade_no
            }
        except Exception as e:
            logger.error(f"执行扣款失败: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================
    # 查询与退款
    # ============================================================

    def query_trade(self, out_trade_no: str) -> Dict[str, Any]:
        """查询交易状态（alipay.trade.query）"""
        if not self.app_id:
            return self._mock_response("query", out_trade_no, "TRADE_SUCCESS")

        sdk = self._get_sdk()
        if sdk is None:
            return self._mock_response("query", out_trade_no, "TRADE_SUCCESS")

        try:
            biz_content = {"out_trade_no": out_trade_no}
            response = sdk.alipay_trade_query(biz_content)
            return {
                "success": True,
                "trade_status": response.get("trade_status", ""),
                "out_trade_no": out_trade_no
            }
        except Exception as e:
            logger.error(f"查询交易失败: {e}")
            return {"success": False, "error": str(e)}

    def refund(
        self,
        out_trade_no: str,
        refund_amount: float,
        refund_reason: str = ""
    ) -> Dict[str, Any]:
        """退款（alipay.trade.refund）"""
        if not self.app_id:
            return self._mock_response("refund", out_trade_no, f"退款：{refund_amount}元")

        sdk = self._get_sdk()
        if sdk is None:
            return self._mock_response("refund", out_trade_no, f"退款：{refund_amount}元")

        try:
            biz_content = {
                "out_trade_no": out_trade_no,
                "refund_amount": refund_amount,
                "refund_reason": refund_reason or "用户请求退款"
            }
            response = sdk.alipay_trade_refund(biz_content)
            return {
                "success": True,
                "out_trade_no": out_trade_no,
                "refund_fee": response.get("refund_fee", 0)
            }
        except Exception as e:
            logger.error(f"退款失败: {e}")
            return {"success": False, "error": str(e)}

    def close_trade(self, out_trade_no: str) -> Dict[str, Any]:
        """关闭交易（alipay.trade.close）"""
        if not self.app_id:
            return self._mock_response("close", out_trade_no, "CLOSED")

        sdk = self._get_sdk()
        if sdk is None:
            return self._mock_response("close", out_trade_no, "CLOSED")

        try:
            biz_content = {"out_trade_no": out_trade_no}
            sdk.alipay_trade_close(biz_content)
            return {"success": True, "out_trade_no": out_trade_no}
        except Exception as e:
            logger.error(f"关闭交易失败: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================
    # 异步通知处理
    # ============================================================

    @staticmethod
    def verify_notification(post_data: Dict[str, str], alipay_public_key: str) -> bool:
        """
        验证异步通知签名

        安全要求：
        1. 必须验签确保通知来自支付宝
        2. 核对 app_id、out_trade_no、total_amount
        3. 只有 trade_status=TRADE_SUCCESS 或 TRADE_FINISHED 才表示支付成功

        Args:
            post_data: POST收到的通知数据
            alipay_public_key: 支付宝公钥

        Returns:
            验签是否通过
        """
        from alipay import AliPay

        try:
            alipay = AliPay(
                appid=post_data.get("app_id", ""),
                app_notify_url="",
                app_private_key_string="",
                alipay_public_key_string=alipay_public_key,
                sign_type="RSA2"
            )

            signature = post_data.get("sign", "")
            sign_type = post_data.get("sign_type", "RSA2")

            # 移除sign和sign_type进行验签
            data_to_verify = {k: v for k, v in post_data.items()
                            if k not in ("sign", "sign_type")}

            return alipay.verify(data_to_verify, signature)
        except Exception as e:
            logger.error(f"验签失败: {e}")
            return False

    @staticmethod
    def parse_notification(post_data: Dict[str, str]) -> Dict[str, Any]:
        """解析异步通知数据"""
        return {
            "trade_status": post_data.get("trade_status", ""),
            "out_trade_no": post_data.get("out_trade_no", ""),
            "trade_no": post_data.get("trade_no", ""),
            "total_amount": float(post_data.get("total_amount", 0)),
            "buyer_pay_amount": float(post_data.get("buyer_pay_amount", 0)),
            "receipt_amount": float(post_data.get("receipt_amount", 0)),
            "gmt_payment": post_data.get("gmt_payment", ""),
            "fund_bill_list": post_data.get("fund_bill_list", ""),
        }

    # ============================================================
    # 辅助方法
    # ============================================================

    def _mock_response(self, pay_type: str, out_trade_no: str, message: str) -> Dict[str, Any]:
        """生成模拟响应（沙箱或未配置时使用）"""
        return {
            "success": True,
            "mock": True,
            "pay_type": pay_type,
            "out_trade_no": out_trade_no,
            "message": message,
            "sandbox_url": self.gateway if self.sandbox else None,
            "note": "这是沙箱模拟响应，实际支付需要配置支付宝密钥"
        }

    @staticmethod
    def generate_trade_no() -> str:
        """生成唯一订单号"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        return f"LL{timestamp}{random_str}"

    def is_sandbox(self) -> bool:
        """是否沙箱环境"""
        return self.sandbox

    def get_config_status(self) -> Dict[str, bool]:
        """获取配置状态"""
        return {
            "app_id": bool(self.app_id),
            "private_key": bool(self.private_key),
            "alipay_public_key": bool(self.alipay_public_key),
            "sandbox": self.sandbox
        }


# ============================================================
# 会员订阅定价
# ============================================================

class MembershipPlan(Enum):
    """会员方案"""
    FREE = ("free", "免费版", 0, ["基础AI对话，每日50次"])
    PERSONAL = ("personal", "个人版", 29, ["完整功能，无限使用"])
    FAMILY = ("family", "家庭版", 79, ["5个账号，孩子管理"])
    SCHOOL = ("school", "学校版", 999, ["全班使用，教师后台"])

    def __init__(self, plan_id: str, plan_name: str, price: float, features: list):
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.price = price  # 元/月
        self.features = features

    @classmethod
    def get_plan(cls, plan_id: str) -> Optional["MembershipPlan"]:
        """获取会员方案"""
        for plan in cls:
            if plan.plan_id == plan_id:
                return plan
        return None

    @classmethod
    def get_all_plans(cls) -> list:
        """获取所有会员方案"""
        return [plan for plan in cls]


# ============================================================
# 快捷函数
# ============================================================

# 全局支付服务实例
_payment_service: Optional[PaymentService] = None


def get_payment_service() -> PaymentService:
    """获取全局支付服务实例"""
    global _payment_service
    if _payment_service is None:
        _payment_service = PaymentService(
            app_id=os.getenv("ALIPAY_APP_ID", ""),
            private_key=os.getenv("ALIPAY_PRIVATE_KEY", ""),
            alipay_public_key=os.getenv("ALIPAY_PUBLIC_KEY", ""),
            sandbox=os.getenv("ALIPAY_SANDBOX", "true").lower() == "true",
            notify_url=os.getenv("ALIPAY_NOTIFY_URL", ""),
            return_url=os.getenv("ALIPAY_RETURN_URL", "")
        )
    return _payment_service


def init_payment_service(**kwargs) -> PaymentService:
    """初始化支付服务"""
    global _payment_service
    _payment_service = PaymentService(**kwargs)
    return _payment_service
