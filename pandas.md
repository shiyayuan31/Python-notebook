# Pandas速查手册
## 1.数据结构
### series
```Python
s = pd.Series(data, index=index_list)  # 创建Series
s.values  # 获取值数组
s.index   # 获取索引
```

### DataFrame
```Python
df = pd.DataFrame(data, columns=col_list, index=index_list)  # 创建DataFrame
df.columns  # 列名列表
df.index    # 行索引
df.shape    # 维度 (行数, 列数)
df.dtypes   # 各列数据类型
```


## 2.数据读取与保存
```Python
df = pd.DataFrame(data, columns=col_list, index=index_list)  # 创建DataFrame
df.columns  # 列名列表
df.index    # 行索引
df.shape    # 维度 (行数, 列数)
df.dtypes   # 各列数据类型
```

## 3.数据查看与筛选
```Python
df.head(n)     # 查看前n行
df.tail(n)     # 查看后n行
df.sample(n)   # 随机抽样n行
df.describe()  # 数值列统计摘要
df.info()      # 数据概览（类型、非空值）

# 筛选数据
df[col_name]          # 选择单列
df[['col1', 'col2']]  # 选择多列
df.loc[row_indexer, col_indexer]  # 按标签选择
df.iloc[row_num, col_num]         # 按位置选择
df.query('age > 30 & salary < 5000')  # 条件查询
```

## 4.数据清洗
```Python
# 处理缺失值
df.dropna(axis=0, how='any')  # 删除含缺失值的行
df.fillna(value)              # 填充缺失值
df.isnull()                   # 检测缺失值

# 去重
df.drop_duplicates(subset=['col1', 'col2'])  # 按列去重

# 类型转换
df['col'] = df['col'].astype(int)  # 转换数据类型
```

## 5.数据处理
```Python
# 添加/删除列
df['new_col'] = values        # 添加新列
df.drop('col', axis=1, inplace=True)  # 删除列

# 重命名列
df.rename(columns={'old_name': 'new_name'}, inplace=True)

# 应用函数
df['col'].apply(lambda x: x*2)  # 应用函数到列
df.map(func)                    # 元素级操作
```

## 6.数据分组与聚合
```Python
# 分组统计
grouped = df.groupby('group_col')
grouped['value_col'].agg(['mean', 'sum', 'count'])  # 聚合操作

# 透视表
pd.pivot_table(df, values='val_col', index='row_col', columns='col_col', aggfunc=np.mean)
```

## 7.合并与连接
```Python
pd.concat([df1, df2], axis=0)  # 纵向拼接
pd.merge(df1, df2, on='key_col', how='inner')  # SQL风格合并
df1.join(df2, on='key_col')    # 按索引合并
```

## 8.时间序列处理
```Python
df['date_col'] = pd.to_datetime(df['date_str'])  # 转换为日期类型
df.set_index('date_col', inplace=True)           # 设为索引
df.resample('M').mean()  # 按月重采样
```


## 其他实用操作
```Python
# 排序
df.sort_values(by='col', ascending=False)

# 重置索引
df.reset_index(drop=True, inplace=True)  # 丢弃旧索引

# 设置索引
df.set_index('col', inplace=True)
```

### 速查技巧：

>使用 df.T 转置数据

>用 df.copy() 避免链式赋值警告

>pd.set_option('display.max_columns', 100) 调整显示列数
