package com.hr.security;

import com.hr.common.BizException;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.cors.CorsUtils;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * 登录拦截器：校验 Authorization: Bearer &lt;token&gt;，通过后把用户信息挂到 request 属性上。
 * 校验失败抛 BizException(401)，由 GlobalExceptionHandler 统一转成响应体。
 */
@Component
public class AuthInterceptor implements HandlerInterceptor {

    public static final String CURRENT_USER = "hr.currentUser";
    private static final String BEARER_PREFIX = "Bearer ";

    private final JwtService jwtService;

    public AuthInterceptor(JwtService jwtService) {
        this.jwtService = jwtService;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        // CORS 预检请求由浏览器发出，不携带业务请求头，必须放行
        if (CorsUtils.isPreFlightRequest(request)) {
            return true;
        }

        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.startsWith(BEARER_PREFIX) || header.substring(BEARER_PREFIX.length()).isBlank()) {
            throw BizException.unauthorized("未登录或登录凭证缺失，请先登录");
        }

        JwtService.TokenPayload payload;
        try {
            payload = jwtService.parse(header.substring(BEARER_PREFIX.length()).trim());
        } catch (ExpiredJwtException e) {
            throw BizException.unauthorized("登录已过期，请重新登录");
        } catch (JwtException | IllegalArgumentException e) {
            throw BizException.unauthorized("登录凭证无效，请重新登录");
        }

        request.setAttribute(CURRENT_USER, payload);
        return true;
    }
}
