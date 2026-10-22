package com.hr.config;

import com.hr.repository.SysUserRepository;
import com.hr.security.PasswordHasher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * 首次启动时向空的 sys_user 表写入预置登录账号。
 * 放在 ApplicationRunner 而非 schema.sql，是因为口令哈希必须在运行时计算。
 */
@Component
public class UserDataInitializer implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(UserDataInitializer.class);
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final SysUserRepository userRepository;
    private final String username;
    private final String password;
    private final String displayName;

    public UserDataInitializer(SysUserRepository userRepository,
                               @Value("${hr.auth.default-username}") String username,
                               @Value("${hr.auth.default-password}") String password,
                               @Value("${hr.auth.default-display-name}") String displayName) {
        this.userRepository = userRepository;
        this.username = username;
        this.password = password;
        this.displayName = displayName;
    }

    @Override
    public void run(ApplicationArguments args) {
        if (userRepository.count() > 0) {
            return;
        }
        String salt = PasswordHasher.newSalt();
        String now = LocalDateTime.now().format(TIME);
        userRepository.insert(username, PasswordHasher.hash(password, salt), salt, displayName, now);
        log.info("sys_user 表为空，已初始化预置登录账号：{}", username);
    }
}
