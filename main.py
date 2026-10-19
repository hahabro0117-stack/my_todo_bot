import datetime
import os
import sqlite3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from google import genai

app = FastAPI(
    title="Executive Task Intelligence System",
    description="최고급 SaaS 대시보드 UI 및 Gemini AI 기반 경영진 브리핑 시스템입니다.",
    version="4.0.0",
)

# 발급받으신 Gemini API 키
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")css


# --- DB 초기화 및 관리 ---
def init_db():
    conn = sqlite3.connect("todo.db")
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


def get_db_tasks():
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, date, task, category, priority, is_done FROM todos ORDER BY is_done ASC, date ASC, id DESC"
    )
    rows = cursor.fetchall()
    conn.close()

    today = datetime.date.today()
    result = []
    for r in rows:
        try:
            task_date = datetime.datetime.strptime(r[1], "%Y-%m-%d").date()
            diff = (task_date - today).days
            if diff == 0:
                d_day = "D-Day"
            elif diff > 0:
                d_day = f"D-{diff}"
            else:
                d_day = f"D+{abs(diff)}"
        except Exception:
            d_day = "-"

        result.append({
            "id": r[0],
            "date": r[1],
            "task": r[2],
            "category": r[3] if r[3] else "업무",
            "priority": r[4] if r[4] else "보통",
            "is_done": bool(r[5]),
            "d_day": d_day,
        })
    return result


