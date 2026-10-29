package com.hr.service;

import com.hr.common.BizException;
import com.hr.common.PageResult;
import com.hr.dto.EmployeeRequest;
import com.hr.model.Employee;
import com.hr.repository.EmployeeRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Set;

@Service
public class EmployeeService {

    public static final Set<String> ALLOWED_STATUS = Set.of("在职", "试用期", "离职");

    private static final DateTimeFormatter TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int MAX_PAGE_SIZE = 100;

    private final EmployeeRepository repository;
    private final DepartmentService departmentService;

    public EmployeeService(EmployeeRepository repository, DepartmentService departmentService) {
        this.repository = repository;
        this.departmentService = departmentService;
    }

    public Employee create(EmployeeRequest request) {
        validateStatus(request.getStatus());
        if (repository.existsByPhone(request.getPhone().trim(), null)) {
            throw BizException.conflict("手机号已存在：" + request.getPhone().trim());
        }

        String now = LocalDateTime.now().format(TIME_FORMATTER);
        Employee employee = new Employee();
        applyRequest(employee, request);
        employee.setCreatedAt(now);
        employee.setUpdatedAt(now);

        long id = repository.insert(employee);
        return getDetail(id);
    }

    public PageResult<Employee> page(String name, String department, int page, int size) {
        if (page < 1) {
            throw BizException.badRequest("页码 page 必须大于等于 1");
        }
        if (size < 1 || size > MAX_PAGE_SIZE) {
            throw BizException.badRequest("每页条数 size 必须在 1 ~ " + MAX_PAGE_SIZE + " 之间");
        }
        long total = repository.count(name, department);
        List<Employee> list = repository.findPage(name, department, (page - 1) * size, size);
        return new PageResult<>(list, total, page, size);
    }

    public Employee getDetail(long id) {
        return repository.findById(id)
                .orElseThrow(() -> BizException.notFound("员工不存在或已被删除，id=" + id));
    }

    public Employee update(long id, EmployeeRequest request) {
        Employee existing = repository.findById(id)
                .orElseThrow(() -> BizException.notFound("员工不存在或已被删除，id=" + id));
        validateStatus(request.getStatus());
        if (repository.existsByPhone(request.getPhone().trim(), id)) {
            throw BizException.conflict("手机号已被其他员工占用：" + request.getPhone().trim());
        }

        applyRequest(existing, request);
        existing.setUpdatedAt(LocalDateTime.now().format(TIME_FORMATTER));
        repository.update(existing);
        return getDetail(id);
    }

    public void delete(long id) {
        repository.findById(id)
                .orElseThrow(() -> BizException.notFound("员工不存在或已被删除，id=" + id));
        repository.softDelete(id, LocalDateTime.now().format(TIME_FORMATTER));
    }

    public List<String> departments() {
        return departmentService.allNames();
    }

    private void validateStatus(String status) {
        if (!ALLOWED_STATUS.contains(status)) {
            throw BizException.badRequest("状态不合法，可选值：" + ALLOWED_STATUS);
        }
    }

    private void applyRequest(Employee employee, EmployeeRequest request) {
        employee.setName(request.getName().trim());
        employee.setPhone(request.getPhone().trim());
        employee.setDepartment(request.getDepartment().trim());
        employee.setPosition(request.getPosition().trim());
        employee.setHireDate(request.getHireDate());
        employee.setStatus(request.getStatus().trim());
    }
}
