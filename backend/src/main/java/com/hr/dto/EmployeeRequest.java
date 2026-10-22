package com.hr.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.time.LocalDate;

/**
 * 新增 / 编辑员工的请求体。
 */
public class EmployeeRequest {

    @NotBlank(message = "姓名不能为空")
    @Size(max = 50, message = "姓名长度不能超过50个字符")
    private String name;

    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确，需为11位中国大陆手机号")
    private String phone;

    @NotBlank(message = "部门不能为空")
    @Size(max = 50, message = "部门长度不能超过50个字符")
    private String department;

    @NotBlank(message = "岗位不能为空")
    @Size(max = 50, message = "岗位长度不能超过50个字符")
    private String position;

    @NotNull(message = "入职时间不能为空")
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate hireDate;

    @NotBlank(message = "状态不能为空")
    private String status;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getPhone() {
        return phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }

    public String getDepartment() {
        return department;
    }

    public void setDepartment(String department) {
        this.department = department;
    }

    public String getPosition() {
        return position;
    }

    public void setPosition(String position) {
        this.position = position;
    }

    public LocalDate getHireDate() {
        return hireDate;
    }

    public void setHireDate(LocalDate hireDate) {
        this.hireDate = hireDate;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
