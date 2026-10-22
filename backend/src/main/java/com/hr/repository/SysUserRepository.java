package com.hr.repository;

import com.hr.model.SysUser;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public class SysUserRepository {

    private static final String COLUMNS =
            "id, username, password_hash, salt, display_name, enabled";

    private static final RowMapper<SysUser> MAPPER = (rs, rowNum) -> new SysUser(
            rs.getLong("id"),
            rs.getString("username"),
            rs.getString("password_hash"),
            rs.getString("salt"),
            rs.getString("display_name"),
            rs.getInt("enabled") == 1);

    private final JdbcTemplate jdbcTemplate;

    public SysUserRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Optional<SysUser> findByUsername(String username) {
        String sql = "SELECT " + COLUMNS + " FROM sys_user WHERE username = ?";
        return jdbcTemplate.query(sql, MAPPER, username).stream().findFirst();
    }

    public long count() {
        Long total = jdbcTemplate.queryForObject("SELECT COUNT(1) FROM sys_user", Long.class);
        return total == null ? 0L : total;
    }

    public void insert(String username, String passwordHash, String salt, String displayName, String now) {
        jdbcTemplate.update(
                "INSERT INTO sys_user (username, password_hash, salt, display_name, enabled, created_at, updated_at) "
                        + "VALUES (?, ?, ?, ?, 1, ?, ?)",
                username, passwordHash, salt, displayName, now, now);
    }
}
