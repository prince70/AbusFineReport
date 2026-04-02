from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import importlib.util
import importlib
import sqlite3
import pyodbc
from collections import defaultdict
from datetime import datetime, timedelta
import random
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'production-query-secret-key-2024')
app.config['JSON_AS_ASCII'] = False

DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')
SQLSERVER_CONFIG = {
    'server': os.environ.get('DB_SERVER', '192.168.41.57'),
    'database': os.environ.get('DB_NAME', 'department2020'),
    'user': os.environ.get('DB_USER', 'sa'),
    'password': os.environ.get('DB_PASSWORD', '3518i')
}

def get_db_connection():
    return sqlite3.connect('production.db')


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

    c.execute('SELECT COUNT(*) FROM role_menus')
    if c.fetchone()[0] == 0:
        c.execute('SELECT id, path FROM menus')
        menu_map = {row[1]: row[0] for row in c.fetchall()}

        admin_menu_paths = ['/dashboard', '/assembly', '/system', '/system/users', '/system/roles']
        user_menu_paths = ['/dashboard', '/assembly']

        for menu_path in admin_menu_paths:
            menu_id = menu_map.get(menu_path)
            if menu_id:
                c.execute('INSERT OR IGNORE INTO role_menus (role_id, menu_id) VALUES (?, ?)', (1, menu_id))

        for menu_path in user_menu_paths:
            menu_id = menu_map.get(menu_path)
            if menu_id:
                c.execute('INSERT OR IGNORE INTO role_menus (role_id, menu_id) VALUES (?, ?)', (2, menu_id))

    # Ensure the checklist/report menu exists (外协加工清单 -> /list)
    c.execute("SELECT id FROM menus WHERE path = '/list'")
    existing = c.fetchone()
    if not existing:
        # insert as a root menu item
        c.execute("INSERT INTO menus (name, path, icon, parent_id, order_num) VALUES (?, ?, ?, ?, ?)",
                  ('外协加工清单', '/list', 'el-icon-document', None, 4))
        c.execute("SELECT id FROM menus WHERE path = '/list'")
        new_menu_id = c.fetchone()[0]
        # grant menu to admin and normal user roles
        c.execute('INSERT OR IGNORE INTO role_menus (role_id, menu_id) VALUES (?, ?)', (1, new_menu_id))
        c.execute('INSERT OR IGNORE INTO role_menus (role_id, menu_id) VALUES (?, ?)', (2, new_menu_id))
    
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
    query = '''
        SELECT DISTINCT v.锁类分区
        FROM department2020.dbo.V_销售订单2 v
        WHERE v.item_no NOT LIKE '115%'
          AND v.item_no NOT LIKE '116%'
          AND v.锁类分区 IS NOT NULL
          AND v.锁类分区 <> ''
        ORDER BY v.锁类分区
    '''

    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        workshops = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'data': workshops})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/assembly-production/query', methods=['GET'])
