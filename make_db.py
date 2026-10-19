import sqlite3

# todo.db라는 이름의 메모장 파일을 엽니다. (없으면 새로 생성됩니다)
conn = sqlite3.connect("todo.db")
cursor = conn.cursor()

# 일정표 상자를 만듭니다 (날짜, 할 일, 완료 여부)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    task TEXT,
    is_done INTEGER DEFAULT 0
)
"""
)

conn.commit()
conn.close()
print("🎉 축하합니다! 일정 저장용 메모장(todo.db)이 완벽하게 만들어졌습니다!")