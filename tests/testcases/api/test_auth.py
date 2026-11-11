# -*- coding: utf-8 -*-
"""
认证接口测试

覆盖 TC-AUTH-001 ~ TC-AUTH-018（TC-AUTH-003/006/007 已合并，编号不回收）
设计方法：等价类划分、边界值分析（上下界成对）、判定表（token 三分支）、场景法、错误推测法
预期基线：LoginRequest 注解 + AuthInterceptor 三分支 + AuthService + GlobalExceptionHandler
Allure 的 feature/story/severity/title 由 conftest 依模块名、类名与 docstring 首行自动生成，用例内不写装饰器。
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.assertions import AssertUtil
from common.data_factory import DataFactory
from common.request_handler import BaseRequest
from config import Config

MISSING_CREDENTIAL = "未登录或登录凭证缺失，请先登录"
INVALID_CREDENTIAL = "登录凭证无效，请重新登录"
EXPIRED_CREDENTIAL = "登录已过期，请重新登录"
CREDENTIAL_ERROR = "用户名或密码错误"
TOKEN_TTL_SECONDS = 43200


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _sign_token(secret: str, payload: dict) -> str:
    """用 HS256 在本地签发 JWT，构造服务端能验签但已失效的 token。"""
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}"


class TestLogin:
    """POST /api/auth/login"""

    def test_login_success(self, auth_api):
        """TC-AUTH-001 [P0] 登录成功-获取Token

        等价类：凭据正确。断言 token 与用户身份信息完整下发。
        """
        resp = auth_api.login(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD)
        AssertUtil.assert_response_success(resp)
        AssertUtil.assert_message_equals(resp, "success")
        data = resp.json()["data"]
        assert data["token"], "token 不应为空"
        assert data["tokenType"] == "Bearer"
        assert data["expiresIn"] == TOKEN_TTL_SECONDS
        assert data["username"] == Config.ADMIN_USERNAME
        assert data["displayName"] == "系统管理员"

    @pytest.mark.parametrize("username,password", [
        ("nonexistent_user_zz", "admin123"),
        (Config.ADMIN_USERNAME, "wrongpwd_zz"),
    ], ids=["用户名不存在", "密码错误"])
    def test_login_fail_username_or_password(self, auth_api, username, password):
        """TC-AUTH-002 [P0] 登录失败-用户名不存在或密码错误（防枚举一致性）

        等价类：凭据错误的两个来源（原 TC-AUTH-003 已并入）。
        两行都断言 message 完全等于同一常量，这本身就是防枚举判定点。
        """
        resp = auth_api.login(username, password)
        AssertUtil.assert_status_code(resp, 401, f"{username}/{password}: ")
        AssertUtil.assert_biz_code(resp, 401)
        AssertUtil.assert_message_equals(resp, CREDENTIAL_ERROR)
        assert resp.json()["data"] is None

    @pytest.mark.parametrize("payload", [
        {"username": "", "password": "admin123"},
        {"password": "admin123"},
    ], ids=["username空串", "username字段缺失"])
    def test_login_username_blank_or_missing(self, auth_api, payload):
        """TC-AUTH-004 [P1] 登录失败-username 为空或缺失

        等价类：必填字段为空/缺失。@NotBlank 先于凭据比对执行，因此是 400 而非 401。
        """
        resp = auth_api.req.post_no_auth("/api/auth/login", json=payload)
        AssertUtil.assert_status_code(resp, 400, f"{payload}: ")
        AssertUtil.assert_biz_code(resp, 400)
        AssertUtil.assert_message_contains(resp, "用户名不能为空")
        assert resp.json()["data"] is None

    @pytest.mark.parametrize("payload", [
        {"username": "admin", "password": ""},
        {"username": "admin"},
    ], ids=["password空串", "password字段缺失"])
    def test_login_password_blank_or_missing(self, auth_api, payload):
        """TC-AUTH-005 [P1] 登录失败-password 为空或缺失

        等价类：必填字段为空/缺失，与 TC-AUTH-004 同源码分支的不同字段。
        """
        resp = auth_api.req.post_no_auth("/api/auth/login", json=payload)
        AssertUtil.assert_status_code(resp, 400, f"{payload}: ")
        AssertUtil.assert_biz_code(resp, 400)
        AssertUtil.assert_message_contains(resp, "密码不能为空")
        assert resp.json()["data"] is None

    @pytest.mark.parametrize("length,expected_status,expected_keyword", [
        (50, 401, CREDENTIAL_ERROR),
        (51, 400, "用户名长度不能超过50个字符"),
    ], ids=["50字符有效上界", "51字符首个无效值"])
    def test_login_username_length_boundary(self, auth_api, length, expected_status, expected_keyword):
        """TC-AUTH-008 [P2] 登录-username 长度边界（50 通过长度校验 / 51 被拒）

        边界值成对：50 通过长度校验进入凭据比对（账号不存在 → 401），51 在校验即被拒 → 400。
        """
        resp = auth_api.login("u" * length, Config.ADMIN_PASSWORD)
        AssertUtil.assert_status_code(resp, expected_status, f"username 长度 {length}: ")
        AssertUtil.assert_message_contains(resp, expected_keyword)

    @pytest.mark.parametrize("length,expected_status,expected_keyword", [
        (64, 401, CREDENTIAL_ERROR),
        (65, 400, "密码长度不能超过64个字符"),
    ], ids=["64字符有效上界", "65字符首个无效值"])
    def test_login_password_length_boundary(self, auth_api, length, expected_status, expected_keyword):
        """TC-AUTH-009 [P2] 登录-password 长度边界（64 通过长度校验 / 65 被拒）

        边界值成对。源码 @Size(max=64) 与 API.md §2.2 声明的 100 不一致（缺陷 D1）。
        """
        resp = auth_api.login(Config.ADMIN_USERNAME, "p" * length)
        AssertUtil.assert_status_code(resp, expected_status, f"password 长度 {length}: ")
        AssertUtil.assert_message_contains(resp, expected_keyword)

    def test_login_username_only_spaces(self, auth_api):
        """TC-AUTH-016 [P2] 登录失败-username 为纯空格

        错误推测：@NotBlank 将仅空白字符视为空，不可下发 token。
        """
        resp = auth_api.login("   ", Config.ADMIN_PASSWORD)
        AssertUtil.assert_status_code(resp, 400)
        AssertUtil.assert_message_contains(resp, "用户名不能为空")
        assert resp.json()["data"] is None

    @pytest.mark.parametrize("username,password,expected_status", [
        ("  admin  ", "admin123", 200),
        ("admin", " admin123", 401),
    ], ids=["用户名带空格被trim", "密码带空格不trim"])
    def test_login_credential_with_surrounding_spaces(self, auth_api, username, password, expected_status):
        """TC-AUTH-017 [P2] 登录-用户名/密码前后带空格

        错误推测：用户名走 findByUsername(trim)，密码用原值比对，两行共同界定该不对称行为。
        """
        resp = auth_api.login(username, password)
        AssertUtil.assert_status_code(resp, expected_status, f"{repr(username)}/{repr(password)}: ")
        if expected_status == 200:
            assert resp.json()["data"]["username"] == Config.ADMIN_USERNAME
        else:
            AssertUtil.assert_message_equals(resp, CREDENTIAL_ERROR)


class TestCurrentUser:
    """GET /api/auth/me —— AuthInterceptor 判定表"""

    def test_get_current_user_success(self, auth_api):
        """TC-AUTH-010 [P0] 获取当前用户-成功"""
        resp = auth_api.get_current_user()
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]
        assert isinstance(data["userId"], int) and data["userId"] > 0
        assert data["username"] == Config.ADMIN_USERNAME
        assert data["displayName"] == "系统管理员"

    def test_get_current_user_no_token(self, no_auth_client):
        """TC-AUTH-011 [P0] 获取当前用户-未携带 Token

        判定表分支①：请求头缺失。message 必须精确锚定，否则与其它 401 分支不可区分。
        """
        resp = no_auth_client.get("/api/auth/me")
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_biz_code(resp, 401)
        AssertUtil.assert_message_equals(resp, MISSING_CREDENTIAL)
        assert resp.json()["data"] is None

    @pytest.mark.parametrize("auth_header", ["InvalidFormat", "Bearer "],
                             ids=["无Bearer前缀", "Bearer后为空"])
    def test_get_current_user_header_format(self, no_auth_client, auth_header):
        """TC-AUTH-012 [P1] 获取当前用户-Authorization 头格式非法

        判定表分支①：不以 "Bearer " 开头、或 Bearer 后为空白，两者共用"凭证缺失"message。
        """
        resp = no_auth_client.get("/api/auth/me", headers={"Authorization": auth_header})
        AssertUtil.assert_status_code(resp, 401, f"Authorization={repr(auth_header)}: ")
        AssertUtil.assert_message_equals(resp, MISSING_CREDENTIAL)

    def test_get_current_user_fake_token(self, no_auth_client):
        """TC-AUTH-013 [P0] 获取当前用户-Token 伪造

        判定表分支②：签名校验失败。
        """
        resp = no_auth_client.get("/api/auth/me", headers={"Authorization": "Bearer fake.token.here"})
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_biz_code(resp, 401)
        AssertUtil.assert_message_equals(resp, INVALID_CREDENTIAL)
        assert resp.json()["data"] is None

    def test_get_current_user_expired_token(self, no_auth_client):
        """TC-AUTH-014 [P1] 获取当前用户-Token 已过期

        判定表分支③：签名有效但 exp 已过。JWT 无状态本地验签，故用 HR_JWT_SECRET 本地自签，
        无需修改后端 TTL 配置、无需等待。
        """
        secret = getattr(Config, "JWT_SECRET", "") or os.getenv("HR_JWT_SECRET", "")
        if not secret:
            pytest.skip("未配置 HR_JWT_SECRET（.env），无法本地自签过期 token")
        now = int(time.time())
        token = _sign_token(secret, {
            "sub": Config.ADMIN_USERNAME,
            "uid": 1,
            "displayName": "系统管理员",
            "iat": now - 7200,
            "exp": now - 3600,
        })
        resp = no_auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_biz_code(resp, 401)
        AssertUtil.assert_message_equals(resp, EXPIRED_CREDENTIAL)


class TestAuthFlow:
    """场景法：认证链路端到端"""

    def test_login_token_grants_access_to_business_api(self):
        """TC-AUTH-018 [P0] 认证链路-登录后访问受保护接口

        场景法：本次登录返回的 token 立即可用于 /me 与业务接口，证明认证闭环成立。
        不复用全局 request_client，才能证明"新签发的 token"本身有效。
        """
        client = BaseRequest()
        token = client_login(client)
        assert token, "登录未返回 token"

        me = client.get("/api/auth/me")
        AssertUtil.assert_response_success(me, "携带本次 token 访问 /api/auth/me: ")
        assert me.json()["data"]["username"] == Config.ADMIN_USERNAME

        listing = client.get("/api/employees", params={"page": 1, "size": 10})
        AssertUtil.assert_response_success(listing, "携带本次 token 访问员工列表: ")
        assert isinstance(listing.json()["data"]["list"], list)


class TestHealth:
    """GET /api/health"""

    def test_health_check(self, no_auth_client):
        """TC-AUTH-015 [P1] 健康检查-无需认证

        源码 HealthController 硬编码返回 UP，不检测 DB/Redis（缺陷 D4），
        故本用例不作为服务可用性门禁，环境就绪判定由 request_client fixture 的真实登录承担。
        """
        resp = no_auth_client.get("/api/health")
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]
        assert data["status"] == "UP"
        assert data["application"] == "hr-employee"


def client_login(client: BaseRequest) -> str:
    """登录并把 token 设置到指定客户端，返回 token。"""
    resp = client.post_no_auth("/api/auth/login",
                               json=DataFactory.login_payload(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD))
    AssertUtil.assert_response_success(resp, "认证链路登录: ")
    token = resp.json()["data"]["token"]
    client.set_token(token)
    return token
