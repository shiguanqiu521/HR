package com.hr.service;

import com.hr.common.BizException;
import com.hr.model.SysUser;
import com.hr.repository.SysUserRepository;
import com.hr.security.JwtService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock
    private SysUserRepository userRepository;

    @Mock
    private JwtService jwtService;

    @InjectMocks
    private AuthService authService;

    /**
     * 接口侧无法构造停用账号：sys_user 没有写入口（首启初始化为 enabled=1，也没有用户管理接口），
     * 这一分支只能在这里驱动。login 的其余三个分支由接口用例锚定，不重复。
     */
    @Test
    @DisplayName("登录 - 账号已停用返回 401，且不进入口令校验")
    void loginRejectsDisabledAccount() {
        SysUser disabled = new SysUser(2L, "old.user", "anyHash", "anySalt", "历史用户", false);
        when(userRepository.findByUsername("old.user")).thenReturn(Optional.of(disabled));

        BizException ex = assertThrows(BizException.class, () -> authService.login("old.user", "anyPassword"));

        assertEquals(401, ex.getCode());
        assertEquals("账号已停用，请联系管理员", ex.getMessage());
    }
}
