package com.hr.dto;

/**
 * 当前登录用户信息，用于前端展示与刷新页面后恢复登录态。
 */
public record UserInfo(long userId, String username, String displayName) {
}
