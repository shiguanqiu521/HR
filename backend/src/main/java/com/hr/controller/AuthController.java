package com.hr.controller;

import com.hr.common.ApiResponse;
import com.hr.dto.LoginRequest;
import com.hr.dto.LoginResponse;
import com.hr.dto.UserInfo;
import com.hr.security.AuthInterceptor;
import com.hr.security.JwtService;
import com.hr.service.AuthService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    /** 登录：换取 JWT 令牌，此接口无需鉴权 */
    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return ApiResponse.success(authService.login(request.username(), request.password()));
    }

    /** 当前登录用户信息，供前端刷新页面后恢复登录态 */
    @GetMapping("/me")
    public ApiResponse<UserInfo> me(@RequestAttribute(AuthInterceptor.CURRENT_USER) JwtService.TokenPayload payload) {
        return ApiResponse.success(new UserInfo(payload.userId(), payload.username(), payload.displayName()));
    }
}
