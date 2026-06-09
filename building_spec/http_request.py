import requests
import json
import os
import zipfile
import xml.etree.ElementTree as ET

JUDGE_API_KEY = ""  # 请在 Building 机评界面配置，或在 user_config.json 中设置
API_URL = ""  # 请配置 JUDGE API 地址

def read_cases_from_excel(excel_path):
    """从 Excel 文件读取测试用例（使用 zip 和 xml 解析）"""
    cases = []
    
    # 打开 Excel 文件（实际是 zip）
    with zipfile.ZipFile(excel_path, 'r') as z:
        # 读取 shared strings
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            with z.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                # 命名空间
                ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for si in root.findall('main:si', ns):
                    t = si.find('main:t', ns)
                    if t is not None:
                        shared_strings.append(t.text)
                    else:
                        # 处理多个 t 元素的情况
                        text_parts = []
                        for t in si.findall('.//main:t', ns):
                            text_parts.append(t.text if t.text else '')
                        shared_strings.append(''.join(text_parts))
        
        # 读取工作表
        sheet_file = 'xl/worksheets/sheet1.xml'
        if sheet_file not in z.namelist():
            raise Exception("未找到工作表 sheet1")
        
        with z.open(sheet_file) as f:
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            sheet_data = root.find('main:sheetData', ns)
            if sheet_data is None:
                raise Exception("无法读取工作表数据失败")
            
            rows = []
            for row_elem in sheet_data.findall('main:row', ns):
                row_data = []
                for cell in row_elem.findall('main:c', ns):
                    cell_type = cell.get('t')
                    cell_value = cell.find('main:v', ns)
                    
                    value = None
                    if cell_value is not None:
                        if cell_type == 's':
                            # 共享字符串索引
                            idx = int(cell_value.text)
                            value = shared_strings[int(idx)]
                        else:
                            value = cell_value.text
                    row_data.append(value)
                rows.append(row_data)
    
    if not rows:
        raise Exception("未读取到数据")
    
    # 查找表头和数据
    
    headers = rows[0] if rows else []
    query_col = None
    base_token_col = None
    
    for idx, header in enumerate(headers):
        if header and "query" in str(header).lower():
            query_col = idx
        if header and ("base_token" in str(header).lower() or "basetoken" in str(header).lower()):
            base_token_col = idx
    
    if query_col is None:
        raise Exception("未找到 query 列")
    if base_token_col is None:
        raise Exception("未找到 base_token 列")
    
    # 读取数据行
    for i, row in enumerate(rows[1:], 1):
        if not row or len(row) <= max(query_col, base_token_col):
            continue
        query_val = row[query_col] if len(row) > query_col else None
        if query_val is None:
            continue
        base_token_val = row[base_token_col] if len(row) > base_token_col else None
        case = {
            "id": f"SpecQuery_v0.7_{i:03d}",
            "query": str(query_val or ""),
            "baseToken": str(base_token_val or "")
        }
        cases.append(case)
    
    print(f"成功读取 {len(cases)} 个测试用例")
    return cases

def send_judge_request(cases, agent="building", dimensions=["table", "permission", "workflow", "formula", "dashboard"], concurrency=5, mode="spec"):
    """发送请求到 judge 接口"""
    headers = {
        "Content-Type": "application/json",
        "x-judge-api-key": JUDGE_API_KEY
    }
    
    data = {
        "agent": agent,
        "cases": cases,
        "options": {
            "dimensions": dimensions,
            "concurrency": concurrency,
            "mode": mode
        }
    }
    
    response = requests.post(API_URL, headers=headers, json=data)
    return response

if __name__ == "__main__":
    excel_path = "input.csv"  # 虽然是 .csv 扩展名，但实际是 Excel 文件
    
    # 检查文件是否存在
    if not os.path.exists(excel_path):
        print(f"错误：文件 {excel_path} 不存在")
        exit(1)
    
    try:
        # 读取测试用例
        print(f"正在从 {excel_path} 读取测试用例...")
        cases = read_cases_from_excel(excel_path)
        
        # 发送请求
        print(f"正在发送请求到 {API_URL}...")
        response = send_judge_request(cases)
        
        # 输出响应信息
        print(f"\n{'='*60}")
        print(f"响应状态码：{response.status_code}")
        
        # 提取并显示重要的响应头
        request_id = response.headers.get('x-bytefaas-request-id')
        tt_logid = response.headers.get('x-tt-logid')
        tt_trace_id = response.headers.get('x-tt-trace-id')
        
        print(f"\n📋 重要标识信息：")
        if request_id:
            print(f"  x-bytefaas-request-id: {request_id}")
        if tt_logid:
            print(f"  x-tt-logid: {tt_logid}")
        if tt_trace_id:
            print(f"  x-tt-trace-id: {tt_trace_id}")
        
        if response.status_code == 201:
            print(f"\n✅ 请求成功提交（异步任务已创建）")
            print(f"\n📌 下一步：")
            print(f"   1. 请加入指定的飞书群等待结果通知")
            print(f"   2. 结果会以群消息和飞书报告的形式发送")
            print(f"   3. 如遇问题，请保存上述 ID 联系 @刘恒伟 排查")
            
            # 保存 ID 信息到文件
            log_file = "judge_request_ids.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if request_id:
                    f.write(f"x-bytefaas-request-id: {request_id}\n")
                if tt_logid:
                    f.write(f"x-tt-logid: {tt_logid}\n")
                if tt_trace_id:
                    f.write(f"x-tt-trace-id: {tt_trace_id}\n")
                f.write(f"测试用例数: {len(cases)}\n")
            
            print(f"\n💾 这些 ID 已保存到: {log_file}")
            
        elif 200 <= response.status_code < 300:
            print("✅ 请求成功")
        else:
            print(f"⚠️ 请求返回状态码: {response.status_code}")
        
        print(f"{'='*60}\n")
            
    except requests.exceptions.RequestException as e:
        print(f"网络请求异常：{e}")
    except Exception as e:
        print(f"程序运行异常：{e}")
        import traceback
        traceback.print_exc()