# --- 1. 최고급 Premium SaaS UI ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home_page():
    return """
    <!DOCTYPE html>
    <html lang="ko">
   <head>
    <meta charset="UTF-8">
    <!-- 모바일 비율 자동 조절을 위한 필수 메타 태그 (추가/확인) -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <title>Executive Task Intelligence</title>
    ...
        <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
        <style>
            :root {
                --bg: #090d16;
                --panel: #111827;
                --panel-border: #1f2937;
                --panel-hover: #172033;
                --text-primary: #f9fafb;
                --text-secondary: #9ca3af;
                --text-muted: #6b7280;
                --accent-blue: #3b82f6;
                --accent-indigo: #6366f1;
                --accent-emerald: #10b981;
                --accent-rose: #f43f5e;
                --accent-amber: #f59e0b;
                --radius-lg: 12px;
                --radius-md: 8px;
            }

            * { box-sizing: border-box; }
            
            body { 
                font-family: "Pretendard Variable", -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif; 
                padding: 40px 20px; 
                max-width: 900px; 
                margin: auto; 
                background-color: var(--bg); 
                color: var(--text-primary);
                line-height: 1.5;
                -webkit-font-smoothing: antialiased;
            }

            /* 헤더 디자인 */
            .header {
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
                margin-bottom: 28px;
                padding-bottom: 20px;
                border-bottom: 1px solid var(--panel-border);
            }
            .header-title h1 { font-size: 22px; font-weight: 800; letter-spacing: -0.5px; margin: 0; color: #ffffff; }
            .header-title p { font-size: 13px; color: var(--text-secondary); margin: 4px 0 0 0; }
            .status-badge { 
                display: inline-flex; 
                align-items: center; 
                gap: 6px; 
                padding: 4px 10px; 
                background: rgba(16, 185, 129, 0.1); 
                border: 1px solid rgba(16, 185, 129, 0.2); 
                border-radius: 20px; 
                font-size: 12px; 
                color: var(--accent-emerald); 
                font-weight: 600;
            }
            .status-dot { width: 6px; height: 6px; background: var(--accent-emerald); border-radius: 50%; display: inline-block; }

            /* KPI 지표 그리드 */
            .kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
            .kpi-card { background: var(--panel); border: 1px solid var(--panel-border); border-radius: var(--radius-lg); padding: 18px 20px; }
            .kpi-label { font-size: 12px; color: var(--text-muted); font-weight: 500; margin-bottom: 6px; }
            .kpi-value { font-size: 24px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px; }

            /* 프로그레스 바 */
            .progress-container { background: #1f2937; border-radius: 10px; height: 6px; width: 100%; margin-top: 10px; overflow: hidden; }
            .progress-bar { background: linear-gradient(90deg, var(--accent-blue), var(--accent-indigo)); height: 100%; width: 0%; transition: width 0.5s ease; }

            /* 카드 패널 */
            .card { 
                background: var(--panel); 
                border: 1px solid var(--panel-border); 
                border-radius: var(--radius-lg); 
                padding: 22px 24px; 
                margin-bottom: 24px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);
            }
            .card-header { font-size: 14px; font-weight: 700; color: #ffffff; margin-bottom: 18px; display: flex; align-items: center; justify-content: space-between; }
            
            /* 입력 필드 레이아웃 */
            .form-grid { display: grid; grid-template-columns: 140px 120px 140px 1fr 90px; gap: 10px; }
            input, select, button { 
                background: #192233; 
                border: 1px solid #2d3a4f; 
                color: var(--text-primary); 
                padding: 10px 14px; 
                border-radius: var(--radius-md); 
                font-size: 13px; 
                font-family: inherit;
                outline: none;
                transition: all 0.2s;
            }
            input:focus, select:focus { border-color: var(--accent-blue); box-shadow: 0 0 0 2px rgba(59,130,246,0.25); }
            
            .btn-submit { 
                background: var(--accent-blue); 
                border: none; 
                color: #ffffff; 
                font-weight: 700; 
                cursor: pointer; 
                transition: background 0.2s;
            }
            .btn-submit:hover { background: #2563eb; }

            /* 리스트 스타일 */
            ul { list-style: none; padding: 0; margin: 0; }
            li { 
                background: #151d2a; 
                border: 1px solid var(--panel-border); 
                border-radius: var(--radius-md); 
                padding: 14px 18px; 
                margin-bottom: 10px; 
                display: flex; 
                align-items: center; 
                justify-content: space-between; 
                transition: all 0.2s;
            }
            li:hover { background: var(--panel-hover); border-color: #2d3a4f; }
            li.done { opacity: 0.5; background: #0e131f; }
            li.done .task-title { text-decoration: line-through; color: var(--text-muted); }

            .task-left { display: flex; align-items: center; gap: 12px; flex: 1; }
            
            /* 마이크로 태그 배지 */
            .tag { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; letter-spacing: -0.2px; }
            .tag-high { background: rgba(244, 63, 94, 0.15); color: #fda4af; border: 1px solid rgba(244, 63, 94, 0.3); }
            .tag-mid { background: rgba(245, 158, 11, 0.15); color: #fde68a; border: 1px solid rgba(245, 158, 11, 0.3); }
            .tag-low { background: rgba(107, 114, 128, 0.15); color: #d1d5db; border: 1px solid rgba(107, 114, 128, 0.3); }
            .tag-cat { background: rgba(59, 130, 246, 0.15); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.3); }
            .tag-dday { background: rgba(99, 102, 241, 0.15); color: #c7d2fe; border: 1px solid rgba(99, 102, 241, 0.3); }

            .actions { display: flex; gap: 6px; }
            .btn-action { padding: 5px 10px; font-size: 12px; background: #1f2937; border: 1px solid #374151; color: var(--text-secondary); border-radius: 4px; cursor: pointer; }
            .btn-action:hover { background: #374151; color: #ffffff; }
            .btn-del:hover { background: rgba(244, 63, 94, 0.2); color: var(--accent-rose); border-color: rgba(244, 63, 94, 0.4); }

            /* AI 브리핑 스페셜 컨테이너 */
            .ai-card { background: linear-gradient(135deg, #111827 0%, #171e31 100%); border: 1px solid #26334d; }
            .btn-ai { 
                background: linear-gradient(90deg, var(--accent-indigo), var(--accent-blue)); 
                border: none; 
                color: #ffffff; 
                font-weight: 700; 
                width: 100%; 
                padding: 12px; 
                border-radius: var(--radius-md); 
                cursor: pointer; 
                font-size: 13px;
                box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
                transition: transform 0.1s, opacity 0.2s;
            }
            .btn-ai:hover { opacity: 0.95; transform: translateY(-1px); }
            
            #aiResult { 
                margin-top: 16px; 
                padding: 18px; 
                background: rgba(15, 23, 42, 0.6); 
                border: 1px solid #1e293b; 
                border-left: 3px solid var(--accent-indigo); 
                border-radius: var(--radius-md); 
                font-size: 13px; 
                color: #cbd5e1; 
                white-space: pre-line; 
                line-height: 1.7; 
            }
            
            input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent-blue); cursor: pointer; }
            /* 📱 모바일 디바이스 최적화 (768px 이하) */
            @media (max-width: 768px) {
                body {
                    padding: 10px !important;
                }
                .container {
                    padding: 8px !important;
                    width: 100% !important;
                }
                /* 그리드 및 카드 레이아웃 모바일 1열/2열 자동 세로 정렬 */
                .kpi-grid, .grid {
                    grid-template-columns: repeat(2, 1fr) !important;
                    gap: 10px !important;
                }
                .kpi-card {
                    padding: 12px !important;
                }
                .kpi-value {
                    font-size: 1.4rem !important;
                }
                .card {
                    padding: 12px !important;
                }
                /* 테이블 좌우 터치 스크롤 처리 */
                .table-responsive {
                    width: 100% !important;
                    overflow-x: auto !important;
                    -webkit-overflow-scrolling: touch;
                }
                table {
                    min-width: 550px !important;
                }
                th, td {
                    padding: 8px 10px !important;
                    font-size: 0.82rem !important;
                }
                /* 타이틀 크기 조정 */
                h1 {
                    font-size: 1.25rem !important;
                }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-title">
                <h1>Executive Task Intelligence</h1>
                <p>Enterprise Management & AI-Powered Executive Assistant System</p>
            </div>
            <div class="status-badge">
                <span class="status-dot"></span> System Live
            </div>
        </div>

        <!-- KPI 실시간 대시보드 -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">전체 등록 과제</div>
                <div class="kpi-value" id="kpiTotal">0</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">미완료 핵심 과제</div>
                <div class="kpi-value" id="kpiPending" style="color: var(--accent-amber);">0</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">프로젝트 완료율</div>
                <div class="kpi-value" id="kpiRate" style="color: var(--accent-emerald);">0%</div>
                <div class="progress-container">
                    <div id="progressBar" class="progress-bar"></div>
                </div>
            </div>
        </div>

        <!-- 일과 등록 -->
        <div class="card">
            <div class="card-header">신규 업무 일정 할당</div>
            <div class="form-grid">
                <input type="date" id="dateInput">
                <select id="catInput">
                    <option value="업무">업무</option>
                    <option value="R&D">R&D</option>
                    <option value="회의">회의</option>
                    <option value="개인">개인</option>
                </select>
                <select id="prioInput">
                    <option value="높음">우선순위: 높음</option>
                    <option value="보통" selected>우선순위: 보통</option>
                    <option value="낮음">우선순위: 낮음</option>
                </select>
                <input type="text" id="taskInput" placeholder="담당 업무 세부 내용을 입력하세요...">
                <button class="btn-submit" onclick="addTask()">등록</button>
            </div>
        </div>

        <!-- 업무 리스트 -->
        <div class="card">
            <div class="card-header">진행 중인 업무 목록</div>
            <ul id="taskList">
                <li style="color: var(--text-muted);">데이터를 불러오는 중입니다...</li>
            </ul>
        </div>

        <!-- AI 수석 비서 브리핑 -->
        <div class="card ai-card">
            <div class="card-header">Gemini Executive AI Assistant</div>
            <button class="btn-ai" onclick="getAISummary()">🤖 AI 실무 우선순위 & 리스크 브리핑 리포트 생성</button>
            <div id="aiResult">버튼을 클릭하면 Gemini AI가 미완료 업무 데이터를 바탕으로 실행 가이드라인을 생성합니다.</div>
        </div>

        <script>
            document.getElementById('dateInput').value = new Date().toISOString().substring(0, 10);
            window.onload = loadTasks;

            async function loadTasks() {
                const res = await fetch('/list');
                const data = await res.json();
                const tasks = data.일정목록 || [];
                const listEl = document.getElementById('taskList');
                listEl.innerHTML = '';

                let completedCount = 0;

                if (tasks.length === 0) {
                    listEl.innerHTML = '<li style="color: var(--text-muted); font-size:13px; justify-content:center;">등록된 업무가 없습니다.</li>';
                    updateKPI(0, 0);
                    return;
                }

                tasks.forEach(item => {
                    if (item.is_done) completedCount++;

                    let tagPrio = item.priority === '높음' ? 'tag-high' : (item.priority === '보통' ? 'tag-mid' : 'tag-low');
                    
                    const li = document.createElement('li');
                    if (item.is_done) li.classList.add('done');

                    li.innerHTML = `
                        <div class="task-left">
                            <input type="checkbox" ${item.is_done ? 'checked' : ''} onchange="toggleDone(${item.id})">
                            <span class="tag ${tagPrio}">${item.priority}</span>
                            <span class="tag tag-cat">${item.category}</span>
                            <span class="tag tag-dday">${item.d_day}</span>
                            <span class="task-title" style="font-size:13px;">[${item.date}] <strong>${item.task}</strong></span>
                        </div>
                        <div class="actions">
                            <button class="btn-action" onclick="updateTask(${item.id}, '${item.date}', '${item.task}', '${item.category}', '${item.priority}')">수정</button>
                            <button class="btn-action btn-del" onclick="deleteTask(${item.id})">삭제</button>
                        </div>
                    `;
                    listEl.appendChild(li);
                });

                updateKPI(tasks.length, completedCount);
            }

            function updateKPI(total, completed) {
                const pending = total - completed;
                const rate = total === 0 ? 0 : Math.round((completed / total) * 100);

                document.getElementById('kpiTotal').innerText = total;
                document.getElementById('kpiPending').innerText = pending;
                document.getElementById('kpiRate').innerText = rate + '%';
                document.getElementById('progressBar').style.width = rate + '%';
            }

            async function addTask() {
                const date = document.getElementById('dateInput').value;
                const task = document.getElementById('taskInput').value;
                const category = document.getElementById('catInput').value;
                const priority = document.getElementById('prioInput').value;

                if (!date || !task) { alert("날짜와 업무 내용을 입력해 주세요."); return; }

                await fetch(`/add?date=${encodeURIComponent(date)}&task=${encodeURIComponent(task)}&category=${encodeURIComponent(category)}&priority=${encodeURIComponent(priority)}`, { method: 'POST' });
                document.getElementById('taskInput').value = '';
                loadTasks();
            }

            async function toggleDone(id) {
                await fetch(`/toggle?item_id=${id}`, { method: 'PUT' });
                loadTasks();
            }

            async function updateTask(id, curDate, curTask, curCat, curPrio) {
                const newDate = prompt("수정할 날짜:", curDate); if (!newDate) return;
                const newTask = prompt("수정할 업무 내용:", curTask); if (!newTask) return;

                await fetch(`/update?item_id=${id}&date=${encodeURIComponent(newDate)}&task=${encodeURIComponent(newTask)}&category=${encodeURIComponent(curCat)}&priority=${encodeURIComponent(curPrio)}`, { method: 'PUT' });
                loadTasks();
            }

            async function deleteTask(id) {
                if (!confirm("해당 업무를 삭제하시겠습니까?")) return;
                await fetch(`/delete?item_id=${id}`, { method: 'DELETE' });
                loadTasks();
            }

            async function getAISummary() {
                document.getElementById('aiResult').innerText = "⏳ Gemini AI가 업무 데이터를 분석하여 Executive 브리핑 보고서를 생성 중입니다...";
                const res = await fetch('/summarize');
                const data = await res.json();
                document.getElementById('aiResult').innerText = data.AI브리핑결과;
            }
        </script>
    </body>
    </html>
    """


