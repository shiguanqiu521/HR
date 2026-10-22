package com.hr.controller;

import com.hr.common.ApiResponse;
import com.hr.common.PageResult;
import com.hr.dto.EmployeeRequest;
import com.hr.model.Employee;
import com.hr.service.EmployeeService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/employees")
public class EmployeeController {

    private final EmployeeService service;

    public EmployeeController(EmployeeService service) {
        this.service = service;
    }

    /** 员工新增 */
    @PostMapping
    public ApiResponse<Employee> create(@Valid @RequestBody EmployeeRequest request) {
        return ApiResponse.success(service.create(request));
    }

    /** 员工列表查询：分页 + 按姓名/部门筛选 */
    @GetMapping
    public ApiResponse<PageResult<Employee>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String department) {
        return ApiResponse.success(service.page(name, department, page, size));
    }

    /** 员工详情查看 */
    @GetMapping("/{id}")
    public ApiResponse<Employee> detail(@PathVariable long id) {
        return ApiResponse.success(service.getDetail(id));
    }

    /** 员工信息编辑 */
    @PutMapping("/{id}")
    public ApiResponse<Employee> update(@PathVariable long id, @Valid @RequestBody EmployeeRequest request) {
        return ApiResponse.success(service.update(id, request));
    }

    /** 员工删除（软删除） */
    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable long id) {
        service.delete(id);
        return ApiResponse.success(null);
    }

    /** 部门字典，供前端筛选下拉使用 */
    @GetMapping("/meta/departments")
    public ApiResponse<List<String>> departments() {
        return ApiResponse.success(service.departments());
    }
}
