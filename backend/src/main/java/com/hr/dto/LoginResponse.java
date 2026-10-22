package com.hr.dto;

/**
 * 登录成功响应。expiresIn 为令牌剩余有效秒数，前端据此提示何时需重新登录。
 */
public record LoginResponse(String token,
                            String tokenType,
                            long expiresIn,
                            String username,
                            String displayName) {

    public static LoginResponse of(String token, long expiresIn, String username, String displayName) {
        return new LoginResponse(token, "Bearer", expiresIn, username, displayName);
    }
}
