package com.hr.controller;

import com.hr.common.ApiResponse;
import com.hr.dto.DepartmentRequest;
import com.hr.model.Department;
import com.hr.service.DepartmentService;
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
@RequestMapping("/api/departments")
public class DepartmentController {

    private final DepartmentService service;

    public DepartmentController(DepartmentService service) {
        this.service = service;
    }

    /** 部门新增 */
    @PostMapping
    public ApiResponse<Department> create(@Valid @RequestBody DepartmentRequest request) {
        return ApiResponse.success(service.create(request));
    }

    /** 部门列表查询 */
    @GetMapping
    public ApiResponse<List<Department>> list(@RequestParam(required = false) String name) {
        return ApiResponse.success(service.list(name));
    }

    /** 部门详情查看 */
    @GetMapping("/{id}")
    public ApiResponse<Department> detail(@PathVariable Long id) {
        return ApiResponse.success(service.getDetail(id));
    }

    /** 部门信息编辑 */
    @PutMapping("/{id}")
    public ApiResponse<Department> update(@PathVariable Long id, @Valid @RequestBody DepartmentRequest request) {
        return ApiResponse.success(service.update(id, request));
    }

    /** 部门删除（软删除） */
    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        service.delete(id);
        return ApiResponse.success(null);
    }

    /** 所有部门名称，供员工表单下拉使用 */
    @GetMapping("/meta/names")
    public ApiResponse<List<String>> allNames() {
        return ApiResponse.success(service.allNames());
    }
}
