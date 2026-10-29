package com.hr.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public class DepartmentRequest {

    @NotBlank(message = "部门名称不能为空")
    @Size(max = 100, message = "部门名称长度不能超过100个字符")
    private String name;

    @Size(max = 200, message = "部门描述长度不能超过200个字符")
    private String description;

    @Size(max = 50, message = "部门负责人长度不能超过50个字符")
    private String manager;

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public String getManager() { return manager; }
    public void setManager(String manager) { this.manager = manager; }
}
