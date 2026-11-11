# -*- coding: utf-8 -*-
"""
页面对象 - 员工管理页
封装员工管理页面的所有交互操作，遵循 Page Object 模式
"""
from common.ui_base import BasePage
from common.logger import logger


class EmployeePage(BasePage):
    """
    员工管理页面 Page Object
    
    Attributes:
        TABLE: 员工数据表格定位器
        TABLE_ROWS: 表格数据行定位器
        SEARCH_NAME_INPUT: 姓名搜索输入框定位器
        SEARCH_DEPT_INPUT: 部门搜索输入框定位器
        SEARCH_BUTTON: 搜索按钮定位器
        ADD_BUTTON: 新增员工按钮定位器
        EDIT_BUTTON: 编辑按钮定位器（行内）
        DELETE_BUTTON: 删除按钮定位器（行内）
        PAGINATION: 分页组件定位器
    """
    
    # 定位器
    TABLE = ("css", ".el-table")
    TABLE_ROWS = ("css", ".el-table__body-wrapper tbody tr")
    SEARCH_NAME_INPUT = ("css", "input[placeholder*='姓名']")
    SEARCH_DEPT_INPUT = ("css", "input[placeholder*='部门']")
    SEARCH_BUTTON = ("css", ".btn-search")
    ADD_BUTTON = ("css", ".btn-add")
    EDIT_BUTTON = ("css", ".btn-edit")
    DELETE_BUTTON = ("css", ".btn-delete")
    PAGINATION = ("css", ".el-pagination")
    
    def __init__(self, driver):
        """
        初始化员工管理页对象
        
        Args:
            driver: Selenium WebDriver 实例
        """
        super().__init__(driver)
    
    def open_employee_page(self, base_url):
        """
        打开员工管理页面
        
        Args:
            base_url: 服务基础地址（如 http://localhost:8080）
            
        Returns:
            EmployeePage: 返回自身实例，支持链式调用
        """
        self.open(f"{base_url}/employees")
        return self
    
    def search_by_name(self, name):
        """
        按姓名进行搜索
        
        Args:
            name: 要搜索的员工姓名（支持模糊匹配）
            
        Returns:
            EmployeePage: 返回自身实例，支持链式调用
        """
        logger.info(f"[EmployeePage] 搜索姓名: {name}")
        self.input_text(self.SEARCH_NAME_INPUT, name)
        self.click(self.SEARCH_BUTTON)
        return self
    
    def search_by_department(self, department):
        """
        按部门进行搜索
        
        Args:
            department: 要搜索的部门名称（支持模糊匹配）
            
        Returns:
            EmployeePage: 返回自身实例，支持链式调用
        """
        logger.info(f"[EmployeePage] 搜索部门: {department}")
        self.input_text(self.SEARCH_DEPT_INPUT, department)
        self.click(self.SEARCH_BUTTON)
        return self
    
    def get_table_row_count(self):
        """
        获取当前表格中的数据行数
        
        Returns:
            int: 表格行数
        """
        elements = self.driver.find_elements(*self.TABLE_ROWS)
        count = len(elements)
        logger.info(f"[EmployeePage] 表格行数: {count}")
        return count
    
    def click_add_button(self):
        """
        点击新增员工按钮
        
        Returns:
            EmployeePage: 返回自身实例，支持链式调用
        """
        logger.info("[EmployeePage] 点击新增")
        self.click(self.ADD_BUTTON)
        return self
    
    def click_edit_button(self, row_index=0):
        """
        点击指定行的编辑按钮
        
        Args:
            row_index: 行索引（从 0 开始），默认第一行
            
        Returns:
            EmployeePage: 返回自身实例，支持链式调用
        """
        logger.info(f"[EmployeePage] 点击编辑: 行 {row_index}")
        rows = self.driver.find_elements(*self.TABLE_ROWS)
        if row_index < len(rows):
            edit_btn = rows[row_index].find_element(*self.EDIT_BUTTON)
            edit_btn.click()
        return self
    
    def click_delete_button(self, row_index=0):
        """
        点击指定行的删除按钮
        
        Args:
            row_index: 行索引（从 0 开始），默认第一行
            
        Returns:
            EmployeePage: 返回自身实例，支持链式调用
        """
        logger.info(f"[EmployeePage] 点击删除: 行 {row_index}")
        rows = self.driver.find_elements(*self.TABLE_ROWS)
        if row_index < len(rows):
            delete_btn = rows[row_index].find_element(*self.DELETE_BUTTON)
            delete_btn.click()
        return self
    
    def is_pagination_visible(self):
        """
        判断分页组件是否可见
        
        Returns:
            bool: 分页组件可见返回 True，否则返回 False
        """
        return self.is_element_present(self.PAGINATION)
