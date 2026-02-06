import pandas as pd

df = pd.read_csv('data.csv')
# describe(): 수치형 컬럼의 통계 요약(count, mean, std, min, max 등) 반환
print(df.describe())