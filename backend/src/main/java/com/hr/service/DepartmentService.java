package com.hr.service;

import com.hr.common.BizException;
import com.hr.dto.DepartmentRequest;
import com.hr.model.Department;
import com.hr.repository.DepartmentRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class DepartmentService {

    private final DepartmentRepository repository;

    public DepartmentService(DepartmentRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public Department create(DepartmentRequest request) {
        if (repository.existsByNameAndDeleted(request.getName(), 0)) {
            throw new BizException("部门名称已存在");
        }
        Department dept = new Department();
        dept.setName(request.getName().trim());
        dept.setDescription(request.getDescription() != null ? request.getDescription().trim() : null);
        dept.setManager(request.getManager() != null ? request.getManager().trim() : null);
        return repository.save(dept);
    }

    public List<Department> list(String name) {
        return repository.search(name);
    }

    public Department getDetail(Long id) {
        return repository.findByIdAndDeleted(id, 0)
                .orElseThrow(() -> new BizException("部门不存在或已删除"));
    }

    @Transactional
    public Department update(Long id, DepartmentRequest request) {
        Department dept = getDetail(id);
        if (!dept.getName().equals(request.getName()) &&
            repository.existsByNameAndDeleted(request.getName(), 0)) {
            throw new BizException("部门名称已存在");
        }
        dept.setName(request.getName().trim());
        dept.setDescription(request.getDescription() != null ? request.getDescription().trim() : null);
        dept.setManager(request.getManager() != null ? request.getManager().trim() : null);
        return repository.save(dept);
    }

    @Transactional
    public void delete(Long id) {
        Department dept = getDetail(id);
        dept.setDeleted(1);
        repository.save(dept);
    }

    public List<String> allNames() {
        return repository.search(null).stream()
                .map(Department::getName)
                .distinct()
                .sorted()
                .toList();
    }
}
