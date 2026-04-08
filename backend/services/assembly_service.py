from io import BytesIO
from datetime import datetime
import importlib


def parse_assembly_filters(args):
    生产车间 = args.get('生产车间', '') or args.get('区域', '')
    订单号 = args.get('订单号', '') or args.get('订单批号', '')
    料品编码 = args.get('料品编码', '')
    料品名称 = args.get('料品名称', '')
    客户 = args.get('客户', '')
    开始日期 = args.get('开始日期', '')
    结束日期 = args.get('结束日期', '')

    status_list = []
    status_list.extend(args.getlist('进度状态'))
    status_list.extend(args.getlist('进度状态[]'))
    single_status = args.get('进度状态', '')
    if single_status and not status_list:
        status_list = [item.strip() for item in single_status.split(',') if item.strip()]

    dedup_status = []
    for item in status_list:
        val = str(item).strip()
        if val and val not in dedup_status:
            dedup_status.append(val)

    return {
        '生产车间': 生产车间,
        '订单号': 订单号,
        '料品编码': 料品编码,
        '料品名称': 料品名称,
        '客户': 客户,
        '开始日期': 开始日期,
        '结束日期': 结束日期,
        '进度状态列表': dedup_status,
    }


def query_workshops(get_sqlserver_connection):
    query = '''
        SELECT DISTINCT v.锁类分区
        FROM department2020.dbo.V_销售订单2 v
        WHERE v.item_no NOT LIKE '115%'
          AND v.item_no NOT LIKE '116%'
          AND v.锁类分区 IS NOT NULL
          AND v.锁类分区 <> ''
        ORDER BY v.锁类分区
    '''

    conn = get_sqlserver_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def query_assembly_data(filters, get_sqlserver_connection):
    生产车间 = filters.get('生产车间', '')
    订单号 = filters.get('订单号', '')
    料品编码 = filters.get('料品编码', '')
    料品名称 = filters.get('料品名称', '')
    客户 = filters.get('客户', '')
    开始日期 = filters.get('开始日期', '')
    结束日期 = filters.get('结束日期', '')
    进度状态列表 = filters.get('进度状态列表', [])

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
    if 进度状态列表:
        placeholders = ','.join(['?'] * len(进度状态列表))
        query += '''
            AND (
                CASE
                    WHEN ISNULL(f.finished_qty, 0) >= CAST(v.sheet_qty AS INT) AND CAST(v.sheet_qty AS INT) > 0 THEN '已完成'
                    WHEN ISNULL(f.finished_qty, 0) > 0 THEN '进行中'
                    ELSE '未开始'
                END
            ) IN (''' + placeholders + ''')
        '''
        params.extend(进度状态列表)

    query += ' ORDER BY v.sheet_lot'

    conn = get_sqlserver_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in rows]
    finally:
        cursor.close()
        conn.close()


def build_assembly_export_file(data):
    try:
        Workbook = importlib.import_module('openpyxl').Workbook
    except Exception as exc:
        raise RuntimeError('缺少 openpyxl 依赖，请先安装 requirements.txt') from exc

    headers = [
        '客户', '订单批号', '分区', '确定交期', '料品编码', '料品名称', '规格型号',
        '订单数量', '完成数量', '未完成数量', '最早完成日期', '最晚完成日期', '进度状态', '备注'
    ]

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = '装嵌生产进度'
    worksheet.append(headers)

    for row in data:
        worksheet.append([
            row.get('客户', ''),
            row.get('订单批号', ''),
            row.get('分区', ''),
            row.get('确定交期', ''),
            row.get('料品编码', ''),
            row.get('料品名称', ''),
            row.get('规格型号', ''),
            row.get('订单数量', 0),
            row.get('完成数量', 0),
            row.get('未完成数量', 0),
            row.get('最早完成日期', ''),
            row.get('最晚完成日期', ''),
            row.get('进度状态', ''),
            row.get('备注', ''),
        ])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    filename = f"assembly_progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return output, filename
