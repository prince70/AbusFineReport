from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
import math


WORKSHOP_MAP = {
    'grinding': {'table': '昨日打磨数据_外协', 'mode': 'grinding'},
    'key': {'table': '昨日钥匙数据_外协', 'mode': 'key'},
    'body': {'table': '昨日锁体数据_外协', 'mode': 'body'},
    'beam': {'table': '昨日锁梁数据_外协', 'mode': 'body'},
    'core': {'table': '昨日锁芯数据_外协', 'mode': 'body'},
}


def clean_arg(args, name, fallback=''):
    value = args.get(name, fallback)
    if value is None:
        return ''
    value = str(value).strip()
    if value.lower() in ('', 'null', 'undefined', 'none'):
        return ''
    return value


def _json_safe_value(value):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=' ')
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore')
    return value


def _to_float(value):
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except Exception:
        return 0.0


def _parse_date_only(text, fallback):
    if not text:
        return fallback
    raw = str(text).strip()
    if not raw:
        return fallback
    try:
        return datetime.fromisoformat(raw[:19]).date()
    except Exception:
        pass
    try:
        return datetime.strptime(raw[:10], '%Y-%m-%d').date()
    except Exception:
        return fallback


def _parse_datetime(text, fallback):
    if not text:
        return fallback
    raw = str(text).strip()
    if not raw:
        return fallback
    try:
        return datetime.fromisoformat(raw[:19])
    except Exception:
        pass
    try:
        return datetime.strptime(raw[:19], '%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    try:
        return datetime.strptime(raw[:10], '%Y-%m-%d')
    except Exception:
        return fallback


def _get_table_columns(cursor, table_name):
    cursor.execute(
        '''
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?
        ''',
        (table_name,)
    )
    return {row[0] for row in cursor.fetchall()}


def _get_table_column_order(cursor, table_name):
    cursor.execute(
        '''
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
        ''',
        (table_name,)
    )
    return [row[0] for row in cursor.fetchall()]


def _decode_mojibake(text):
    if not isinstance(text, str):
        return text
    try:
        fixed = text.encode('latin1').decode('gbk')
        if fixed and fixed != text:
            return fixed
    except Exception:
        pass
    return text


def _get_table_columns_fallback(cursor, table_name):
    columns = _get_table_column_order(cursor, table_name)
    decoded = [_decode_mojibake(name) for name in columns]
    return decoded


WORKSHOP_COLUMN_RENAMES = {
    '��������': '生产车间',
    '���Ʒ����': '半成品名称',
    '���Ʒ���': '半成品规格',
    '��Э��Ŀ1': '外协项目1',
    'Ʒ��Ҫ��1': '品质要求1',
    'ȷ������': '确定交期',
    '���ϵ���_��': '盆的重量_千克',
    '��λ': '单位',
    '�������_ǧ��': '物料单重_克',
    'ÿ��������ֻ��': '每盆重量或只数',
}


def _rename_row_keys(row):
    renamed = {}
    for key, value in row.items():
        renamed[WORKSHOP_COLUMN_RENAMES.get(key, key)] = value
    return renamed


def _resolve_remark_expr(column_names):
    remark_candidates = ['备注', '算好盆数', '盆数']
    remark_col = next((name for name in remark_candidates if name in column_names), None)
    if not remark_col:
        return "''"
    safe_name = remark_col.replace(']', ']]')
    return f"ISNULL(CAST(t.[{safe_name}] AS NVARCHAR(100)), '')"


def _col_exists(column_names, column_name):
    return column_name in column_names


def _safe_col(column_name):
    return column_name.replace(']', ']]')


def _first_existing_col(column_names, candidates):
    for name in candidates:
        if name in column_names:
            return name
    return None


def _text_expr(column_names, candidates, max_len=255):
    col = _first_existing_col(column_names, candidates)
    if not col:
        return "''", None
    safe = _safe_col(col)
    return f"ISNULL(CAST(t.[{safe}] AS NVARCHAR({max_len})), '')", col


def _decimal_expr(column_names, candidates, scale=3):
    col = _first_existing_col(column_names, candidates)
    if not col:
        return f"CAST(0 AS DECIMAL(18, {scale}))", None
    safe = _safe_col(col)
    return f"CAST(ISNULL(t.[{safe}], 0) AS DECIMAL(18, {scale}))", col


def _int_expr(column_names, candidates):
    col = _first_existing_col(column_names, candidates)
    if not col:
        return "CAST(0 AS INT)", None
    safe = _safe_col(col)
    return f"CAST(ISNULL(t.[{safe}], 0) AS INT)", col


def _post_process_rows(data):
    def _spec_group_key(spec, delivery_date):
        text = str(spec or '').strip()
        if not text:
            spec_key = ''
        else:
            parts = text.split()
            spec_key = ' '.join(parts[:2]) if len(parts) >= 2 else text

        date_str = ''
        if delivery_date:
            try:
                if isinstance(delivery_date, str):
                    date_str = delivery_date[:10]
                else:
                    date_str = str(delivery_date)[:10]
            except Exception:
                date_str = ''
        return f"{spec_key}|{date_str}" if date_str else spec_key

    group_qty = defaultdict(int)
    group_unit = defaultdict(float)
    group_pack = defaultdict(float)
    group_remark_sum = defaultdict(float)

    for item in data:
        key = _spec_group_key(item.get('规格型号'), item.get('交货期限'))
        item['规格型号分组'] = key
        qty = int(item.get('订单数量') or 0)
        unit = float(item.get('单重_克') or 0)
        pack = float(item.get('每盆重量或只数') or 0)
        remark_value = _to_float(item.get('备注原始'))
        group_qty[key] += qty
        if unit > group_unit[key]:
            group_unit[key] = unit
        if pack > group_pack[key]:
            group_pack[key] = pack
        group_remark_sum[key] += remark_value

    def _fmt_num(value):
        if abs(value - int(value)) < 1e-9:
            return str(int(value))
        return f"{value:.3f}".rstrip('0').rstrip('.')

    for item in data:
        key = item.get('规格型号分组', '')
        item['净重'] = round(group_qty[key] * group_unit[key] / 1000.0, 2)
        total_qty = float(group_qty[key])
        pack_qty = float(group_pack[key])
        remark_sum = float(group_remark_sum[key])
        if remark_sum > 0:
            item['盆数'] = int(math.ceil(remark_sum))
        elif pack_qty > 0:
            item['盆数'] = int(math.ceil(total_qty / pack_qty))
        else:
            item['盆数'] = 0
        if pack_qty > 0:
            quotient = int(total_qty // pack_qty)
            remainder = total_qty - (quotient * pack_qty)
            item['备注'] = f"{quotient}*{_fmt_num(pack_qty)}+{_fmt_num(remainder)}"
        else:
            item['备注'] = ''
        item.pop('备注原始', None)
        item.pop('每盆重量或只数', None)
        item.pop('单重_克', None)

    data.sort(key=lambda x: (
        x.get('规格型号分组') or '',
        x.get('订单号') or '',
        str(x.get('订单整货期') or '')
    ))
    return data


def _query_grinding_data(args, get_sqlserver_connection):
    订单批号 = clean_arg(args, '订单批号') or clean_arg(args, '订单号')
    外协件名称 = clean_arg(args, '外协件名称')
    规格型号 = clean_arg(args, '规格型号')
    区域 = clean_arg(args, '区域')
    查询时间 = clean_arg(args, '查询时间')
    开始日期 = clean_arg(args, '开始日期')
    结束日期 = clean_arg(args, '结束日期')

    conn = get_sqlserver_connection()
    cursor = conn.cursor()
    try:
        table_name = '昨日打磨数据_外协'
        columns = _get_table_columns(cursor, table_name)
        display_columns = _get_table_columns_fallback(cursor, table_name)
        if 'OrderNumber' not in columns:
            return []

        remark_expr = _resolve_remark_expr(columns)
        name_expr = "ISNULL(CAST(t.[半成品名称] AS NVARCHAR(255)), '')" if _col_exists(columns, '半成品名称') else "''"
        spec_expr = "ISNULL(CAST(t.[半成品规格] AS NVARCHAR(255)), '')" if _col_exists(columns, '半成品规格') else "''"
        qty_expr = "CAST(ISNULL(t.[EachFinishedQty], 0) AS INT)" if _col_exists(columns, 'EachFinishedQty') else "CAST(0 AS INT)"
        unit_expr = "ISNULL(CAST(t.[单位] AS NVARCHAR(50)), '')" if _col_exists(columns, '单位') else "''"
        project_expr = "ISNULL(CAST(t.[外协项目1] AS NVARCHAR(255)), '')" if _col_exists(columns, '外协项目1') else "''"
        quality_expr = "ISNULL(CAST(t.[品质要求1] AS NVARCHAR(255)), '')" if _col_exists(columns, '品质要求1') else "''"
        finish_date_expr = 't.[FinishedDate]' if _col_exists(columns, 'FinishedDate') else 'CAST(NULL AS DATETIME)'
        delivery_expr = "ISNULL(v.确定交期, t.[确定交期])" if _col_exists(columns, '确定交期') else 'v.确定交期'
        gross_expr = "CAST(ISNULL(t.[盆的重量_千克], 0) AS DECIMAL(18, 3))" if _col_exists(columns, '盆的重量_千克') else "CAST(0 AS DECIMAL(18, 3))"
        pack_expr = "CAST(ISNULL(t.[每盆重量或只数], 0) AS DECIMAL(18, 3))" if _col_exists(columns, '每盆重量或只数') else "CAST(0 AS DECIMAL(18, 3))"
        unit_weight_expr = "CAST(ISNULL(t.[物料单重_克], 0) AS DECIMAL(18, 3))" if _col_exists(columns, '物料单重_克') else "CAST(0 AS DECIMAL(18, 3))"

        query = f'''
        SELECT
            t.OrderNumber AS 订单号,
            t.OrderNumber AS 订单批号,
            ISNULL(v.锁类分区, '') AS 分区,
            {name_expr} AS 外协件名称,
            {spec_expr} AS 规格型号,
            {qty_expr} AS 订单数量,
            {unit_expr} AS 单位,
            {remark_expr} AS 备注原始,
            '' AS 备注,
            {project_expr} AS 外协项目,
            {quality_expr} AS 品质要求,
            {finish_date_expr} AS 交货期限,
            CAST(NULL AS DATETIME) AS 上线日期,
            {delivery_expr} AS 订单整货期,
            ISNULL(v.锁类分区, '') AS 责任车间,
            {gross_expr} AS 毛重,
            {pack_expr} AS 每盆只数,
            {unit_weight_expr} AS 单重_克,
            CAST(0 AS DECIMAL(18, 2)) AS 净重
        FROM department2020.dbo.昨日打磨数据_外协 t
        LEFT JOIN department2020.dbo.V_销售订单2 v ON t.OrderNumber = v.sheet_lot
        WHERE 1=1
        '''
        params = []

        if 查询时间 and _col_exists(columns, 'FinishedDate'):
            query += " AND CONVERT(VARCHAR(19), t.FinishedDate, 120) = ?"
            params.append(查询时间)
        if 开始日期 and _col_exists(columns, 'FinishedDate'):
            query += ' AND t.FinishedDate >= ?'
            params.append(开始日期)
        if 结束日期 and _col_exists(columns, 'FinishedDate'):
            query += ' AND t.FinishedDate <= ?'
            params.append(结束日期)
        if 订单批号:
            query += ' AND t.OrderNumber LIKE ?'
            params.append(f'%{订单批号}%')
        if 外协件名称 and _col_exists(columns, '半成品名称'):
            query += ' AND t.半成品名称 LIKE ?'
            params.append(f'%{外协件名称}%')
        if 规格型号 and _col_exists(columns, '半成品规格'):
            query += ' AND t.半成品规格 LIKE ?'
            params.append(f'%{规格型号}%')
        if 区域:
            query += ' AND v.锁类分区 LIKE ?'
            params.append(f'%{区域}%')

        query += ' ORDER BY t.半成品规格, t.OrderNumber, t.FinishedDate'
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description] if cursor.description else []
        data = [dict(zip(columns, row)) for row in rows]
        return _post_process_rows(data)
    finally:
        cursor.close()
        conn.close()


def _query_workshop_shift_data(args, get_sqlserver_connection, table_name, mode):
    订单批号 = clean_arg(args, '订单批号') or clean_arg(args, '订单号')
    外协件名称 = clean_arg(args, '外协件名称')
    规格型号 = clean_arg(args, '规格型号')
    区域 = clean_arg(args, '区域')
    生产车间 = clean_arg(args, '生产车间')

    now = datetime.now()
    today = now.date()
    has_start_date = bool(clean_arg(args, '开始日期'))
    has_end_date = bool(clean_arg(args, '结束日期'))
    has_date_filter = has_start_date or has_end_date
    start_date = _parse_date_only(clean_arg(args, '开始日期'), today)
    end_date = _parse_date_only(clean_arg(args, '结束日期'), start_date)

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.min.time())

    if mode == 'key' and not has_date_filter:
        cte_sql = f'''
            WITH source_rows AS (
                SELECT *
                FROM department2020.dbo.[{table_name}]
            )
        '''
        params = []
    elif mode == 'key':
        window_start = start_dt + timedelta(hours=8)
        window_end = end_dt + timedelta(hours=8)
        urgent_start = window_end
        urgent_end = datetime.combine(end_date + timedelta(days=1), datetime.min.time()) - timedelta(seconds=1)

        cte_sql = f'''
            WITH source_rows AS (
                SELECT *
                FROM department2020.dbo.[{table_name}]
                WHERE (urgent <> 1 OR urgent IS NULL)
                  AND FinishedDate >= ?
                  AND FinishedDate < ?
                UNION ALL
                SELECT *
                FROM department2020.dbo.[{table_name}]
                WHERE urgent = 1
                  AND FinishedDate >= ?
                  AND FinishedDate <= ?
            )
        '''
        params = [window_start, window_end, urgent_start, urgent_end]
    elif mode == 'body' and not has_date_filter:
        cte_sql = f'''
            WITH source_rows AS (
                SELECT *
                FROM department2020.dbo.[{table_name}]
                WHERE 1=1
            )
        '''
        params = []
    else:
        start_dt = _parse_datetime(clean_arg(args, '开始日期'), datetime.combine(start_date, datetime.min.time()))
        end_dt = _parse_datetime(clean_arg(args, '结束日期'), datetime.combine(end_date, datetime.min.time()))
        urgent_start = end_dt
        urgent_end = end_dt + timedelta(days=1)
        cte_sql = f'''
            WITH source_rows AS (
                SELECT *
                FROM department2020.dbo.[{table_name}]
                WHERE (urgent <> 1 OR urgent IS NULL)
                  AND FinishedDate >= ?
                  AND FinishedDate <= ?
                UNION ALL
                SELECT *
                FROM department2020.dbo.[{table_name}]
                WHERE urgent = 1
                  AND FinishedDate >= ?
                  AND FinishedDate <= ?
            )
        '''
        params = [start_dt, end_dt, urgent_start, urgent_end]

    conn = get_sqlserver_connection()
    cursor = conn.cursor()
    try:
        columns = _get_table_columns(cursor, table_name)
        display_columns = _get_table_columns_fallback(cursor, table_name)
        if 'OrderNumber' not in columns:
            return []

        if mode in ('key', 'body'):
            query = cte_sql + '''
            SELECT t.*
            FROM source_rows t
            WHERE 1=1
            '''

            if 订单批号:
                query += ' AND t.OrderNumber LIKE ?'
                params.append(f'%{订单批号}%')

            name_col = _first_existing_col(columns, ['半成品名称', '外协件名称', '品名', '物料名称', 'Name'])
            if 外协件名称 and name_col:
                query += f" AND t.[{_safe_col(name_col)}] LIKE ?"
                params.append(f'%{外协件名称}%')

            spec_col = _first_existing_col(columns, ['半成品规格', '规格型号', '规格', '型号'])
            if 规格型号 and spec_col:
                query += f" AND t.[{_safe_col(spec_col)}] LIKE ?"
                params.append(f'%{规格型号}%')

            if mode == 'body' and 生产车间 and _col_exists(columns, '生产车间'):
                query += ' AND ISNULL(t.生产车间, \'\') LIKE ?'
                params.append(f'%{生产车间}%')

            st = clean_arg(args, 'st').lower() in ('1', 'true', 'yes', 'on')
            st2 = clean_arg(args, 'st2').lower() in ('1', 'true', 'yes', 'on')
            if mode == 'body' and st:
                st_parts = []
                if _col_exists(columns, '半成品名称'):
                    st_parts.append("ISNULL(t.半成品名称, '') = '合金锁体'")
                if _col_exists(columns, 'ItemExternalId'):
                    st_parts.append("ISNULL(t.ItemExternalId, '') LIKE '24%'")
                if st_parts:
                    query += ' AND (' + ' OR '.join(st_parts) + ')'
            if mode == 'body' and st2 and _col_exists(columns, 'ItemExternalId'):
                query += " AND ISNULL(t.ItemExternalId, '') LIKE '21%'"

            if _col_exists(columns, 'FinishedDate'):
                query += ' ORDER BY CASE WHEN CAST(t.FinishedDate AS DATE) = CAST(GETDATE() AS DATE) THEN 0 ELSE 1 END, t.FinishedDate DESC, t.OrderNumber DESC'
            else:
                query += ' ORDER BY t.OrderNumber DESC'

            cursor.execute(query, params)
            rows = cursor.fetchall()
            renamed_columns = [WORKSHOP_COLUMN_RENAMES.get(name, name) for name in display_columns]
            data = [_rename_row_keys(dict(zip(display_columns, row))) for row in rows]
            return {
                'data': data,
                'columns': renamed_columns,
                'raw_columns': True,
                'total': len(data),
            }

        if mode == 'key':
            query = cte_sql + '''
            SELECT t.*
            FROM source_rows t
            WHERE 1=1
            '''

            if 订单批号:
                query += ' AND t.OrderNumber LIKE ?'
                params.append(f'%{订单批号}%')

            name_col = _first_existing_col(columns, ['半成品名称', '外协件名称', '品名', '物料名称', 'Name'])
            if 外协件名称 and name_col:
                query += f" AND t.[{_safe_col(name_col)}] LIKE ?"
                params.append(f'%{外协件名称}%')

            spec_col = _first_existing_col(columns, ['半成品规格', '规格型号', '规格', '型号'])
            if 规格型号 and spec_col:
                query += f" AND t.[{_safe_col(spec_col)}] LIKE ?"
                params.append(f'%{规格型号}%')

            if _col_exists(columns, 'FinishedDate'):
                query += ' ORDER BY CASE WHEN CAST(t.FinishedDate AS DATE) = CAST(GETDATE() AS DATE) THEN 0 ELSE 1 END, t.FinishedDate DESC, t.OrderNumber DESC'
            else:
                query += ' ORDER BY t.OrderNumber DESC'

            cursor.execute(query, params)
            rows = cursor.fetchall()
            row_columns = display_columns
            data = [_rename_row_keys(dict(zip(row_columns, row))) for row in rows]
            return {
                'data': data,
                'columns': [_decode_mojibake(name) for name in row_columns],
                'raw_columns': True,
                'total': len(data),
            }

        remark_expr = _resolve_remark_expr(columns)
        name_expr, name_col = _text_expr(columns, ['半成品名称', '外协件名称', '品名', '物料名称', 'Name'])
        spec_expr, spec_col = _text_expr(columns, ['半成品规格', '规格型号', '规格', '型号'])
        qty_expr, _ = _int_expr(columns, ['EachFinishedQty', 'FinishedQty', '数量', '订单数量'])
        unit_expr, _ = _text_expr(columns, ['单位', 'Unit'], max_len=50)
        project_expr, _ = _text_expr(columns, ['外协项目1', '外协项目', '加工项目'])
        quality_expr, _ = _text_expr(columns, ['品质要求1', '品质要求', '质量要求'])
        finish_date_expr = 't.[FinishedDate]' if _col_exists(columns, 'FinishedDate') else 'CAST(NULL AS DATETIME)'
        delivery_expr = "ISNULL(v.确定交期, t.[确定交期])" if _col_exists(columns, '确定交期') else 'v.确定交期'
        gross_expr, _ = _decimal_expr(columns, ['盆的重量_千克', '毛重'])
        pack_expr, _ = _decimal_expr(columns, ['每盆重量或只数', '每盆只数'])
        unit_weight_expr, _ = _decimal_expr(columns, ['物料单重_克', '单重_克'])

        query = cte_sql + f'''
        SELECT
            t.OrderNumber AS 订单号,
            t.OrderNumber AS 订单批号,
            ISNULL(v.锁类分区, '') AS 分区,
            {name_expr} AS 外协件名称,
            {spec_expr} AS 规格型号,
            {qty_expr} AS 订单数量,
            {unit_expr} AS 单位,
            {remark_expr} AS 备注原始,
            '' AS 备注,
            {project_expr} AS 外协项目,
            {quality_expr} AS 品质要求,
            {finish_date_expr} AS 交货期限,
            CAST(NULL AS DATETIME) AS 上线日期,
            {delivery_expr} AS 订单整货期,
            ISNULL(v.锁类分区, '') AS 责任车间,
            {gross_expr} AS 毛重,
            {pack_expr} AS 每盆只数,
            {unit_weight_expr} AS 单重_克,
            CAST(0 AS DECIMAL(18, 2)) AS 净重
        FROM source_rows t
        LEFT JOIN department2020.dbo.V_销售订单2 v ON t.OrderNumber = v.sheet_lot
        WHERE 1=1
        '''

        if 订单批号:
            query += ' AND t.OrderNumber LIKE ?'
            params.append(f'%{订单批号}%')
        if 外协件名称 and name_col:
            query += f" AND t.[{_safe_col(name_col)}] LIKE ?"
            params.append(f'%{外协件名称}%')
        if 规格型号 and spec_col:
            query += f" AND t.[{_safe_col(spec_col)}] LIKE ?"
            params.append(f'%{规格型号}%')
        if 区域:
            query += ' AND v.锁类分区 LIKE ?'
            params.append(f'%{区域}%')

        if mode == 'body' and 生产车间 and _col_exists(columns, '生产车间'):
            query += ' AND ISNULL(t.生产车间, \'\') LIKE ?'
            params.append(f'%{生产车间}%')

        st = clean_arg(args, 'st').lower() in ('1', 'true', 'yes', 'on')
        st2 = clean_arg(args, 'st2').lower() in ('1', 'true', 'yes', 'on')
        if mode == 'body' and st:
            st_parts = []
            if _col_exists(columns, '半成品名称'):
                st_parts.append("ISNULL(t.半成品名称, '') = '合金锁体'")
            if _col_exists(columns, 'ItemExternalId'):
                st_parts.append("ISNULL(t.ItemExternalId, '') LIKE '24%'")
            if st_parts:
                query += ' AND (' + ' OR '.join(st_parts) + ')'
        if mode == 'body' and st2 and _col_exists(columns, 'ItemExternalId'):
            query += " AND ISNULL(t.ItemExternalId, '') LIKE '21%'"

        if _col_exists(columns, 'FinishedDate'):
            query += ' ORDER BY t.FinishedDate DESC, t.OrderNumber DESC'
        else:
            query += ' ORDER BY t.OrderNumber DESC'
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = display_columns
        data = [_rename_row_keys(dict(zip(columns, row))) for row in rows]
        return _post_process_rows(data)
    finally:
        cursor.close()
        conn.close()


def query_checklist_data(args, get_sqlserver_connection):
    workshop = clean_arg(args, '车间类型') or clean_arg(args, 'workshop') or 'grinding'
    workshop = workshop.lower()
    config = WORKSHOP_MAP.get(workshop, WORKSHOP_MAP['grinding'])
    if config['mode'] == 'grinding':
        return _query_grinding_data(args, get_sqlserver_connection)
    return _query_workshop_shift_data(args, get_sqlserver_connection, config['table'], config['mode'])


def query_finished_qty_all(args, get_sqlserver_connection):
    order_number = clean_arg(args, 'OrderNumber') or clean_arg(args, '订单批号') or clean_arg(args, '订单号')
    if not order_number:
        return []

    conn = get_sqlserver_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''
            SELECT *
            FROM department2020.dbo.APS_FinishedQty_All
            WHERE OrderNumber = ?
            ''',
            (order_number,)
        )
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description] if cursor.description else []
        return [
            {column: _json_safe_value(value) for column, value in zip(columns, row)}
            for row in rows
        ]
    finally:
        cursor.close()
        conn.close()
