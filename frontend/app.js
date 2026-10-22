const { createApp, reactive, ref, computed, onMounted } = Vue;
const { ElMessage, ElMessageBox } = ElementPlus;

const API_BASE = window.HR_API_BASE || 'http://localhost:8080/api';
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
        throw new Error('无法连接后端服务，请确认 http://localhost:8080 已启动');
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

        const dialogTitle = computed(() => (editingId.value ? '编辑员工信息' : '新增员工'));
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
                // 删除最后一页的唯一记录后，回退一页
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
                departments.value = await request('/employees/meta/departments');
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
                await Promise.all([loadList(), loadDepartments()]);
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
                await Promise.all([loadList(), loadDepartments()]);
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
                await Promise.all([loadList(), loadDepartments()]);
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
            apiOnline.value = false;
            dialogVisible.value = false;
            detailVisible.value = false;
            ElMessage.success('已退出登录');
        }

        async function restoreSession() {
            try {
                const me = await request('/auth/me');
                auth.user = { userId: me.userId, username: me.username, displayName: me.displayName };
                localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
            } catch (e) {
                if (!auth.token) return; // 令牌失效，forceLogout 已切回登录页
            }
            await Promise.all([loadList(), loadDepartments()]);
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
            indexMethod, statusTagType,
            handleSearch, handleReset, handlePageChange, handleSizeChange,
            openCreate, openEdit, editFromDetail, handleDialogClosed, handleSubmit,
            openDetail, handleDelete, handleLogin, handleLogout
        };
    }
});

app.use(ElementPlus, { locale: window.ElementPlusLocaleZhCn });
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(name, component);
}
app.mount('#app');
