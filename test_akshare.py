"""Test different AKShare methods to get full stock list"""
import akshare as ak
import baostock as bs
import pandas as pd

print("=" * 60)
print("Testing different methods to get A-stock list")
print("=" * 60)

# Method 1: AKShare stock_info_a_code_name
print("\n1. Testing AKShare stock_info_a_code_name():")
try:
    df = ak.stock_info_a_code_name()
    print(f"   Success! Got {len(df)} stocks")
    print(f"   Columns: {df.columns.tolist()}")
    print(f"   First 5: {df['code'].head().tolist()}")
except Exception as e:
    print(f"   Failed: {e}")

# Method 2: AKShare stock_zh_a_spot (need to extract codes)
print("\n2. Testing AKShare stock_zh_a_spot():")
try:
    df = ak.stock_zh_a_spot()
    print(f"   Success! Got {len(df)} stocks")
    print(f"   Columns: {df.columns.tolist()}")
    codes = df['代码'].tolist()
    print(f"   First 5 codes: {codes[:5]}")
except Exception as e:
    print(f"   Failed: {e}")

# Method 3: BaoStock stock list
print("\n3. Testing BaoStock stock list:")
try:
    lg = bs.login()
    if lg.error_code == '0':
        rs = bs.query_stock_basic()
        if rs.error_code == '0':
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            df = pd.DataFrame(data_list, columns=rs.fields)
            print(f"   Success! Got {len(df)} stocks")
            print(f"   Columns: {df.columns.tolist()}")
            # Filter only A-shares (stock_type is '1' for A-share)
            a_shares = df[df['type'] == '1']
            print(f"   A-shares: {len(a_shares)}")
            print(f"   First 5 codes: {a_shares['code'].head().tolist()}")
        bs.logout()
    else:
        print(f"   BaoStock login failed: {lg.error_msg}")
except Exception as e:
    print(f"   Failed: {e}")

# Method 4: AKShare individual market lists
print("\n4. Testing AKShare individual market lists:")
try:
    # Get Shanghai A-shares
    sh_stocks = ak.stock_info_sh_name_code(indicator="主板A股")
    print(f"   Shanghai A-shares: {len(sh_stocks)}")
    # Get Shenzhen A-shares
    sz_stocks = ak.stock_info_sz_name_code(indicator="A股列表")
    print(f"   Shenzhen A-shares: {len(sz_stocks)}")
    total = len(sh_stocks) + len(sz_stocks)
    print(f"   Total A-shares: {total}")
except Exception as e:
    print(f"   Failed: {e}")

print("\n" + "=" * 60)