@require_permission('assembly:query')
def query_assembly():
    生产车间 = request.args.get('生产车间', '') or request.args.get('区域', '')
    订单号 = request.args.get('订单号', '') or request.args.get('订单批号', '')
    料品编码 = request.args.get('料品编码', '')
    料品名称 = request.args.get('料品名称', '')
    客户 = request.args.get('客户', '')
    开始日期 = request.args.get('开始日期', '')
    结束日期 = request.args.get('结束日期', '')
    进度状态 = request.args.get('进度状态', '')

    query = '''
        SELECT
            v.客户 AS 客户,
            v.sheet_lot AS 订单号,
            v.sheet_lot AS 订单批号,
            v.确定交期 AS 确定交期,
            v.锁类分区 AS 生产车间,
            v.锁类分区 AS 分区,
            v.锁类分区 AS 锁类分区,
            v.item_no AS 料品编码,
            v.part_name AS 料品名称,
            v.part_spec AS 料品规格,
            v.part_spec AS 规格型号,
            CAST(v.sheet_qty AS INT) AS 计划数量,
            CAST(v.sheet_qty AS INT) AS 订单数量,
            ISNULL(f.finished_qty, 0) AS 已完成数量,
            ISNULL(f.finished_qty, 0) AS 完成数量,
            CASE
                WHEN CAST(v.sheet_qty AS INT) - ISNULL(f.finished_qty, 0) > 0
                    THEN CAST(v.sheet_qty AS INT) - ISNULL(f.finished_qty, 0)
                ELSE 0
            END AS 未开始数量,
            CAST(v.sheet_qty AS INT) - ISNULL(f.finished_qty, 0) AS 未完成数量,
            CASE
                WHEN CAST(v.sheet_qty AS INT) > 0
                    THEN ROUND(ISNULL(f.finished_qty, 0) * 100.0 / CAST(v.sheet_qty AS INT), 1)
                ELSE 0
            END AS 完成率,
            f.min_finished_date AS 最早完成日期,
            f.max_finished_date AS 最晚完成日期,
            CASE
                WHEN ISNULL(f.finished_qty, 0) >= CAST(v.sheet_qty AS INT) AND CAST(v.sheet_qty AS INT) > 0 THEN '已完成'
                WHEN ISNULL(f.finished_qty, 0) > 0 THEN '进行中'
                ELSE '未开始'
            END AS 进度状态,
            '' AS 备注
        FROM department2020.dbo.V_销售订单2 v
        LEFT JOIN (
            SELECT
                OrderNumber,
                SUM(EachFinishedQty) AS finished_qty,
                MIN(FinishedDate) AS min_finished_date,
                MAX(FinishedDate) AS max_finished_date
            FROM APS_FinishedQty
            WHERE ResName LIKE 'ZQ-%'
              AND JobExternalId NOT LIKE '%中间件%'
            GROUP BY OrderNumber
        ) f ON v.sheet_lot = f.OrderNumber
        WHERE v.item_no NOT LIKE '115%'
          AND v.item_no NOT LIKE '116%'
    '''
    params = []

    if 生产车间:
        query += ' AND v.锁类分区 LIKE ?'
        params.append(生产车间)
    if 订单号:
        query += ' AND v.sheet_lot LIKE ?'
        params.append(f'%{订单号}%')
    if 客户:
        query += ' AND v.客户 LIKE ?'
        params.append(f'%{客户}%')
    if 料品编码:
        query += ' AND v.item_no LIKE ?'
        params.append(f'%{料品编码}%')
    if 料品名称:
        query += ' AND v.part_name LIKE ?'
        params.append(f'%{料品名称}%')
    if 开始日期:
        query += ' AND v.确定交期 >= ?'
        params.append(开始日期)
    if 结束日期:
        query += ' AND v.确定交期 <= ?'
        params.append(结束日期)
    if 进度状态:
        query += '''
            AND (
                CASE
                    WHEN ISNULL(f.finished_qty, 0) >= CAST(v.sheet_qty AS INT) AND CAST(v.sheet_qty AS INT) > 0 THEN '已完成'
                    WHEN ISNULL(f.finished_qty, 0) > 0 THEN '进行中'
                    ELSE '未开始'
                END
            ) = ?
        '''
        params.append(进度状态)

    query += ' ORDER BY v.sheet_lot'

    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description] if cursor.description else []
        data = [dict(zip(columns, row)) for row in rows]
        total = len(data)
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'data': data, 'total': total})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/checklist/options', methods=['GET'])
def get_checklist_options():
    """Get distinct 外协件名称 options for filter dropdown."""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    user_permissions = get_user_permissions(session['user_id'])
    if 'checklist:query' not in user_permissions and 'assembly:query' not in user_permissions:
        return jsonify({'status': 'error', 'message': 'No permission'}), 403

    def _clean_arg(name, fallback=''):
        value = request.args.get(name, fallback)
        if value is None:
            return ''
        value = str(value).strip()
        if value.lower() in ('', 'null', 'undefined', 'none'):
            return ''
        return value

    订单批号 = _clean_arg('订单批号') or _clean_arg('订单号')
    规格型号 = _clean_arg('规格型号')
    区域 = _clean_arg('区域')
    开始日期 = _clean_arg('开始日期')
    结束日期 = _clean_arg('结束日期')

    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()

        query = '''
            SELECT DISTINCT
                CAST(ISNULL(t.半成品名称, '') AS NVARCHAR(MAX)) AS 外协件名称
            FROM department2020.dbo.昨日打磨数据_外协 t
            LEFT JOIN department2020.dbo.V_销售订单2 v ON t.OrderNumber = v.sheet_lot
            WHERE t.半成品名称 IS NOT NULL
              AND t.半成品名称 != ''
        '''
        params = []

        if 开始日期:
            query += ' AND t.FinishedDate >= ?'
            params.append(开始日期)
        if 结束日期:
            query += ' AND t.FinishedDate <= ?'
            params.append(结束日期)
        if 订单批号:
            query += ' AND t.OrderNumber LIKE ?'
            params.append(f'%{订单批号}%')
        if 规格型号:
            query += ' AND t.半成品规格 LIKE ?'
            params.append(f'%{规格型号}%')
        if 区域:
            query += ' AND v.锁类分区 LIKE ?'
            params.append(f'%{区域}%')

        query += ' ORDER BY 外协件名称'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        names = [str(row[0]).strip() for row in rows if row[0]]
        cursor.close()
        conn.close()
        app.logger.info(f'Fetched {len(names)} checklist options')
        return jsonify({'status': 'success', 'data': names})
    except Exception as e:
        import traceback
        error_msg = str(e)
        app.logger.error(f'Error in get_checklist_options: {error_msg}\n{traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': error_msg}), 500


