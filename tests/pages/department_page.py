# -*- coding: utf-8 -*-
"""
页面对象 - 部门管理页
封装部门管理页面的所有交互操作，遵循 Page Object 模式
"""
from common.ui_base import BasePage
from common.logger import logger


class DepartmentPage(BasePage):
    """
    部门管理页面 Page Object
    
    Attributes:
        TABLE: 部门数据表格定位器
        TABLE_ROWS: 表格数据行定位器
        SEARCH_INPUT: 部门名称搜索输入框定位器
        SEARCH_BUTTON: 搜索按钮定位器
        ADD_BUTTON: 新增部门按钮定位器
    """
    
    # 定位器
    TABLE = ("css", ".el-table")
    TABLE_ROWS = ("css", ".el-table__body-wrapper tbody tr")
    SEARCH_INPUT = ("css", "input[placeholder*='部门']")
    SEARCH_BUTTON = ("css", ".btn-search")
    ADD_BUTTON = ("css", ".btn-add")
    
    def __init__(self, driver):
        """
        初始化部门管理页对象
        
        Args:
            driver: Selenium WebDriver 实例
        """
        super().__init__(driver)
    
    def open_department_page(self, base_url):
        """
        打开部门管理页面
        
        Args:
            base_url: 服务基础地址（如 http://localhost:8080）
            
        Returns:
            DepartmentPage: 返回自身实例，支持链式调用
        """
        self.open(f"{base_url}/departments")
        return self
    
    def search_by_name(self, name):
        """
        按部门名称进行搜索
        
        Args:
            name: 要搜索的部门名称（支持模糊匹配）
            
        Returns:
            DepartmentPage: 返回自身实例，支持链式调用
        """
        logger.info(f"[DepartmentPage] 搜索: {name}")
        self.input_text(self.SEARCH_INPUT, name)
        self.click(self.SEARCH_BUTTON)
        return self
    
    def get_table_row_count(self):
        """
        获取当前表格中的数据行数
        
        Returns:
            int: 表格行数
        """
        elements = self.driver.find_elements(*self.TABLE_ROWS)
        return len(elements)
    
    def click_add_button(self):
        """
        点击新增部门按钮
        
        Returns:
            DepartmentPage: 返回自身实例，支持链式调用
        """
        self.click(self.ADD_BUTTON)
        return self
