import time
import datetime
import html
import os
import sqlite3
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google import genai

app = FastAPI(
    title="Executive Task Intelligence System",
    description="최고급 SaaS 대시보드 UI 및 Gemini AI 기반 경영진 브리핑 시스템입니다.",
    version="4.0.0",
)

# 발급받으신 Gemini API 키 (서버 환경변수에서 로드)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


# --- DB connection helper ---
def get_db():
    conn = sqlite3.connect("todo.db", timeout=10)
    return conn


# --- DB 초기화 및 관리 ---
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            task TEXT NOT NULL,
            category TEXT DEFAULT '업무',
            priority TEXT DEFAULT '보통',
            is_done INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


init_db()


# --- 메인 페이지 ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home_page():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, task, category, priority, is_done FROM todos ORDER BY id DESC")
    todos = cursor.fetchall()
    conn.close()

    total_count = len(todos)
    done_count = sum(1 for t in todos if t[5] == 1)
    pending_count = total_count - done_count
    progress_rate = int((done_count / total_count * 100)) if total_count > 0 else 0

    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # 업무 목록 카드 HTML 생성
    items_html = ""
    for t in todos:
        t_id, t_date, t_task, t_cat, t_prio, t_done = t
        
        # D-Day 계산
        try:
            target_date = datetime.datetime.strptime(t_date, "%Y-%m-%d").date()
            days_left = (target_date - datetime.date.today()).days
            if days_left == 0:
                dday_str = "D-Day"
            elif days_left > 0:
                dday_str = f"D-{days_left}"
            else:
                dday_str = f"D+{abs(days_left)}"
        except Exception:
            dday_str = "D-?"

        prio_color = "#ef4444" if t_prio == "높음" else ("#f59e0b" if t_prio == "보통" else "#3b82f6")
        checked_attr = "checked" if t_done else ""
        done_style = "text-decoration: line-through; opacity: 0.5;" if t_done else ""

        # JS 탈출 및 HTML 이스케이프 처리
        safe_task = html.escape(t_task)
        js_task = safe_task.replace("'", "\\'").replace('"', '\\"')

        items_html += f"""
        <div class="todo-card">
            <div class="todo-top-row">
                <input type="checkbox" onchange="toggleDone({t_id}, this.checked)" {checked_attr}>
                <div class="badge-group">
                    <span class="badge" style="background: rgba(239,68,68,0.15); color: {prio_color};">{t_prio}</span>
                    <span class="badge" style="background: rgba(59,130,246,0.15); color: #60a5fa;">{t_cat}</span>
                    <span class="badge" style="background: rgba(139,92,246,0.15); color: #a78bfa;">{dday_str}</span>
                </div>
            </div>
            <div class="todo-title" style="{done_style}">
                [{t_date}] {safe_task}
            </div>
            <div class="todo-actions">
                <button class="btn-action" onclick="editTodo({t_id}, '{js_task}')">수정</button>
                <button class="btn-action btn-del" onclick="deleteTodo({t_id})">삭제</button>
            </div>
        </div>
        """

    if not items_html:
        items_html = '<div style="text-align:center; color:#9ca3af; padding:20px;">등록된 과제가 없습니다.</div>'

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Executive Task Intelligence</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
        <style>
            :root {{
                --bg: #090d16;
                --panel: #111827;
                --panel-border: #1f2937;
                --text-primary: #f9fafb;
                --text-secondary: #9ca3af;
                --accent-blue: #3b82f6;
                --accent-indigo: #6366f1;
                --accent-emerald: #10b981;
                --accent-amber: #f59e0b;
                --radius-lg: 12px;
                --radius-md: 8px;
            }}

            * {{ box-sizing: border-box; margin: 0; padding: 0; }}

            body {{
                font-family: 'Pretendard', system-ui, sans-serif;
                background-color: var(--bg);
                color: var(--text-primary);
                padding: 20px;
                line-height: 1.5;
            }}

            .container {{
                max-width: 1000px;
                margin: 0 auto;
                width: 100%;
            }}

            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}

            .header h1 {{
                font-size: 1.5rem;
                font-weight: 700;
                background: linear-gradient(to right, #60a5fa, #a78bfa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}

            .status-badge {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 4px 10px;
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 20px;
                color: #34d399;
                font-size: 0.8rem;
            }}

            .status-dot {{
                width: 6px;
                height: 6px;
                background-color: #34d399;
                border-radius: 50%;
            }}

            /* KPI Grid */
            .kpi-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 12px;
                margin-bottom: 20px;
            }}

            .kpi-card {{
                background-color: var(--panel);
                border: 1px solid var(--panel-border);
                border-radius: var(--radius-lg);
                padding: 16px;
            }}

            .kpi-label {{ font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 6px; }}
            .kpi-value {{ font-size: 1.8rem; font-weight: 700; }}

            /* Form & Cards */
            .card {{
                background-color: var(--panel);
                border: 1px solid var(--panel-border);
                border-radius: var(--radius-lg);
                padding: 20px;
                margin-bottom: 20px;
            }}

            .card-title {{
                font-size: 1.1rem;
                font-weight: 600;
                margin-bottom: 16px;
            }}

            .form-grid {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}

            .form-control {{
                background: #1f2937;
                border: 1px solid #374151;
                color: var(--text-primary);
                padding: 10px 14px;
                border-radius: var(--radius-md);
                font-size: 0.9rem;
                outline: none;
            }}

            .form-control:focus {{ border-color: var(--accent-blue); }}

            .btn-primary {{
                background: var(--accent-blue);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: var(--radius-md);
                font-weight: 600;
                cursor: pointer;
            }}

            /* 업무 목록 카드 디자인 */
            .todo-card {{
                background: rgba(31, 41, 55, 0.4);
                border: 1px solid var(--panel-border);
                border-radius: var(--radius-md);
                padding: 14px;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
            }}

            .todo-top-row {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}

            .badge-group {{
                display: flex;
                gap: 6px;
                align-items: center;
            }}

            .badge {{
                display: inline-block;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 600;
                white-space: nowrap;
            }}

            .todo-title {{
                flex: 1;
                font-size: 0.95rem;
                font-weight: 500;
                word-break: break-all;
            }}

            .todo-actions {{
                display: flex;
                gap: 6px;
            }}

            .btn-action {{
                background: #374151;
                color: #d1d5db;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 0.8rem;
                cursor: pointer;
            }}

            .btn-del {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}

            .btn-ai {{
                width: 100%;
                background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                color: white;
                border: none;
                padding: 12px;
                border-radius: var(--radius-md);
                font-weight: 600;
                font-size: 0.95rem;
                cursor: pointer;
                margin-bottom: 12px;
            }}

            @media (max-width: 768px) {{
                body {{ padding: 10px; }}
                .kpi-grid {{ grid-template-columns: repeat(2, 1fr); gap: 8px; }}
                .kpi-card {{ padding: 12px; }}
                .kpi-value {{ font-size: 1.4rem; }}

                .form-grid {{
                    flex-direction: column !important;
                    width: 100% !important;
                }}
                .form-control, .btn-primary {{
                    width: 100% !important;
                }}

                .todo-card {{
                    flex-direction: column !important;
                    align-items: flex-start !important;
                    gap: 10px !important;
                }}

                .todo-top-row {{
                    width: 100% !important;
                    justify-content: flex-start !important;
                }}

                .todo-title {{
                    width: 100% !important;
                    font-size: 0.9rem !important;
                    line-height: 1.4 !important;
                }}

                .todo-actions {{
                    width: 100% !important;
                    display: flex !important;
                    gap: 8px !important;
                }}

                .btn-action {{
                    flex: 1 !important;
                    height: 38px !important;
                    font-size: 0.85rem !important;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>Executive Task Intelligence</h1>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">Enterprise Management System</div>
                </div>
                <div class="status-badge">
                    <span class="status-dot"></span> System Live
                </div>
            </div>

            <!-- KPI 실시간 대시보드 -->
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">전체 등록 과제</div>
                    <div class="kpi-value" style="color: var(--accent-blue);">{total_count}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">미완료 핵심 과제</div>
                    <div class="kpi-value" style="color: var(--accent-amber);">{pending_count}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">프로젝트 완료율</div>
                    <div class="kpi-value" style="color: var(--accent-emerald);">{progress_rate}%</div>
                </div>
            </div>

            <!-- 신규 업무 할당 -->
            <div class="card">
                <div class="card-title">신규 업무 일정 할당</div>
                <form action="/add" method="post" class="form-grid">
                    <input type="date" name="date" value="{today_str}" class="form-control" required>
                    <select name="category" class="form-control">
                        <option value="업무">업무</option>
                        <option value="미팅">미팅</option>
                        <option value="프로젝트">프로젝트</option>
                        <option value="기타">기타</option>
                    </select>
                    <select name="priority" class="form-control">
                        <option value="보통">우선순위: 보통</option>
                        <option value="높음">우선순위: 높음</option>
                        <option value="낮음">우선순위: 낮음</option>
                    </select>
                    <input type="text" name="task" placeholder="담당 업무 세부 내용을 입력하세요..." class="form-control" style="flex:1;" required>
                    <button type="submit" class="btn-primary">등록</button>
                </form>
            </div>

            <!-- 진행 중인 업무 목록 -->
            <div class="card">
                <div class="card-title">진행 중인 업무 목록</div>
                {items_html}
            </div>

            <!-- Gemini AI Assistant -->
            <div class="card">
                <div class="card-title">Gemini Executive AI Assistant</div>
                <button class="btn-ai" onclick="getAiBriefing()">🤖 AI 실무 우선순위 & 리스크 브리핑 리포트 생성</button>
                <div id="aiResult" style="display:none; background:#1f2937; padding:16px; border-radius:8px; font-size:0.9rem; white-space:pre-line; line-height:1.6; color:#e5e7eb;"></div>
            </div>
        </div>

        <script>
            async function toggleDone(id, isDone) {{
                await fetch('/toggle/' + id + '?is_done=' + (isDone ? 1 : 0), {{ method: 'POST' }});
                location.reload();
            }}

            async function deleteTodo(id) {{
                if (confirm('해당 과제를 삭제하시겠습니까?')) {{
                    await fetch('/delete/' + id, {{ method: 'POST' }});
                    location.reload();
                }}
            }}

            async function editTodo(id, currentTask) {{
                const newTask = prompt('수정할 업무 내용을 입력하세요:', currentTask);
                if (newTask && newTask !== currentTask) {{
                    await fetch('/edit/' + id + '?task=' + encodeURIComponent(newTask), {{ method: 'POST' }});
                    location.reload();
                }}
            }}

            async function getAiBriefing() {{
                const resDiv = document.getElementById('aiResult');
                resDiv.style.display = 'block';
                resDiv.innerText = '🤖 Gemini AI가 미완료 업무 데이터를 분석 중입니다...';
                
                try {{
                    const response = await fetch('/ai-briefing');
                    const data = await response.json();
                    resDiv.innerText = data.briefing;
                }} catch (e) {{
                    resDiv.innerText = '❌ 브리핑 생성 중 오류가 발생했습니다.';
                }}
            }}
        </script>
    </body>
    </html>
    """
    return html_content


# --- API 엔드포인트 ---
@app.post("/add")
def add_todo(date: str = Form(...), task: str = Form(...), category: str = Form("업무"), priority: str = Form("보통")):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO todos (date, task, category, priority) VALUES (?, ?, ?, ?)", (date, task, category, priority))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)


@app.post("/toggle/{todo_id}")
def toggle_todo(todo_id: int, is_done: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE todos SET is_done = ? WHERE id = ?", (is_done, todo_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/delete/{todo_id}")
def delete_todo(todo_id: int):
    conn = get_db()
    cursor = conn.cursor()
    # 튜플 파라미터 적용 (todo_id,)
    cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/edit/{todo_id}")
def edit_todo(todo_id: int, task: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE todos SET task = ? WHERE id = ?", (task, todo_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.get("/ai-briefing")
def ai_briefing():
    if not GEMINI_API_KEY:
        return {"briefing": "⚠️ Gemini API 키가 설정되지 않았습니다. 환경변수에 GEMINI_API_KEY를 등록해 주세요."}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT date, task, category, priority FROM todos WHERE is_done = 0 ORDER BY date ASC")
    pending = cursor.fetchall()
    conn.close()

    if not pending:
        return {"briefing": "🎉 현재 미완료된 과제가 없습니다! 완벽하게 업무를 처리하셨습니다."}

    todo_text = "\n".join([f"- [{p[0]}] [{p[2]}/{p[3]}] {p[1]}" for p in pending])
    prompt = f"다음은 현재 미완료된 경영 일정 및 업무 리스트입니다:\n{todo_text}\n\n경영진을 위해 업무 우선순위 분석 및 실행 리스크 브리핑 리포트를 간결하게 작성해 주세요."

# --- 수정 위치: ai_briefing() 함수 내부 ---

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-3.8-flash",  # <--- 이 부분을 gemini-3.8-flash 로 변경!
            contents=prompt,
        )
        return {"briefing": response.text}
    except Exception as e:
=======
import datetime
import html
import os
import sqlite3
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google import genai

app = FastAPI(
    title="Executive Task Intelligence System",
    description="최고급 SaaS 대시보드 UI 및 Gemini AI 기반 경영진 브리핑 시스템입니다.",
    version="4.0.0",
)

# 발급받으신 Gemini API 키 (서버 환경변수에서 로드)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


# --- DB connection helper ---
def get_db():
    conn = sqlite3.connect("todo.db", timeout=10)
    return conn


# --- DB 초기화 및 관리 ---
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            task TEXT NOT NULL,
            category TEXT DEFAULT '업무',
            priority TEXT DEFAULT '보통',
            is_done INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


init_db()


# --- 메인 페이지 ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home_page():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, task, category, priority, is_done FROM todos ORDER BY id DESC")
    todos = cursor.fetchall()
    conn.close()

    total_count = len(todos)
    done_count = sum(1 for t in todos if t[5] == 1)
    pending_count = total_count - done_count
    progress_rate = int((done_count / total_count * 100)) if total_count > 0 else 0

    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # 업무 목록 카드 HTML 생성
    items_html = ""
    for t in todos:
        t_id, t_date, t_task, t_cat, t_prio, t_done = t
        
        # D-Day 계산
        try:
            target_date = datetime.datetime.strptime(t_date, "%Y-%m-%d").date()
            days_left = (target_date - datetime.date.today()).days
            if days_left == 0:
                dday_str = "D-Day"
            elif days_left > 0:
                dday_str = f"D-{days_left}"
            else:
                dday_str = f"D+{abs(days_left)}"
        except Exception:
            dday_str = "D-?"

        prio_color = "#ef4444" if t_prio == "높음" else ("#f59e0b" if t_prio == "보통" else "#3b82f6")
        checked_attr = "checked" if t_done else ""
        done_style = "text-decoration: line-through; opacity: 0.5;" if t_done else ""

        # JS 탈출 및 HTML 이스케이프 처리
        safe_task = html.escape(t_task)
        js_task = safe_task.replace("'", "\\'").replace('"', '\\"')

        items_html += f"""
        <div class="todo-card">
            <div class="todo-top-row">
                <input type="checkbox" onchange="toggleDone({t_id}, this.checked)" {checked_attr}>
                <div class="badge-group">
                    <span class="badge" style="background: rgba(239,68,68,0.15); color: {prio_color};">{t_prio}</span>
                    <span class="badge" style="background: rgba(59,130,246,0.15); color: #60a5fa;">{t_cat}</span>
                    <span class="badge" style="background: rgba(139,92,246,0.15); color: #a78bfa;">{dday_str}</span>
                </div>
            </div>
            <div class="todo-title" style="{done_style}">
                [{t_date}] {safe_task}
            </div>
            <div class="todo-actions">
                <button class="btn-action" onclick="editTodo({t_id}, '{js_task}')">수정</button>
                <button class="btn-action btn-del" onclick="deleteTodo({t_id})">삭제</button>
            </div>
        </div>
        """

    if not items_html:
        items_html = '<div style="text-align:center; color:#9ca3af; padding:20px;">등록된 과제가 없습니다.</div>'

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Executive Task Intelligence</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
        <style>
            :root {{
                --bg: #090d16;
                --panel: #111827;
                --panel-border: #1f2937;
                --text-primary: #f9fafb;
                --text-secondary: #9ca3af;
                --accent-blue: #3b82f6;
                --accent-indigo: #6366f1;
                --accent-emerald: #10b981;
                --accent-amber: #f59e0b;
                --radius-lg: 12px;
                --radius-md: 8px;
            }}

            * {{ box-sizing: border-box; margin: 0; padding: 0; }}

            body {{
                font-family: 'Pretendard', system-ui, sans-serif;
                background-color: var(--bg);
                color: var(--text-primary);
                padding: 20px;
                line-height: 1.5;
            }}

            .container {{
                max-width: 1000px;
                margin: 0 auto;
                width: 100%;
            }}

            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}

            .header h1 {{
                font-size: 1.5rem;
                font-weight: 700;
                background: linear-gradient(to right, #60a5fa, #a78bfa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}

            .status-badge {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 4px 10px;
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 20px;
                color: #34d399;
                font-size: 0.8rem;
            }}

            .status-dot {{
                width: 6px;
                height: 6px;
                background-color: #34d399;
                border-radius: 50%;
            }}

            /* KPI Grid */
            .kpi-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 12px;
                margin-bottom: 20px;
            }}

            .kpi-card {{
                background-color: var(--panel);
                border: 1px solid var(--panel-border);
                border-radius: var(--radius-lg);
                padding: 16px;
            }}

            .kpi-label {{ font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 6px; }}
            .kpi-value {{ font-size: 1.8rem; font-weight: 700; }}

            /* Form & Cards */
            .card {{
                background-color: var(--panel);
                border: 1px solid var(--panel-border);
                border-radius: var(--radius-lg);
                padding: 20px;
                margin-bottom: 20px;
            }}

            .card-title {{
                font-size: 1.1rem;
                font-weight: 600;
                margin-bottom: 16px;
            }}

            .form-grid {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}

            .form-control {{
                background: #1f2937;
                border: 1px solid #374151;
                color: var(--text-primary);
                padding: 10px 14px;
                border-radius: var(--radius-md);
                font-size: 0.9rem;
                outline: none;
            }}

            .form-control:focus {{ border-color: var(--accent-blue); }}

            .btn-primary {{
                background: var(--accent-blue);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: var(--radius-md);
                font-weight: 600;
                cursor: pointer;
            }}

            /* 업무 목록 카드 디자인 */
            .todo-card {{
                background: rgba(31, 41, 55, 0.4);
                border: 1px solid var(--panel-border);
                border-radius: var(--radius-md);
                padding: 14px;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
            }}

            .todo-top-row {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}

            .badge-group {{
                display: flex;
                gap: 6px;
                align-items: center;
            }}

            .badge {{
                display: inline-block;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 600;
                white-space: nowrap;
            }}

            .todo-title {{
                flex: 1;
                font-size: 0.95rem;
                font-weight: 500;
                word-break: break-all;
            }}

            .todo-actions {{
                display: flex;
                gap: 6px;
            }}

            .btn-action {{
                background: #374151;
                color: #d1d5db;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 0.8rem;
                cursor: pointer;
            }}

            .btn-del {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}

            .btn-ai {{
                width: 100%;
                background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                color: white;
                border: none;
                padding: 12px;
                border-radius: var(--radius-md);
                font-weight: 600;
                font-size: 0.95rem;
                cursor: pointer;
                margin-bottom: 12px;
            }}

            @media (max-width: 768px) {{
                body {{ padding: 10px; }}
                .kpi-grid {{ grid-template-columns: repeat(2, 1fr); gap: 8px; }}
                .kpi-card {{ padding: 12px; }}
                .kpi-value {{ font-size: 1.4rem; }}

                .form-grid {{
                    flex-direction: column !important;
                    width: 100% !important;
                }}
                .form-control, .btn-primary {{
                    width: 100% !important;
                }}

                .todo-card {{
                    flex-direction: column !important;
                    align-items: flex-start !important;
                    gap: 10px !important;
                }}

                .todo-top-row {{
                    width: 100% !important;
                    justify-content: flex-start !important;
                }}

                .todo-title {{
                    width: 100% !important;
                    font-size: 0.9rem !important;
                    line-height: 1.4 !important;
                }}

                .todo-actions {{
                    width: 100% !important;
                    display: flex !important;
                    gap: 8px !important;
                }}

                .btn-action {{
                    flex: 1 !important;
                    height: 38px !important;
                    font-size: 0.85rem !important;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>Executive Task Intelligence</h1>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">Enterprise Management System</div>
                </div>
                <div class="status-badge">
                    <span class="status-dot"></span> System Live
                </div>
            </div>

            <!-- KPI 실시간 대시보드 -->
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">전체 등록 과제</div>
                    <div class="kpi-value" style="color: var(--accent-blue);">{total_count}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">미완료 핵심 과제</div>
                    <div class="kpi-value" style="color: var(--accent-amber);">{pending_count}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">프로젝트 완료율</div>
                    <div class="kpi-value" style="color: var(--accent-emerald);">{progress_rate}%</div>
                </div>
            </div>

            <!-- 신규 업무 할당 -->
            <div class="card">
                <div class="card-title">신규 업무 일정 할당</div>
                <form action="/add" method="post" class="form-grid">
                    <input type="date" name="date" value="{today_str}" class="form-control" required>
                    <select name="category" class="form-control">
                        <option value="업무">업무</option>
                        <option value="미팅">미팅</option>
                        <option value="프로젝트">프로젝트</option>
                        <option value="기타">기타</option>
                    </select>
                    <select name="priority" class="form-control">
                        <option value="보통">우선순위: 보통</option>
                        <option value="높음">우선순위: 높음</option>
                        <option value="낮음">우선순위: 낮음</option>
                    </select>
                    <input type="text" name="task" placeholder="담당 업무 세부 내용을 입력하세요..." class="form-control" style="flex:1;" required>
                    <button type="submit" class="btn-primary">등록</button>
                </form>
            </div>

            <!-- 진행 중인 업무 목록 -->
            <div class="card">
                <div class="card-title">진행 중인 업무 목록</div>
                {items_html}
            </div>

            <!-- Gemini AI Assistant -->
            <div class="card">
                <div class="card-title">Gemini Executive AI Assistant</div>
                <button class="btn-ai" onclick="getAiBriefing()">🤖 AI 실무 우선순위 & 리스크 브리핑 리포트 생성</button>
                <div id="aiResult" style="display:none; background:#1f2937; padding:16px; border-radius:8px; font-size:0.9rem; white-space:pre-line; line-height:1.6; color:#e5e7eb;"></div>
            </div>
        </div>

        <script>
            async function toggleDone(id, isDone) {{
                await fetch('/toggle/' + id + '?is_done=' + (isDone ? 1 : 0), {{ method: 'POST' }});
                location.reload();
            }}

            async function deleteTodo(id) {{
                if (confirm('해당 과제를 삭제하시겠습니까?')) {{
                    await fetch('/delete/' + id, {{ method: 'POST' }});
                    location.reload();
                }}
            }}

            async function editTodo(id, currentTask) {{
                const newTask = prompt('수정할 업무 내용을 입력하세요:', currentTask);
                if (newTask && newTask !== currentTask) {{
                    await fetch('/edit/' + id + '?task=' + encodeURIComponent(newTask), {{ method: 'POST' }});
                    location.reload();
                }}
            }}

            async function getAiBriefing() {{
                const resDiv = document.getElementById('aiResult');
                resDiv.style.display = 'block';
                resDiv.innerText = '🤖 Gemini AI가 미완료 업무 데이터를 분석 중입니다...';
                
                try {{
                    const response = await fetch('/ai-briefing');
                    const data = await response.json();
                    resDiv.innerText = data.briefing;
                }} catch (e) {{
                    resDiv.innerText = '❌ 브리핑 생성 중 오류가 발생했습니다.';
                }}
            }}
        </script>
    </body>
    </html>
    """
    return html_content


# --- API 엔드포인트 ---
@app.post("/add")
def add_todo(date: str = Form(...), task: str = Form(...), category: str = Form("업무"), priority: str = Form("보통")):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO todos (date, task, category, priority) VALUES (?, ?, ?, ?)", (date, task, category, priority))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)


@app.post("/toggle/{todo_id}")
def toggle_todo(todo_id: int, is_done: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE todos SET is_done = ? WHERE id = ?", (is_done, todo_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/delete/{todo_id}")
def delete_todo(todo_id: int):
    conn = get_db()
    cursor = conn.cursor()
    # 튜플 파라미터 적용 (todo_id,)
    cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/edit/{todo_id}")
def edit_todo(todo_id: int, task: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE todos SET task = ? WHERE id = ?", (task, todo_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.get("/ai-briefing")
def ai_briefing():
    if not GEMINI_API_KEY:
        return {"briefing": "⚠️ Gemini API 키가 설정되지 않았습니다. 환경변수에 GEMINI_API_KEY를 등록해 주세요."}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT date, task, category, priority FROM todos WHERE is_done = 0 ORDER BY date ASC")
    pending = cursor.fetchall()
    conn.close()

    if not pending:
        return {"briefing": "🎉 현재 미완료된 과제가 없습니다! 완벽하게 업무를 처리하셨습니다."}

    todo_text = "\n".join([f"- [{p[0]}] [{p[2]}/{p[3]}] {p[1]}" for p in pending])
    prompt = f"다음은 현재 미완료된 경영 일정 및 업무 리스트입니다:\n{todo_text}\n\n경영진을 위해 업무 우선순위 분석 및 실행 리스크 브리핑 리포트를 간결하게 작성해 주세요."

    # 503 과부하 에러 대비 3회 자동 재시도 로직
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
            )
            return {"briefing": response.text}
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                time.sleep(2)
                continue
            return {"briefing": f"❌ Gemini AI 호출 실패: {str(e)}"}