# --- 2. 백엔드 API 기능 ---


@app.post("/add")
def add_task(
    date: str, task: str, category: str = "업무", priority: str = "보통"
):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO todos (date, task, category, priority, is_done) VALUES (?, ?, ?, ?, 0)",
        (date, task, category, priority),
    )
    conn.commit()
    conn.close()
    return {"상태": "성공"}


@app.get("/list")
def get_tasks():
    return {"일정목록": get_db_tasks()}


@app.put("/toggle")
def toggle_task(item_id: int):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE todos SET is_done = CASE WHEN is_done = 1 THEN 0 ELSE 1 END WHERE id = ?",
        (item_id,),
    )
    conn.commit()
    conn.close()
    return {"상태": "성공"}


@app.put("/update")
def update_task(
    item_id: int,
    date: str,
    task: str,
    category: str = "업무",
    priority: str = "보통",
):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE todos SET date = ?, task = ?, category = ?, priority = ? WHERE id = ?",
        (date, task, category, priority, item_id),
    )
    conn.commit()
    conn.close()
    return {"상태": "성공"}


@app.delete("/delete")
def delete_task(item_id: int):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"상태": "성공"}


@app.get("/summarize")
def summarize_tasks():
    all_tasks = get_db_tasks()
    todo_tasks = [t for t in all_tasks if not t["is_done"]]

    if not todo_tasks:
        return {
            "AI브리핑결과": "🎉 [Executive Report] 현재 미완료된 업무 과제가 없습니다. 주요 리스크가 소멸되었습니다."
        }

    prompt = f"""
    당신은 대기업 수석 경영전략 컨설턴트 및 AI 수석 비서입니다.
    아래는 사용자의 [미완료 실무 업무 목록 데이터]입니다:
    {todo_tasks}

    위 데이터를 바탕으로 최고 경영진(Executive) 보고용 브리핑 리포트를 작성해 주세요:
    1. 🎯 [최우선 과제 (Top Priority Task)]: D-Day 마감 임박 및 우선순위 최상위 항목 지정
    2. 💡 [실행 로드맵 (Actionable Steps)]: 효율적 리소스 배분을 위한 2~3줄 가이드
    3. ⚠️ [마감 리스크 관리 (Deadline Risk)]: 주의가 필요한 과제 경고
    """

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-3.8-flash", contents=prompt
    )

    return {"AI브리핑결과": response.text}