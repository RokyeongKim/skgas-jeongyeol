import sqlite3, os

db = os.path.join(os.path.dirname(__file__), "data", "cases.db")
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM reports")
print("삭제 전 제보 건수:", c.fetchone()[0])
c.execute("DELETE FROM reports")
conn.commit()
c.execute("SELECT COUNT(*) FROM reports")
print("삭제 후 제보 건수:", c.fetchone()[0])
conn.close()
print("완료")
