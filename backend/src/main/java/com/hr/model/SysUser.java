package com.hr.model;

/**
 * 登录用户，仅在服务端内部流转，不直接作为接口响应体。
 */
public record SysUser(long id,
                      String username,
                      String passwordHash,
                      String salt,
                      String displayName,
                      boolean enabled) {
}
