package com.hr.repository;

import com.hr.model.Employee;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Repository
public class EmployeeRepository {

    private static final String COLUMNS =
            "id, name, phone, department, position, hire_date, status, created_at, updated_at";

    private static final RowMapper<Employee> MAPPER = (rs, rowNum) -> {
        Employee e = new Employee();
        e.setId(rs.getLong("id"));
        e.setName(rs.getString("name"));
        e.setPhone(rs.getString("phone"));
        e.setDepartment(rs.getString("department"));
        e.setPosition(rs.getString("position"));
        e.setHireDate(LocalDate.parse(rs.getString("hire_date")));
        e.setStatus(rs.getString("status"));
        e.setCreatedAt(rs.getString("created_at"));
        e.setUpdatedAt(rs.getString("updated_at"));
        return e;
    };

    private final JdbcTemplate jdbcTemplate;

    public EmployeeRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public long insert(Employee e) {
        String sql = "INSERT INTO employee (name, phone, department, position, hire_date, status, deleted, created_at, updated_at) "
                + "VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)";
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, e.getName());
            ps.setString(2, e.getPhone());
            ps.setString(3, e.getDepartment());
            ps.setString(4, e.getPosition());
            ps.setString(5, e.getHireDate().toString());
            ps.setString(6, e.getStatus());
            ps.setString(7, e.getCreatedAt());
            ps.setString(8, e.getUpdatedAt());
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            throw new IllegalStateException("新增员工失败，无法获取主键");
        }
        return key.longValue();
    }

    public Optional<Employee> findById(long id) {
        String sql = "SELECT " + COLUMNS + " FROM employee WHERE id = ? AND deleted = 0";
        return jdbcTemplate.query(sql, MAPPER, id).stream().findFirst();
    }

    public List<Employee> findPage(String name, String department, int offset, int limit) {
        StringBuilder sql = new StringBuilder("SELECT " + COLUMNS + " FROM employee WHERE deleted = 0");
        List<Object> args = new ArrayList<>();
        appendFilters(sql, args, name, department);
        sql.append(" ORDER BY id DESC LIMIT ? OFFSET ?");
        args.add(limit);
        args.add(offset);
        return jdbcTemplate.query(sql.toString(), MAPPER, args.toArray());
    }

    public long count(String name, String department) {
        StringBuilder sql = new StringBuilder("SELECT COUNT(1) FROM employee WHERE deleted = 0");
        List<Object> args = new ArrayList<>();
        appendFilters(sql, args, name, department);
        Long total = jdbcTemplate.queryForObject(sql.toString(), Long.class, args.toArray());
        return total == null ? 0L : total;
    }

    public int update(Employee e) {
        String sql = "UPDATE employee SET name = ?, phone = ?, department = ?, position = ?, hire_date = ?, "
                + "status = ?, updated_at = ? WHERE id = ? AND deleted = 0";
        return jdbcTemplate.update(sql,
                e.getName(), e.getPhone(), e.getDepartment(), e.getPosition(),
                e.getHireDate().toString(), e.getStatus(), e.getUpdatedAt(), e.getId());
    }

    public int softDelete(long id, String now) {
        return jdbcTemplate.update(
                "UPDATE employee SET deleted = 1, updated_at = ? WHERE id = ? AND deleted = 0", now, id);
    }

    public boolean existsByPhone(String phone, Long excludeId) {
        if (excludeId == null) {
            Integer c = jdbcTemplate.queryForObject(
                    "SELECT COUNT(1) FROM employee WHERE deleted = 0 AND phone = ?", Integer.class, phone);
            return c != null && c > 0;
        }
        Integer c = jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM employee WHERE deleted = 0 AND phone = ? AND id <> ?",
                Integer.class, phone, excludeId);
        return c != null && c > 0;
    }

    public List<String> findDepartments() {
        return jdbcTemplate.queryForList(
                "SELECT DISTINCT department FROM employee WHERE deleted = 0 ORDER BY department", String.class);
    }

    private void appendFilters(StringBuilder sql, List<Object> args, String name, String department) {
        if (name != null && !name.isBlank()) {
            sql.append(" AND name LIKE ?");
            args.add("%" + name.trim() + "%");
        }
        if (department != null && !department.isBlank()) {
            sql.append(" AND department LIKE ?");
            args.add("%" + department.trim() + "%");
        }
    }
}
