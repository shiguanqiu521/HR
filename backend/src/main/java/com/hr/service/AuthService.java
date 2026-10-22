package com.hr.service;

import com.hr.common.BizException;
import com.hr.dto.LoginResponse;
import com.hr.model.SysUser;
import com.hr.repository.SysUserRepository;
import com.hr.security.JwtService;
import com.hr.security.PasswordHasher;
import org.springframework.stereotype.Service;

@Service
public class AuthService {

    private final SysUserRepository userRepository;
    private final JwtService jwtService;

    public AuthService(SysUserRepository userRepository, JwtService jwtService) {
        this.userRepository = userRepository;
        this.jwtService = jwtService;
    }

    public LoginResponse login(String username, String password) {
        SysUser user = userRepository.findByUsername(username.trim())
                .orElseThrow(() -> BizException.unauthorized("用户名或密码错误"));
        if (!user.enabled()) {
            throw BizException.unauthorized("账号已停用，请联系管理员");
        }
        if (!PasswordHasher.matches(password, user.salt(), user.passwordHash())) {
            throw BizException.unauthorized("用户名或密码错误");
        }
        String token = jwtService.generate(user.id(), user.username(), user.displayName());
        return LoginResponse.of(token, jwtService.getTtlSeconds(), user.username(), user.displayName());
    }
}
