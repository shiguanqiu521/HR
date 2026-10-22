package com.hr.security;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Date;

/**
 * JWT 签发与校验，无状态：服务端不保存会话，令牌自带过期时间。
 */
@Component
public class JwtService {

    private final SecretKey key;
    private final Duration ttl;

    public JwtService(@Value("${hr.auth.jwt-secret}") String secret,
                      @Value("${hr.auth.token-ttl-minutes}") long ttlMinutes) {
        byte[] keyBytes = secret.getBytes(StandardCharsets.UTF_8);
        if (keyBytes.length < 32) {
            throw new IllegalStateException("hr.auth.jwt-secret 长度不足，HS256 要求至少 32 字节");
        }
        this.key = Keys.hmacShaKeyFor(keyBytes);
        this.ttl = Duration.ofMinutes(ttlMinutes);
    }

    public record TokenPayload(long userId, String username, String displayName) {
    }

    public String generate(long userId, String username, String displayName) {
        Date now = new Date();
        return Jwts.builder()
                .subject(username)
                .claim("uid", userId)
                .claim("displayName", displayName)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + ttl.toMillis()))
                .signWith(key, Jwts.SIG.HS256)
                .compact();
    }

    /**
     * 校验签名与有效期，失败时抛出 io.jsonwebtoken.JwtException 的子类，由调用方转成 401。
     */
    public TokenPayload parse(String token) {
        var claims = Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
        return new TokenPayload(
                claims.get("uid", Number.class).longValue(),
                claims.getSubject(),
                claims.get("displayName", String.class));
    }

    public long getTtlSeconds() {
        return ttl.toSeconds();
    }
}