@app.route('/api/checklist/query', methods=['GET'])
def query_checklist():
    """Query SQL Server real data for /list page from 昨日打磨数据_外协."""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    user_permissions = get_user_permissions(session['user_id'])
    if 'checklist:query' not in user_permissions and 'assembly:query' not in user_permissions:
        return jsonify({'status': 'error', 'message': 'No permission'}), 403

    def _clean_arg(name, fallback=''):
        value = request.args.get(name, fallback)
        if value is None:
            return ''
        value = str(value).strip()
        if value.lower() in ('', 'null', 'undefined', 'none'):
            return ''
        return value

    订单批号 = _clean_arg('订单批号') or _clean_arg('订单号')
    外协件名称 = _clean_arg('外协件名称')
    规格型号 = _clean_arg('规格型号')
    区域 = _clean_arg('区域')
    查询时间 = _clean_arg('查询时间')
    开始日期 = _clean_arg('开始日期')
    结束日期 = _clean_arg('结束日期')

    query = '''
        SELECT
            t.OrderNumber AS 订单号,
            t.OrderNumber AS 订单批号,
            ISNULL(v.锁类分区, '') AS 分区,
            ISNULL(t.半成品名称, '') AS 外协件名称,
            ISNULL(t.半成品规格, '') AS 规格型号,
            CAST(ISNULL(t.EachFinishedQty, 0) AS INT) AS 订单数量,
            ISNULL(t.单位, '') AS 单位,
            '' AS 备注,
            ISNULL(t.外协项目1, '') AS 外协项目,
            ISNULL(t.品质要求1, '') AS 品质要求,
            t.FinishedDate AS 交货期限,
            CAST(NULL AS DATETIME) AS 上线日期,
            ISNULL(v.确定交期, t.[确定交期]) AS 订单整货期,
            ISNULL(v.锁类分区, '') AS 责任车间,
            CAST(ISNULL(t.盆的重量_千克, 0) AS DECIMAL(18, 3)) AS 毛重,
            CAST(ISNULL(t.每盆重量或只数, 0) AS DECIMAL(18, 3)) AS 每盆只数,
            CAST(ISNULL(t.物料单重_克, 0) AS DECIMAL(18, 3)) AS 单重_克,
            CAST(0 AS DECIMAL(18, 2)) AS 净重
        FROM department2020.dbo.昨日打磨数据_外协 t
        LEFT JOIN department2020.dbo.V_销售订单2 v ON t.OrderNumber = v.sheet_lot
        WHERE 1=1
    '''
    params = []

    # 新规则：支持单选日期+时间（按 FinishedDate 到秒精确过滤）
    if 查询时间:
        query += " AND CONVERT(VARCHAR(19), t.FinishedDate, 120) = ?"
        params.append(查询时间)
    if 开始日期:
        query += ' AND t.FinishedDate >= ?'
        params.append(开始日期)
    if 结束日期:
        query += ' AND t.FinishedDate <= ?'
        params.append(结束日期)
    if 订单批号:
        query += ' AND t.OrderNumber LIKE ?'
        params.append(f'%{订单批号}%')
    
    # Handle multiple 外协件名称 (comma-separated or array)
    外协件名称_list = request.args.get('外协件名称', '')
    if 外协件名称_list:
        # Support both comma-separated string and multiple query params
        if ',' in 外协件名称_list:
            names = [n.strip() for n in 外协件名称_list.split(',') if n.strip()]
        else:
            names = [外协件名称_list.strip()]
        
        if names:
            placeholders = ','.join(['?' for _ in names])
            query += f' AND t.半成品名称 IN ({placeholders})'
            params.extend(names)
    
    if 规格型号:
        query += ' AND t.半成品规格 LIKE ?'
        params.append(f'%{规格型号}%')
    if 区域:
        query += ' AND v.锁类分区 LIKE ?'
        params.append(f'%{区域}%')

    query += ' ORDER BY t.半成品规格, t.OrderNumber, t.FinishedDate'

    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description] if cursor.description else []
        data = [dict(zip(columns, row)) for row in rows]

        def _spec_group_key(spec, delivery_date):
            text = str(spec or '').strip()
            if not text:
                spec_key = ''
            else:
                parts = text.split()
                # Ignore color suffix in common patterns such as "ABUS 145/40 不锈钢色".
                spec_key = ' '.join(parts[:2]) if len(parts) >= 2 else text
            
            # Extract date part from 确定交期 for composite grouping
            date_str = ''
            if delivery_date:
                try:
                    # Convert datetime to date string YYYY-MM-DD
                    if isinstance(delivery_date, str):
                        date_str = delivery_date[:10]
                    else:
                        date_str = str(delivery_date)[:10]
                except:
                    date_str = ''
            
            # Composite key: spec + delivery_date
            return f"{spec_key}|{date_str}" if date_str else spec_key

        group_qty = defaultdict(int)
        group_unit = defaultdict(float)
        group_pack = defaultdict(float)
        for item in data:
            key = _spec_group_key(item.get('规格型号'), item.get('交货期限'))
            item['规格型号分组'] = key
            qty = int(item.get('订单数量') or 0)
            unit = float(item.get('单重_克') or 0)
            pack = float(item.get('每盆只数') or 0)
            group_qty[key] += qty
            if unit > group_unit[key]:
                group_unit[key] = unit
            if pack > group_pack[key]:
                group_pack[key] = pack

        def _fmt_num(value):
            if abs(value - int(value)) < 1e-9:
                return str(int(value))
            return f"{value:.3f}".rstrip('0').rstrip('.')

        for item in data:
            key = item.get('规格型号分组', '')
            item['净重'] = round(group_qty[key] * group_unit[key] / 1000.0, 2)
            total_qty = float(group_qty[key])
            pack_qty = float(group_pack[key])
            if pack_qty > 0:
                quotient = int(total_qty // pack_qty)
                remainder = total_qty - (quotient * pack_qty)
                item['备注'] = f"{quotient}*{_fmt_num(pack_qty)}+{_fmt_num(remainder)}"
            else:
                item['备注'] = ''
            item.pop('单重_克', None)

        data.sort(key=lambda x: (
            x.get('规格型号分组') or '',
            x.get('订单号') or '',
            str(x.get('订单整货期') or '')
        ))
        total = len(data)
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    return jsonify({'status': 'success', 'data': data, 'total': total})

@app.route('/')
def index():
    import os
    with open(os.path.join(os.path.dirname(__file__), 'index.html'), 'r', encoding='utf-8') as f:
        return f.read()


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    base_dir = os.path.dirname(__file__)
    return send_from_directory(os.path.join(base_dir, 'assets'), filename)


@app.route('/logo.ico')
def serve_logo():
    base_dir = os.path.dirname(__file__)
    assets_logo = os.path.join(base_dir, 'assets', 'logo.ico')
    if os.path.exists(assets_logo):
        return send_from_directory(os.path.join(base_dir, 'assets'), 'logo.ico')
    return send_from_directory(base_dir, 'logo.ico')

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)
