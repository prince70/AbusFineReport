from flask import Flask, request, jsonify, session, send_from_directory, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import importlib.util
import importlib
import sqlite3
from datetime import datetime, timedelta
import random
import os

from backend.services.assembly_service import (
    build_assembly_export_file,
    parse_assembly_filters,
    query_assembly_data,
    query_workshops,
)
from backend.services.checklist_service import query_checklist_data, query_finished_qty_all

app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get('SECRET_KEY', 'production-query-secret-key-2024')
app.config['JSON_AS_ASCII'] = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DB_FILE = os.path.join(PROJECT_ROOT, 'production.db')

DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')
SQLSERVER_CONFIG = {
    'server': os.environ.get('DB_SERVER', '192.168.41.57'),
    'database': os.environ.get('DB_NAME', 'department2020'),
    'user': os.environ.get('DB_USER', 'sa'),
    'password': os.environ.get('DB_PASSWORD', '3518i')
}

def get_db_connection():
    return sqlite3.connect(DB_FILE)


def get_sqlserver_connection():
    if importlib.util.find_spec('pyodbc') is None:
        raise RuntimeError('缺少 pyodbc 依赖，请先安装 requirements.txt')

    pyodbc = importlib.import_module('pyodbc')
    driver = os.environ.get('DB_DRIVER', 'ODBC Driver 18 for SQL Server')
    server = os.environ.get('DB_SERVER', '192.168.41.57')
    database = os.environ.get('DB_NAME', 'department2020')
    user = os.environ.get('DB_USER', 'sa')
    password = os.environ.get('DB_PASSWORD', '3518i')
    trust_cert = os.environ.get('DB_TRUST_CERTIFICATE', 'yes')
    encrypt = os.environ.get('DB_ENCRYPT', 'no')

    connection_string = (
        f'DRIVER={{{driver}}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={user};'
        f'PWD={password};'
        f'Encrypt={encrypt};'
        f'TrustServerCertificate={trust_cert};'
    )
    return pyodbc.connect(connection_string, timeout=10)


def get_menu_paths_for_permission_codes(permission_codes):
    paths = {'/dashboard'}
    permission_to_paths = {
        'assembly:query': ['/assembly'],
        'checklist:query': ['/list', '/list/grinding', '/list/key', '/list/body', '/list/beam', '/list/core'],
        'user:view': ['/system/users'],
        'role:view': ['/system/roles'],
    }

    for code in permission_codes or []:
        for path in permission_to_paths.get(code, []):
            paths.add(path)

    return paths


def get_menu_ids_for_paths(cursor, menu_paths):
    cursor.execute('SELECT id, path, parent_id FROM menus')
    menus = cursor.fetchall()
    menus_by_path = {row[1]: {'id': row[0], 'parent_id': row[2]} for row in menus}
    menus_by_id = {row[0]: {'id': row[0], 'parent_id': row[2]} for row in menus}

    menu_ids = set()
    for path in menu_paths or []:
        current = menus_by_path.get(path)
        while current:
            menu_ids.add(current['id'])
            parent_id = current['parent_id']
            current = menus_by_id.get(parent_id)

    return menu_ids


