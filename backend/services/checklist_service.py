from collections import defaultdict


def clean_arg(args, name, fallback=''):
    value = args.get(name, fallback)
    if value is None:
        return ''
    value = str(value).strip()
    if value.lower() in ('', 'null', 'undefined', 'none'):
        return ''
    return value


def query_checklist_data(args, get_sqlserver_connection):
    订单批号 = clean_arg(args, '订单批号') or clean_arg(args, '订单号')
    外协件名称 = clean_arg(args, '外协件名称')
    规格型号 = clean_arg(args, '规格型号')
    区域 = clean_arg(args, '区域')
    查询时间 = clean_arg(args, '查询时间')
    开始日期 = clean_arg(args, '开始日期')
    结束日期 = clean_arg(args, '结束日期')

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
    if 外协件名称:
        query += ' AND t.半成品名称 LIKE ?'
        params.append(f'%{外协件名称}%')
    if 规格型号:
        query += ' AND t.半成品规格 LIKE ?'
        params.append(f'%{规格型号}%')
    if 区域:
        query += ' AND v.锁类分区 LIKE ?'
        params.append(f'%{区域}%')

    query += ' ORDER BY t.半成品规格, t.OrderNumber, t.FinishedDate'

    conn = get_sqlserver_connection()
    cursor = conn.cursor()
    try:
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
            item.pop('每盆只数', None)
            item.pop('单重_克', None)

        data.sort(key=lambda x: (
            x.get('规格型号分组') or '',
            x.get('订单号') or '',
            str(x.get('订单整货期') or '')
        ))

        return data
    finally:
        cursor.close()
        conn.close()
