import duckdb
con = duckdb.connect("predictions.duckdb")
df = con.execute("SELECT * FROM predictions").df()
print(df)
