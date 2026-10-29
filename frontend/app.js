const { createApp, reactive, ref, computed, onMounted } = Vue;
const { ElMessage, ElMessageBox } = ElementPlus;

const API_BASE = window.HR_API_BASE || '/api';
const STATUS_OPTIONS = ['在职', '试用期', '离职'];

const TOKEN_KEY = 'hr_token';
const USER_KEY = 'hr_user';

function readStoredUser() {
    try {
        return JSON.parse(localStorage.getItem(USER_KEY)) || null;
    } catch (e) {
        return null;
    }
}

const auth = reactive({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: readStoredUser(),
    // 本地有令牌时先乐观进入主界面，再由 /auth/me 校验真伪
    view: localStorage.getItem(TOKEN_KEY) ? 'main' : 'login'
});

function saveSession(token, user) {
    auth.token = token;
    auth.user = user;
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearSession() {
    auth.token = '';
    auth.user = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

function forceLogout(message) {
    clearSession();
    auth.view = 'login';
    ElMessage.warning(message || '登录已失效，请重新登录');
}

async function request(path, { skipAuthRedirect = false, ...options } = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (auth.token) headers['Authorization'] = 'Bearer ' + auth.token;

    let res;
    try {
        res = await fetch(API_BASE + path, { ...options, headers });
    } catch (e) {
        throw new Error('无法连接后端服务，请确认后端已启动');
    }

    const text = await res.text();
    let body = null;
    if (text) {
        try { body = JSON.parse(text); } catch (e) { body = null; }
    }
    const message = (body && body.message) || ('请求失败 (HTTP ' + res.status + ')');

    if (res.status === 401) {
        if (!skipAuthRedirect) forceLogout(message);
        throw new Error(message);
    }
    if (!res.ok) {
        throw new Error(message);
    }
    return body ? body.data : null;
}

const emptyForm = () => ({
    name: '',
    phone: '',
    department: '',
    position: '',
    hireDate: '',
    status: '在职'
});

const app = createApp({
    setup() {
        const list = ref([]);
        const total = ref(0);
        const loading = ref(false);
        const apiOnline = ref(false);
        const departments = ref([]);

        const query = reactive({ page: 1, size: 10, name: '', department: '' });

        const dialogVisible = ref(false);
        const submitting = ref(false);
        const formRef = ref(null);
        const editingId = ref(null);
        const form = reactive(emptyForm());

        const detailVisible = ref(false);
        const detailLoading = ref(false);
        const detail = ref(null);

        const loginFormRef = ref(null);
        const loginLoading = ref(false);
        const loginForm = reactive({ username: '', password: '' });

        const activeTab = ref('employee');

        // 部门管理相关
        const deptList = ref([]);
        const deptLoading = ref(false);
        const deptQuery = reactive({ name: '' });
        const deptDialogVisible = ref(false);
        const deptSubmitting = ref(false);
        const deptFormRef = ref(null);
        const editingDeptId = ref(null);
        const deptForm = reactive({ name: '', description: '', manager: '' });

        const dialogTitle = computed(() => (editingId.value ? '编辑员工信息' : '新增员工'));
        const deptDialogTitle = computed(() => (editingDeptId.value ? '编辑部门' : '新增部门'));
        const currentUserLabel = computed(() => {
            const u = auth.user;
            if (!u) return '';
            return u.displayName && u.displayName !== u.username
                ? u.displayName + '（' + u.username + '）'
                : u.username;
        });

        const rules = {
            name: [
                { required: true, message: '请输入姓名', trigger: 'blur' },
                { max: 50, message: '姓名长度不能超过50个字符', trigger: 'blur' }
            ],
            phone: [
                { required: true, message: '请输入手机号', trigger: 'blur' },
                { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确，需为11位中国大陆手机号', trigger: 'blur' }
            ],
            department: [{ required: true, message: '请选择或输入部门', trigger: 'change' }],
            position: [
                { required: true, message: '请输入岗位', trigger: 'blur' },
                { max: 50, message: '岗位长度不能超过50个字符', trigger: 'blur' }
            ],
            hireDate: [{ required: true, message: '请选择入职时间', trigger: 'change' }],
            status: [{ required: true, message: '请选择状态', trigger: 'change' }]
        };

        const deptRules = {
            name: [
                { required: true, message: '请输入部门名称', trigger: 'blur' },
                { max: 100, message: '部门名称长度不能超过100个字符', trigger: 'blur' }
            ],
            manager: [
                { max: 50, message: '负责人长度不能超过50个字符', trigger: 'blur' }
            ],
            description: [
                { max: 200, message: '描述长度不能超过200个字符', trigger: 'blur' }
            ]
        };

        const loginRules = {
            username: [
                { required: true, message: '请输入用户名', trigger: 'blur' },
                { max: 50, message: '用户名长度不能超过50个字符', trigger: 'blur' }
            ],
            password: [
                { required: true, message: '请输入密码', trigger: 'blur' },
                { max: 64, message: '密码长度不能超过64个字符', trigger: 'blur' }
            ]
        };

        function buildQuery(extra) {
            const params = new URLSearchParams();
            params.set('page', query.page);
            params.set('size', query.size);
            if (query.name && query.name.trim()) params.set('name', query.name.trim());
            if (query.department && query.department.trim()) params.set('department', query.department.trim());
            if (extra) Object.keys(extra).forEach(k => params.set(k, extra[k]));
            return params.toString();
        }

        async function loadList() {
            loading.value = true;
            try {
                const data = await request('/employees?' + buildQuery());
                list.value = data.list;
                total.value = data.total;
                apiOnline.value = true;
                if (data.list.length === 0 && data.total > 0 && query.page > 1) {
                    query.page = Math.max(1, Math.ceil(data.total / query.size));
                    return loadList();
                }
            } catch (e) {
                apiOnline.value = false;
                if (auth.token) ElMessage.error(e.message);
            } finally {
                loading.value = false;
            }
        }

        async function loadDepartments() {
            try {
                const params = deptQuery.name && deptQuery.name.trim() ? '?name=' + encodeURIComponent(deptQuery.name.trim()) : '';
                deptList.value = await request('/departments' + params);
            } catch (e) {
                deptList.value = [];
            }
        }

        async function loadDepartmentMeta() {
            try {
                departments.value = await request('/departments/meta/names');
            } catch (e) {
                departments.value = [];
            }
        }

        function indexMethod(index) {
            return (query.page - 1) * query.size + index + 1;
        }

        function statusTagType(status) {
            if (status === '在职') return 'success';
            if (status === '试用期') return 'warning';
            return 'info';
        }

        function handleSearch() {
            query.page = 1;
            loadList();
        }

        function handleReset() {
            query.name = '';
            query.department = '';
            query.page = 1;
            query.size = 10;
            loadList();
        }

        function handlePageChange(page) {
            query.page = page;
            loadList();
        }

        function handleSizeChange(size) {
            query.size = size;
            query.page = 1;
            loadList();
        }

        function fillForm(source) {
            const data = source || emptyForm();
            Object.keys(form).forEach(key => { form[key] = data[key]; });
        }

        function openCreate() {
            editingId.value = null;
            fillForm(null);
            dialogVisible.value = true;
        }

        async function openEdit(row) {
            editingId.value = row.id;
            try {
                fillForm(await request('/employees/' + row.id));
            } catch (e) {
                fillForm(row);
            }
            dialogVisible.value = true;
        }

        function editFromDetail() {
            const row = detail.value;
            detailVisible.value = false;
            if (row) openEdit(row);
        }

        function handleDialogClosed() {
            editingId.value = null;
            if (formRef.value) formRef.value.clearValidate();
            fillForm(null);
        }

        async function handleSubmit() {
            if (!formRef.value) return;
            try {
                await formRef.value.validate();
            } catch (e) {
                return;
            }

            submitting.value = true;
            const payload = {
                name: form.name.trim(),
                phone: form.phone.trim(),
                department: (form.department || '').trim(),
                position: form.position.trim(),
                hireDate: form.hireDate,
                status: form.status
            };
            try {
                if (editingId.value) {
                    await request('/employees/' + editingId.value, { method: 'PUT', body: JSON.stringify(payload) });
                    ElMessage.success('员工信息修改成功');
                } else {
                    await request('/employees', { method: 'POST', body: JSON.stringify(payload) });
                    ElMessage.success('员工新增成功');
                    query.page = 1;
                }
                dialogVisible.value = false;
                await Promise.all([loadList(), loadDepartmentMeta()]);
            } catch (e) {
                if (auth.token) ElMessage.error(e.message);
            } finally {
                submitting.value = false;
            }
        }

        async function openDetail(row) {
            detail.value = row;
            detailVisible.value = true;
            detailLoading.value = true;
            try {
                detail.value = await request('/employees/' + row.id);
            } catch (e) {
                if (auth.token) {
                    ElMessage.error(e.message);
                    detailVisible.value = false;
                }
            } finally {
                detailLoading.value = false;
            }
        }

        async function handleDelete(row) {
            try {
                await ElMessageBox.confirm(
                    '确认删除员工「' + row.name + '」吗？删除后该记录将从列表中移除（数据仍保留在库中）。',
                    '删除确认',
                    { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
                );
            } catch (e) {
                return;
            }
            try {
                await request('/employees/' + row.id, { method: 'DELETE' });
                ElMessage.success('删除成功');
                await Promise.all([loadList(), loadDepartmentMeta()]);
            } catch (e) {
                if (auth.token) ElMessage.error(e.message);
            }
        }

        // 部门管理方法
        function openDeptCreate() {
            editingDeptId.value = null;
            deptForm.name = '';
            deptForm.description = '';
            deptForm.manager = '';
            deptDialogVisible.value = true;
        }

        async function openDeptEdit(row) {
            editingDeptId.value = row.id;
            try {
                const dept = await request('/departments/' + row.id);
                deptForm.name = dept.name;
                deptForm.description = dept.description || '';
                deptForm.manager = dept.manager || '';
            } catch (e) {
                deptForm.name = row.name;
                deptForm.description = row.description || '';
                deptForm.manager = row.manager || '';
            }
            deptDialogVisible.value = true;
        }

        function handleDeptDialogClosed() {
            editingDeptId.value = null;
            if (deptFormRef.value) deptFormRef.value.clearValidate();
            deptForm.name = '';
            deptForm.description = '';
            deptForm.manager = '';
        }

        async function handleDeptSubmit() {
            if (!deptFormRef.value) return;
            try {
                await deptFormRef.value.validate();
            } catch (e) {
                return;
            }

            deptSubmitting.value = true;
            const payload = {
                name: deptForm.name.trim(),
                description: deptForm.description.trim(),
                manager: deptForm.manager.trim()
            };
            try {
                if (editingDeptId.value) {
                    await request('/departments/' + editingDeptId.value, { method: 'PUT', body: JSON.stringify(payload) });
                    ElMessage.success('部门修改成功');
                } else {
                    await request('/departments', { method: 'POST', body: JSON.stringify(payload) });
                    ElMessage.success('部门新增成功');
                }
                deptDialogVisible.value = false;
                await loadDepartments();
                await loadDepartmentMeta();
            } catch (e) {
                if (auth.token) ElMessage.error(e.message);
            } finally {
                deptSubmitting.value = false;
            }
        }

        async function handleDeptDelete(row) {
            try {
                await ElMessageBox.confirm(
                    '确认删除部门「' + row.name + '」吗？删除后该部门将从列表中移除。',
                    '删除确认',
                    { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
                );
            } catch (e) {
                return;
            }
            try {
                await request('/departments/' + row.id, { method: 'DELETE' });
                ElMessage.success('部门删除成功');
                await Promise.all([loadDepartments(), loadDepartmentMeta()]);
            } catch (e) {
                if (auth.token) ElMessage.error(e.message);
            }
        }

        async function handleLogin() {
            if (!loginFormRef.value) return;
            try {
                await loginFormRef.value.validate();
            } catch (e) {
                return;
            }

            loginLoading.value = true;
            try {
                const data = await request('/auth/login', {
                    method: 'POST',
                    body: JSON.stringify({
                        username: loginForm.username.trim(),
                        password: loginForm.password
                    }),
                    skipAuthRedirect: true
                });
                saveSession(data.token, {
                    userId: null,
                    username: data.username,
                    displayName: data.displayName
                });
                auth.view = 'main';
                loginForm.password = '';
                if (loginFormRef.value) loginFormRef.value.clearValidate();
                ElMessage.success('登录成功，欢迎 ' + (data.displayName || data.username));
                query.page = 1;
                await Promise.all([loadList(), loadDepartmentMeta(), loadDepartments()]);
            } catch (e) {
                ElMessage.error(e.message);
            } finally {
                loginLoading.value = false;
            }
        }

        async function handleLogout() {
            try {
                await ElMessageBox.confirm('确认退出登录吗？', '退出确认',
                    { type: 'warning', confirmButtonText: '退出登录', cancelButtonText: '取消' });
            } catch (e) {
                return;
            }
            clearSession();
            auth.view = 'login';
            list.value = [];
            total.value = 0;
            departments.value = [];
            deptList.value = [];
            apiOnline.value = false;
            dialogVisible.value = false;
            detailVisible.value = false;
            deptDialogVisible.value = false;
            ElMessage.success('已退出登录');
        }

        async function restoreSession() {
            try {
                const me = await request('/auth/me');
                auth.user = { userId: me.userId, username: me.username, displayName: me.displayName };
                localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
            } catch (e) {
                if (!auth.token) return;
            }
            await Promise.all([loadList(), loadDepartmentMeta(), loadDepartments()]);
        }

        async function probeHealth() {
            try {
                await fetch(API_BASE + '/health');
                apiOnline.value = true;
            } catch (e) {
                apiOnline.value = false;
            }
        }

        onMounted(() => {
            probeHealth();
            if (auth.token) restoreSession();
        });

        return {
            auth, list, total, loading, apiOnline, departments, query,
            dialogVisible, dialogTitle, submitting, formRef, form, rules, statusOptions: STATUS_OPTIONS,
            detailVisible, detailLoading, detail,
            loginFormRef, loginForm, loginRules, loginLoading, currentUserLabel,
            activeTab,
            deptList, deptLoading, deptQuery, deptDialogVisible, deptDialogTitle, deptSubmitting, deptFormRef, deptForm, deptRules,
            indexMethod, statusTagType,
            handleSearch, handleReset, handlePageChange, handleSizeChange,
            openCreate, openEdit, editFromDetail, handleDialogClosed, handleSubmit,
            openDetail, handleDelete,
            openDeptCreate, openDeptEdit, handleDeptDialogClosed, handleDeptSubmit, handleDeptDelete,
            handleLogin, handleLogout
        };
    }
});

app.use(ElementPlus, { locale: window.ElementPlusLocaleZhCn });
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(name, component);
}
app.mount('#app');