def sync_role_menus_from_permissions(cursor, role_id):
    cursor.execute('''SELECT DISTINCT p.code FROM permissions p
                     JOIN role_permissions rp ON p.id = rp.permission_id
                     WHERE rp.role_id = ?''', (role_id,))
    permission_codes = [row[0] for row in cursor.fetchall()]
    menu_paths = get_menu_paths_for_permission_codes(permission_codes)
    menu_ids = get_menu_ids_for_paths(cursor, menu_paths)

    cursor.execute('DELETE FROM role_menus WHERE role_id = ?', (role_id,))
    for menu_id in menu_ids:
        cursor.execute('INSERT OR IGNORE INTO role_menus (role_id, menu_id) VALUES (?, ?)', (role_id, menu_id))

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  nickname TEXT,
                  email TEXT,
                  status INTEGER DEFAULT 1,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS roles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL,
                  description TEXT,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS permissions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL,
                  code TEXT UNIQUE NOT NULL,
                  type TEXT,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS role_permissions
                 (role_id INTEGER,
                  permission_id INTEGER,
                  PRIMARY KEY (role_id, permission_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_roles
                 (user_id INTEGER,
                  role_id INTEGER,
                  PRIMARY KEY (user_id, role_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS menus
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  path TEXT,
                  icon TEXT,
                  parent_id INTEGER,
                  order_num INTEGER,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS role_menus
                 (role_id INTEGER,
                  menu_id INTEGER,
                  PRIMARY KEY (role_id, menu_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS assembly_progress
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  订单号 TEXT,
                  料品编码 TEXT,
                  料品名称 TEXT,
                  料品规格 TEXT,
                  生产车间 TEXT,
                  计划数量 INTEGER,
                  已完成数量 INTEGER,
                  进行中数量 INTEGER,
                  未开始数量 INTEGER,
                  完成率 REAL,
                  计划开始日期 TEXT,
                  计划结束日期 TEXT,
                  实际开始日期 TEXT,
                  实际结束日期 TEXT,
                  进度状态 TEXT,
                  备注 TEXT)''')

    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, nickname, status) VALUES (?, ?, ?, ?)",
                  ('admin', generate_password_hash('admin123'), '系统管理员', 1))
        c.execute("INSERT INTO users (username, password, nickname, status) VALUES (?, ?, ?, ?)",
                  ('user', generate_password_hash('user123'), '普通用户', 1))
    
    c.execute('SELECT COUNT(*) FROM roles')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO roles (name, description) VALUES (?, ?)", ('超级管理员', '拥有所有权限'))
        c.execute("INSERT INTO roles (name, description) VALUES (?, ?)", ('普通用户', '普通操作权限'))
        c.execute("INSERT INTO roles (name, description) VALUES (?, ?)", ('访客', '只读权限'))
    
    c.execute('SELECT COUNT(*) FROM permissions')
    if c.fetchone()[0] == 0:
        perms = [
            ('用户管理', 'user:view', 'button'),
            ('用户新增', 'user:add', 'button'),
            ('用户编辑', 'user:edit', 'button'),
            ('用户删除', 'user:delete', 'button'),
            ('角色管理', 'role:view', 'button'),
            ('角色新增', 'role:add', 'button'),
            ('角色编辑', 'role:edit', 'button'),
            ('角色删除', 'role:delete', 'button'),
            ('装嵌进度查询', 'assembly:query', 'menu'),
            ('外协加工清单查询', 'checklist:query', 'menu'),
            ('装嵌进度导出', 'assembly:export', 'button'),
        ]
        for name, code, ptype in perms:
            c.execute("INSERT INTO permissions (name, code, type) VALUES (?, ?, ?)", (name, code, ptype))

    # Ensure checklist query permission exists for existing databases.
    c.execute("SELECT id FROM permissions WHERE code = ?", ('checklist:query',))
    checklist_perm = c.fetchone()
    if not checklist_perm:
        c.execute("INSERT INTO permissions (name, code, type) VALUES (?, ?, ?)", ('外协加工清单查询', 'checklist:query', 'menu'))
        checklist_perm_id = c.lastrowid
    else:
        checklist_perm_id = checklist_perm[0]
    
    c.execute('SELECT COUNT(*) FROM menus')
    if c.fetchone()[0] == 0:
        menus = [
            ('首页', '/dashboard', 'el-icon-s-home', 0, 1),
            ('装嵌生产进度', '/assembly', 'el-icon-document', 0, 2),
            ('系统管理', '/system', 'el-icon-setting', 0, 3),
            ('用户管理', '/system/users', 'el-icon-user', 3, 1),
            ('角色管理', '/system/roles', 'el-icon-postcard', 3, 2),
        ]
        for name, path, icon, parent, order in menus:
            c.execute("INSERT INTO menus (name, path, icon, parent_id, order_num) VALUES (?, ?, ?, ?, ?)",
                      (name, path, icon, parent if parent else None, order))
    
    c.execute('SELECT COUNT(*) FROM role_permissions')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (1, 1)")
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (1, 2)")
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (1, 3)")
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (1, 4)")
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (1, 5)")
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (1, 6)")
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (1, 7)")
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (1, 8)")
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (1, 9)")
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (1, 10)")
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (2, 9)")
        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (2, 10)")

    # Ensure admin and normal user have checklist query permission.
    c.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)', (1, checklist_perm_id))
    c.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)', (2, checklist_perm_id))

    c.execute('SELECT id FROM roles')
    for row in c.fetchall():
        sync_role_menus_from_permissions(c, row[0])

    # Ensure the checklist parent menu and workshop sub-menus exist.
    c.execute("SELECT id FROM menus WHERE path = '/list'")
    parent = c.fetchone()
    if not parent:
        c.execute(
            "INSERT INTO menus (name, path, icon, parent_id, order_num) VALUES (?, ?, ?, ?, ?)",
            ('外协加工清单', '/list', 'el-icon-document', None, 4)
        )
        checklist_parent_id = c.lastrowid
    else:
        checklist_parent_id = parent[0]
        c.execute(
            "UPDATE menus SET name = ?, icon = ?, parent_id = ?, order_num = ? WHERE id = ?",
            ('外协加工清单', 'el-icon-document', None, 4, checklist_parent_id)
        )

    workshop_menus = [
        ('打磨车间', '/list/grinding', 1),
        ('钥匙车间', '/list/key', 2),
        ('锁体车间', '/list/body', 3),
        ('锁梁车间', '/list/beam', 4),
        ('锁芯车间', '/list/core', 5),
    ]

    for name, path, order_num in workshop_menus:
        c.execute("SELECT id FROM menus WHERE path = ?", (path,))
        row = c.fetchone()
        if not row:
            c.execute(
                "INSERT INTO menus (name, path, icon, parent_id, order_num) VALUES (?, ?, ?, ?, ?)",
                (name, path, 'el-icon-document', checklist_parent_id, order_num)
            )
            menu_id = c.lastrowid
        else:
            menu_id = row[0]
            c.execute(
                "UPDATE menus SET name = ?, icon = ?, parent_id = ?, order_num = ? WHERE id = ?",
                (name, 'el-icon-document', checklist_parent_id, order_num, menu_id)
            )

        c.execute('INSERT OR IGNORE INTO role_menus (role_id, menu_id) VALUES (?, ?)', (1, menu_id))
        c.execute('INSERT OR IGNORE INTO role_menus (role_id, menu_id) VALUES (?, ?)', (2, menu_id))

    c.execute('INSERT OR IGNORE INTO role_menus (role_id, menu_id) VALUES (?, ?)', (1, checklist_parent_id))
    c.execute('INSERT OR IGNORE INTO role_menus (role_id, menu_id) VALUES (?, ?)', (2, checklist_parent_id))

    c.execute('SELECT id FROM roles')
    for row in c.fetchall():
        sync_role_menus_from_permissions(c, row[0])
    
    c.execute('SELECT COUNT(*) FROM user_roles')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO user_roles (user_id, role_id) VALUES (1, 1)")
        c.execute("INSERT INTO user_roles (user_id, role_id) VALUES (2, 2)")
    
    c.execute('SELECT COUNT(*) FROM assembly_progress')
    if c.fetchone()[0] == 0:
        workshops = ['装配车间A', '装配车间B', '装配车间C', '测试车间']
        statuses = ['已完成', '进行中', '未开始', '已逾期', '即将逾期']
        for i in range(200):
            plan_qty = random.randint(100, 5000)
            completed = random.randint(0, plan_qty)
            in_progress = random.randint(0, plan_qty - completed)
            not_started = plan_qty - completed - in_progress
            start = datetime.now() - timedelta(days=random.randint(1, 60))
            end = start + timedelta(days=random.randint(5, 30))
            actual_start = start + timedelta(days=random.randint(0, 3))
            status = random.choice(statuses)
            rate = round(completed / plan_qty * 100, 1) if plan_qty > 0 else 0
            
            c.execute("""INSERT INTO assembly_progress (订单号, 料品编码, 料品名称, 料品规格, 生产车间, 计划数量, 已完成数量, 进行中数量, 未开始数量, 完成率, 计划开始日期, 计划结束日期, 实际开始日期, 实际结束日期, 进度状态, 备注) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (f'ORD-{random.randint(10000, 99999)}',
                       f'LP{random.randint(100000, 999999)}',
                       random.choice(['产品A', '产品B', '产品C', '产品D', '组件X', '组件Y']),
                       f'规格-{random.randint(1, 20)}',
                       random.choice(workshops),
                       plan_qty, completed, in_progress, not_started, rate,
                       start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'),
                       actual_start.strftime('%Y-%m-%d'), (actual_start + timedelta(days=random.randint(5, 25))).strftime('%Y-%m-%d'),
                       status, f'备注-{random.randint(1, 100)}'))
    
    conn.commit()
    conn.close()

init_db()

def require_login(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        return handler(*args, **kwargs)
    return wrapped

def require_permission(permission_code):
    def decorator(handler):
        @wraps(handler)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
            if permission_code not in get_user_permissions(session['user_id']):
                return jsonify({'status': 'error', 'message': 'No permission'}), 403
            return handler(*args, **kwargs)
        return wrapped
    return decorator

def get_user_permissions(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT DISTINCT p.code FROM permissions p
                 JOIN role_permissions rp ON p.id = rp.permission_id
                 JOIN user_roles ur ON rp.role_id = ur.role_id
                 WHERE ur.user_id = ?''', (user_id,))
    perms = [row[0] for row in c.fetchall()]
    conn.close()
    return perms

def get_user_menus(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT DISTINCT m.id, m.name, m.path, m.icon, m.parent_id, m.order_num
                 FROM menus m
                 JOIN role_menus rm ON m.id = rm.menu_id
                 JOIN user_roles ur ON rm.role_id = ur.role_id
                 WHERE ur.user_id = ?
                 ORDER BY m.order_num''', (user_id,))
    menus = c.fetchall()
    conn.close()
    return menus

def build_menu_tree(menus):
    menu_dict = {}
    for m in menus:
        menu_dict[m[0]] = {'id': m[0], 'name': m[1], 'path': m[2], 'icon': m[3], 'parentId': m[4], 'orderNum': m[5], 'children': []}
    
    result = []
    for m in menus:
        if m[4] is None:
            result.append(menu_dict[m[0]])
        else:
            parent = menu_dict.get(m[4])
            if parent:
                parent['children'].append(menu_dict[m[0]])
    
    return result

@app.route('/api/check-login', methods=['GET'])
def check_login():
    if 'user_id' in session:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT id, username, nickname FROM users WHERE id = ?', (session['user_id'],))
        user = c.fetchone()
        conn.close()
        if user:
            permissions = get_user_permissions(user[0])
            menus = get_user_menus(user[0])
            return jsonify({
                'status': 'success',
                'loggedIn': True,
                'user': {'id': user[0], 'username': user[1], 'nickname': user[2]},
                'permissions': permissions,
                'menus': build_menu_tree(menus)
            })
    return jsonify({'status': 'success', 'loggedIn': False})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, password, nickname FROM users WHERE username = ? AND status = 1', (username,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password_hash(user[2], password):
        session['user_id'] = user[0]
        session['username'] = user[1]
        permissions = get_user_permissions(user[0])
        menus = get_user_menus(user[0])
        return jsonify({
            'status': 'success',
            'user': {'id': user[0], 'username': user[1], 'nickname': user[3]},
            'permissions': permissions,
            'menus': build_menu_tree(menus)
        })
    return jsonify({'status': 'error', 'message': '用户名或密码错误'})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'status': 'success'})

@app.route('/api/me', methods=['GET'])
@require_login
def get_me():
    user_id = session['user_id']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, nickname FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()

    if not user:
        session.clear()
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    return jsonify({
        'status': 'success',
        'data': {
            'id': user[0],
            'username': user[1],
            'nickname': user[2],
            'permissions': get_user_permissions(user[0]),
            'menus': build_menu_tree(get_user_menus(user[0]))
        }
    })

@app.route('/api/users', methods=['GET'])
@require_permission('user:view')
def get_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT u.id, u.username, u.nickname, u.email, u.status, u.created_at,
                 GROUP_CONCAT(r.name) as roles
                 FROM users u
                 LEFT JOIN user_roles ur ON u.id = ur.user_id
                 LEFT JOIN roles r ON ur.role_id = r.id
                 GROUP BY u.id''')
    users = c.fetchall()
    conn.close()
    
    result = []
    for u in users:
        result.append({
            'id': u[0], 'username': u[1], 'nickname': u[2], 'email': u[3],
            'status': u[4], 'createdAt': u[5], 'roles': u[6] or ''
        })
    
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/users', methods=['POST'])
@require_permission('user:add')
def create_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    nickname = data.get('nickname', '')
    email = data.get('email', '')
    roles = data.get('roles', [])
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('SELECT id FROM users WHERE username = ?', (username,))
        if c.fetchone():
            conn.close()
            return jsonify({'status': 'error', 'message': '用户名已存在'})
        
        c.execute("""INSERT INTO users (username, password, nickname, email, created_at)
                     VALUES (?, ?, ?, ?, ?)""",
                  (username, generate_password_hash(password), nickname, email, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        user_id = c.lastrowid
        
        for role_id in roles:
            c.execute('INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)', (user_id, role_id))
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@require_permission('user:edit')
def update_user(user_id):
    data = request.get_json()
    nickname = data.get('nickname')
    email = data.get('email')
    status = data.get('status')
    roles = data.get('roles', [])
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('UPDATE users SET nickname = ?, email = ?, status = ? WHERE id = ?',
                  (nickname, email, status, user_id))
        
        c.execute('DELETE FROM user_roles WHERE user_id = ?', (user_id,))
        for role_id in roles:
            c.execute('INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)', (user_id, role_id))
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_permission('user:delete')
def delete_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM user_roles WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/roles', methods=['GET'])
@require_permission('role:view')
def get_roles():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT r.id, r.name, r.description, r.created_at,
                 GROUP_CONCAT(p.code) as permissions
                 FROM roles r
                 LEFT JOIN role_permissions rp ON r.id = rp.role_id
                 LEFT JOIN permissions p ON rp.permission_id = p.id
                 GROUP BY r.id''')
    roles = c.fetchall()
    conn.close()
    
    result = []
    for r in roles:
        result.append({
            'id': r[0], 'name': r[1], 'description': r[2], 'createdAt': r[3],
            'permissions': r[4].split(',') if r[4] else []
        })
    
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/roles', methods=['POST'])
@require_permission('role:add')
def create_role():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    permissions = data.get('permissions', [])
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('SELECT id FROM roles WHERE name = ?', (name,))
        if c.fetchone():
            conn.close()
            return jsonify({'status': 'error', 'message': '角色名已存在'})
        
        c.execute("INSERT INTO roles (name, description, created_at) VALUES (?, ?, ?)",
                  (name, description, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        role_id = c.lastrowid
        
        for perm_id in permissions:
            c.execute('INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)', (role_id, perm_id))

        sync_role_menus_from_permissions(c, role_id)
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/roles/<int:role_id>', methods=['PUT'])
@require_permission('role:edit')
def update_role(role_id):
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    permissions = data.get('permissions', [])
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('UPDATE roles SET name = ?, description = ? WHERE id = ?', (name, description, role_id))
        
        c.execute('DELETE FROM role_permissions WHERE role_id = ?', (role_id,))
        for perm_id in permissions:
            c.execute('INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)', (role_id, perm_id))

        sync_role_menus_from_permissions(c, role_id)
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        conn.close()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/roles/<int:role_id>', methods=['DELETE'])
@require_permission('role:delete')
def delete_role(role_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM role_permissions WHERE role_id = ?', (role_id,))
    c.execute('DELETE FROM user_roles WHERE role_id = ?', (role_id,))
    c.execute('DELETE FROM roles WHERE id = ?', (role_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/permissions', methods=['GET'])
@require_login
def get_permissions():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, code, type FROM permissions ORDER BY type, id')
    perms = c.fetchall()
    conn.close()
    
    result = [{'id': p[0], 'name': p[1], 'code': p[2], 'type': p[3]} for p in perms]
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/assembly-production/workshops', methods=['GET'])
@require_permission('assembly:query')
def get_workshops():
    try:
        workshops = query_workshops(get_sqlserver_connection)
        return jsonify({'status': 'success', 'data': workshops})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/assembly-production/query', methods=['GET'])
@require_permission('assembly:query')
def query_assembly():
    try:
        filters = parse_assembly_filters(request.args)
        data = query_assembly_data(filters, get_sqlserver_connection)
        return jsonify({'status': 'success', 'data': data, 'total': len(data)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/assembly-production/export', methods=['GET'])
@require_permission('assembly:export')
def export_assembly():
    try:
        filters = parse_assembly_filters(request.args)
        data = query_assembly_data(filters, get_sqlserver_connection)
        output, filename = build_assembly_export_file(data)
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/checklist/query', methods=['GET'])
def query_checklist():
    """Query SQL Server real data for /list page from 昨日打磨数据_外协."""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    user_permissions = get_user_permissions(session['user_id'])
    if 'checklist:query' not in user_permissions and 'assembly:query' not in user_permissions:
        return jsonify({'status': 'error', 'message': 'No permission'}), 403

    try:
        data = query_checklist_data(request.args, get_sqlserver_connection)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    return jsonify({'status': 'success', 'data': data, 'total': len(data)})


@app.route('/api/checklist/finished-qty-all', methods=['GET'])
def query_finished_qty_all_api():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    user_permissions = get_user_permissions(session['user_id'])
    if 'checklist:query' not in user_permissions and 'assembly:query' not in user_permissions:
        return jsonify({'status': 'error', 'message': 'No permission'}), 403

    try:
        data = query_finished_qty_all(request.args, get_sqlserver_connection)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    return jsonify({'status': 'success', 'data': data, 'total': len(data)})

@app.route('/')
def index():
    return _serve_frontend_index()


def _serve_frontend_index():
    base_dir = PROJECT_ROOT
    dist_index = os.path.join(base_dir, 'frontend-dist', 'index.html')
    if os.path.exists(dist_index):
        return send_from_directory(os.path.join(base_dir, 'frontend-dist'), 'index.html')
    return send_from_directory(base_dir, 'index.html')


@app.route('/static/<path:filename>')
def serve_vite_static(filename):
    base_dir = PROJECT_ROOT
    dist_dir = os.path.join(base_dir, 'frontend-dist')
    return send_from_directory(dist_dir, filename)


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    base_dir = PROJECT_ROOT
    return send_from_directory(os.path.join(base_dir, 'assets'), filename)


@app.route('/logo.ico')
def serve_logo():
    base_dir = PROJECT_ROOT
    assets_logo = os.path.join(base_dir, 'assets', 'logo.ico')
    if os.path.exists(assets_logo):
        return send_from_directory(os.path.join(base_dir, 'assets'), 'logo.ico')
    return send_from_directory(base_dir, 'logo.ico')


@app.route('/<path:path>')
def spa_fallback(path):
    # Keep API and explicit static asset routes untouched.
    if path.startswith('api/') or path.startswith('assets/') or path.startswith('static/'):
        return jsonify({'status': 'error', 'message': 'Not Found'}), 404
    return _serve_frontend_index()

@app.route('/api/dashboard/stats', methods=['GET'])
@require_login
def dashboard_stats():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM assembly_progress')
    total_orders = c.fetchone()[0]
    
    c.execute('SELECT SUM(计划数量), SUM(已完成数量) FROM assembly_progress')
    stats = c.fetchone()
    
    c.execute("""SELECT 进度状态, COUNT(*) FROM assembly_progress GROUP BY 进度状态""")
    status_stats = c.fetchall()
    
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM roles')
    total_roles = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'status': 'success',
        'data': {
            'totalOrders': total_orders,
            'totalQuantity': stats[0] or 0,
            'totalCompleted': stats[1] or 0,
            'statusStats': [{'status': s[0], 'count': s[1]} for s in status_stats],
            'totalUsers': total_users,
            'totalRoles': total_roles
        }
    })


