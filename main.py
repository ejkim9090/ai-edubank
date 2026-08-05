from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse # HTML 파일을 보내기 위해 추가!
from pydantic import BaseModel # 👈 이거 한 줄 추가! (데이터를 받을 때 쓰는 도구입니다)
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import math
from sklearn.linear_model import LinearRegression

# import os # 파일 경로 확인을 위해 추가
# 👇 Supabase 라이브러리 추가
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 🌟 .env 파일에서 환경 변수 불러오기 (로컬 테스트용)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 수파베이스 클라이언트 초기화
# ==========================================
# ☁️ Supabase 클라우드 DB 연결 설정 (여기를 수정하세요!)
# ==========================================
# SUPABASE_URL = "https://본인의_프로젝트주소.supabase.co"
# SUPABASE_KEY = "본인의_anon_public_API_KEY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# ==========================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/api/dashboard/{user_id}")
def get_user_dashboard(user_id: int):
    user_res = supabase.table("users").select("*").eq("user_id", user_id).execute()
    logs_res = supabase.table("logs").select("*").eq("user_id", user_id).execute()
    
    if not user_res.data:
        return {"error": "존재하지 않는 학생입니다."}
        
    user = user_res.data[0]
    logs_df = pd.DataFrame(logs_res.data) if logs_res.data else pd.DataFrame()
    
    solved_count = len(logs_df)
    correct_rate = int((len(logs_df[logs_df['is_correct'] == True]) / solved_count) * 100) if solved_count > 0 else 0
    avg_time_sec = int(logs_df['time_spent'].mean()) if solved_count > 0 else 0
    
    # AI 문해력 수준 텍스트 변환
    literacy_map = {1: "초보형 🐣", 2: "활용형 🚀", 3: "자립형 👑"}
    ai_literacy = literacy_map.get(user.get("ai_literacy_level", 1), "초보형 🐣")
    
    return {
        "name": user['name'],
        "solved_count": solved_count,
        "correct_rate": correct_rate,
        "avg_time_sec": avg_time_sec,
        "level": user.get('level', 1),
        "theta": user.get('theta', 0.0),
        "ai_literacy": ai_literacy,
        "learning_tendency": user.get('learning_tendency', '자율형')
    }

# ==========================================
# 🤖 [AI 맞춤형 하이브리드 추천 API]
# ==========================================
@app.get("/api/recommend/{user_id}")
def get_recommendation(user_id: int):
    logs_res = supabase.table("logs").select("*").execute()
    questions_res = supabase.table("questions").select("*").execute()
    
    logs_df = pd.DataFrame(logs_res.data) if logs_res.data else pd.DataFrame()
    questions_df = pd.DataFrame(questions_res.data) if questions_res.data else pd.DataFrame()
    
    if logs_df.empty or questions_df.empty:
        return {"message": "학습 데이터가 부족합니다."}
        
    # 1. 사용자-문항 행렬 및 코사인 유사도 계산
    logs_df['score'] = logs_df['is_correct'].apply(lambda x: 1 if x else -1)
    user_item_matrix = logs_df.pivot_table(index='user_id', columns='question_id', values='score').fillna(0)
    
    if user_id not in user_item_matrix.index:
        return {"message": "새로운 학습자입니다. 진단 평가를 먼저 진행해주세요."}
        
    similarity_matrix = cosine_similarity(user_item_matrix)
    similarity_df = pd.DataFrame(similarity_matrix, index=user_item_matrix.index, columns=user_item_matrix.index)
    
    # 나와 유사도가 높은 이웃 추출 (본인 제외, 유사도 0 이상)
    my_similarities = similarity_df[user_id]
    similar_peers = my_similarities[(my_similarities.index != user_id) & (my_similarities > 0)]
    
    # 2. 새로운 문제 추천 (협업필터링 + 필수문항 가중치)
    my_solved = logs_df[logs_df['user_id'] == user_id]['question_id'].tolist()
    recommend_candidates = []
    
    for _, q_row in questions_df.iterrows():
        q_id = q_row['question_id']
        if q_id in my_solved:
            continue
            
        # 이 문제를 맞힌 유사 이웃 학생 수 계산
        peer_correct_logs = logs_df[(logs_df['user_id'].isin(similar_peers.index)) & 
                                    (logs_df['question_id'] == q_id) & 
                                    (logs_df['is_correct'] == True)]
        peer_count = len(peer_correct_logs['user_id'].unique())
        
        # [핵심 로직] 기본 점수 = 이웃 수 * 평균 유사도
        base_score = peer_count * (similar_peers.mean() if not similar_peers.empty else 1.0)
        
        # 🌟 필수 문항 가중치 적용!
        final_score = base_score * q_row['essential_weight'] if q_row['is_essential'] else base_score
        
        # 점수가 있거나 필수문항인 경우 후보에 추가
        if final_score > 0 or q_row['is_essential']:
            recommend_candidates.append({
                "question_id": q_id,
                "topic": q_row['topic'],
                "content": q_row['content'],
                "is_essential": q_row['is_essential'],
                "peer_count": peer_count,
                "final_score": round(final_score, 2)
            })
            
    # 최종 점수 순으로 내림차순 정렬
    recommend_candidates.sort(key=lambda x: x['final_score'], reverse=True)
    
    # 3. 복습 문제 추천 (패턴 4: 시간지연 오답 추출)
    delayed_wrong_logs = logs_df[(logs_df['user_id'] == user_id) & (logs_df['pattern_class'] == 4)]
    review_q_ids = delayed_wrong_logs['question_id'].unique().tolist()
    reviews = questions_df[questions_df['question_id'].isin(review_q_ids)].to_dict('records')
    
    return {
        "target_user": user_id,
        "recommended_questions": recommend_candidates[:3], # 상위 3개 추천
        "review_questions": reviews[:3]
    }

# HTML 화면 연결 라우터들
@app.get("/")
def read_root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

@app.get("/quiz")
def read_quiz():
    return FileResponse(os.path.join(os.path.dirname(__file__), "quiz.html"))

@app.get("/bank")
def read_bank():
    return FileResponse(os.path.join(os.path.dirname(__file__), "bank.html"))

@app.get("/api/questions")
def get_all_questions():
    questions_res = supabase.table("questions").select("*").execute()
    return questions_res.data

@app.get("/api/question/{q_id}")
def get_question(q_id: str):
    q_res = supabase.table("questions").select("*").eq("question_id", q_id).execute()
    if not q_res.data:
        return {"error": "문제를 찾을 수 없습니다."}
    return q_res.data[0]

# 데이터베이스 쓰기 (Insert) API
class SubmitData(BaseModel):
    user_id: int
    question_id: str
    is_correct: bool
    time_spent: int
    pattern_class: int

@app.post("/api/submit")
def submit_answer(data: SubmitData):
    # # 1. 현재 클라우드 DB에 로그가 몇 개 있는지 확인하여 새 번호(log_id) 생성
    # logs_res = supabase.table("logs").select("log_id").execute()
    # new_log_id = len(logs_res.data) + 1 if logs_res.data else 1
    
    # 2. 새 log_id를 포함하여 데이터 저장!
    response = supabase.table("logs").insert({
        # "log_id": new_log_id,         # 👈 직접 만든 log_id 추가!
        "user_id": data.user_id,
        "question_id": data.question_id,
        "is_correct": data.is_correct,
        "time_spent": data.time_spent,
        "pattern_class": data.pattern_class
    }).execute()
        
    return {"message": "클라우드 DB에 성공적으로 저장되었습니다!"}

# HTML 화면 연결 라우터들
@app.get("/login")
def read_login():
    return FileResponse(os.path.join(os.path.dirname(__file__), "login.html"))

# ==========================================
# 👨‍🏫 [교수자용 환류 대시보드 API]
# ==========================================
@app.get("/teacher")
def read_teacher():
    return FileResponse(os.path.join(os.path.dirname(__file__), "teacher.html"))

# ==========================================
# 👨‍🏫 [교수자용 환류 대시보드 API - 빅데이터 고도화 버전]
# ==========================================
@app.get("/api/teacher/stats")
def get_teacher_stats():
    logs_res = supabase.table("logs").select("*").execute()
    users_res = supabase.table("users").select("*").execute()
    questions_res = supabase.table("questions").select("*").execute()

    logs_df = pd.DataFrame(logs_res.data) if logs_res.data else pd.DataFrame()
    users_df = pd.DataFrame(users_res.data) if users_res.data else pd.DataFrame()
    questions_df = pd.DataFrame(questions_res.data) if questions_res.data else pd.DataFrame()

    if logs_df.empty or users_df.empty:
        return {"error": "데이터가 부족합니다."}

    # 1. 기본 통계
    total_students = len(users_df)
    total_solved = len(logs_df)
    correct_rate = int((len(logs_df[logs_df['is_correct'] == True]) / total_solved) * 100)
    
    # 2. 클래스 평균 능력치 (IRT Theta)
    avg_theta = round(users_df['theta'].mean(), 2)

    # 3. 단원별 정답률 분석 (시각화 차트용 데이터)
    # 로그와 문제 데이터를 합쳐서 단원(topic)별 정답률 계산
    merged_df = pd.merge(logs_df, questions_df, on='question_id')
    topic_stats = merged_df.groupby('topic')['is_correct'].mean().reset_index()
    topic_stats['is_correct'] = (topic_stats['is_correct'] * 100).astype(int)
    
    chart_labels = topic_stats['topic'].tolist()
    chart_data = topic_stats['is_correct'].tolist()

    # 4. 공통 취약 단원 (정답률이 가장 낮은 단원)
    weak_concept = "데이터 부족"
    if not topic_stats.empty:
        weakest_row = topic_stats.loc[topic_stats['is_correct'].idxmin()]
        weak_concept = f"{weakest_row['topic']} (정답률 {weakest_row['is_correct']}%)"

    # 5. 즉각 개입 필요 학생 (패턴 4: 시간 지연 오답이 3회 이상인 학생들)
    pattern4_logs = logs_df[logs_df['pattern_class'] == 4]
    p4_counts = pattern4_logs['user_id'].value_counts()
    critical_users = p4_counts[p4_counts >= 3].index.tolist() # 3번 이상 지연 오답을 낸 심각한 학생
    
    needs_help_students = users_df[users_df['user_id'].isin(critical_users)][['user_id', 'name', 'theta']].to_dict('records')
    return {
        "total_students": total_students,
        "total_solved": total_solved,
        "correct_rate": correct_rate,
        "avg_theta": avg_theta,
        "weak_concept": weak_concept,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "needs_help_students": needs_help_students
    }

# ==========================================
# 🔍 [교수자용: 특정 학생 정밀 진단 리포트 API]
# ==========================================
@app.get("/student_detail")
def read_student_detail():
    return FileResponse(os.path.join(os.path.dirname(__file__), "student_detail.html"))

@app.get("/api/teacher/student/{user_id}")
def get_student_analysis(user_id: int):
    # 1. 학생 기본 정보 가져오기
    user_res = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if not user_res.data:
        return {"error": "학생 정보를 찾을 수 없습니다."}
    user_info = user_res.data[0]

    # 2. 학생의 전체 풀이 로그 및 문제 정보 가져오기
    logs_res = supabase.table("logs").select("*").eq("user_id", user_id).execute()
    questions_res = supabase.table("questions").select("*").execute()
    
    logs_df = pd.DataFrame(logs_res.data) if logs_res.data else pd.DataFrame()
    questions_df = pd.DataFrame(questions_res.data) if questions_res.data else pd.DataFrame()

    if logs_df.empty:
        return {"user": user_info, "message": "아직 푼 문제가 없습니다."}

    # 3. 시간 지연 오답(패턴 4) 데이터 추출
    merged_df = pd.merge(logs_df, questions_df, on='question_id')
    pattern4_df = merged_df[merged_df['pattern_class'] == 4]
    
    # 4. 가장 취약한 단원 분석
    weak_topics = pattern4_df['topic'].value_counts().to_dict() if not pattern4_df.empty else {}
    primary_weak_topic = list(weak_topics.keys())[0] if weak_topics else "없음"

    # 5. AI 진단 코멘트 자동 생성
    if primary_weak_topic != "없음":
        ai_comment = f"현재 {user_info['name']} 학생은 '{primary_weak_topic}' 단원에서 심각한 병목 현상(시간 지연 및 오답 반복)을 겪고 있습니다. 기초 개념 복습 및 {user_info['learning_tendency']}에 맞춘 1:1 지도가 필요합니다."
    else:
        ai_comment = f"{user_info['name']} 학생은 현재 큰 학습 결손 없이 잘 따라오고 있습니다."

    # 6. 구체적으로 틀린 문제 목록 정리
    trouble_questions = pattern4_df[['question_id', 'topic', 'content', 'time_spent']].to_dict('records')

    return {
        "user": user_info,
        "ai_comment": ai_comment,
        "weak_topics": weak_topics,
        "trouble_questions": trouble_questions
    }

# ==========================================
# 📈 [학생용: 나의 AI 정밀 진단 리포트 API (5대 분석)]
# ==========================================
@app.get("/my_report")
def get_my_report_page():
    return FileResponse(os.path.join(os.path.dirname(__file__), "report.html"))

@app.get("/api/report/{user_id}")
def get_student_report(user_id: int):
    logs_res = supabase.table("logs").select("*").execute()
    questions_res = supabase.table("questions").select("*").execute()
    users_res = supabase.table("users").select("*").execute()

    logs_df = pd.DataFrame(logs_res.data)
    questions_df = pd.DataFrame(questions_res.data)
    users_df = pd.DataFrame(users_res.data)

    user_logs = logs_df[logs_df['user_id'] == user_id]
    if user_logs.empty:
        return {"error": "데이터가 부족합니다."}

    merged_df = pd.merge(logs_df, questions_df, on='question_id')
    user_merged = merged_df[merged_df['user_id'] == user_id]
    current_user = users_df[users_df['user_id'] == user_id].iloc[0]

    # 📊 1. 방사형 차트 (영역별 성취도)
    topic_class_avg = merged_df.groupby('topic')['is_correct'].mean() * 100
    topic_user_avg = user_merged.groupby('topic')['is_correct'].mean() * 100
    
    topics = questions_df['topic'].unique().tolist()
    radar_class = [round(topic_class_avg.get(t, 0), 1) for t in topics]
    radar_user = [round(topic_user_avg.get(t, 0), 1) for t in topics]

    # 🎯 2. 산점도 (학습 행동 패턴)
    scatter_data = []
    for _, row in user_merged.iterrows():
        # 정답=1, 오답=0. 산점도 분산을 위해 약간의 노이즈(jitter) 추가
        y_val = 1 if row['is_correct'] else 0
        y_jitter = y_val + np.random.uniform(-0.1, 0.1)
        scatter_data.append({"x": row['time_spent'], "y": y_jitter, "topic": row['topic']})

    # 📈 3. 선형 회귀 (IRT 능력치 성장 추세) - 리스트 기반 안전한 분할 처리
    sorted_logs = user_logs.sort_values('log_id')
    is_correct_list = sorted_logs['is_correct'].tolist()
    # 리스트를 5개 조각으로 균등하게 쪼갬
    chunks = np.array_split(is_correct_list, 5)
    
    trend_x = np.array([1, 2, 3, 4, 5]).reshape(-1, 1)
    trend_y = []
    base_theta = float(current_user.get('theta', 0.0)) - 0.8
    
    for chunk in chunks:
        if len(chunk) > 0:
            # 불리언(True/False) 리스트의 평균값(True의 비율)을 바로 계산
            correct_mean = float(np.mean(chunk))
            base_theta += (correct_mean * 0.2)
        trend_y.append(base_theta)
    
    lr = LinearRegression()
    lr.fit(trend_x, trend_y)
    trend_line = lr.predict(trend_x)
    next_pred = lr.predict(np.array([[6]]))[0]

    # 🤝 4. 협업필터링 (도플갱어 그룹 분석)
    logs_df['score'] = logs_df['is_correct'].apply(lambda x: 1 if x else -1)
    matrix = logs_df.pivot_table(index='user_id', columns='question_id', values='score').fillna(0)
    sim = pd.DataFrame(cosine_similarity(matrix), index=matrix.index, columns=matrix.index)
    
    if user_id in sim.index:
        peers = sim[user_id].drop(user_id).nlargest(5).index
        peer_logs = merged_df[(merged_df['user_id'].isin(peers)) & (merged_df['is_correct'] == False)]
        peer_weak_topic = peer_logs['topic'].value_counts().idxmax() if not peer_logs.empty else "없음"
    else:
        peer_weak_topic = "데이터 부족"

    # 🏁 5. 로지스틱 회귀 (목표 도달 확률)
    # S자 시그모이드 함수를 사용하여 합격 확률 예측 (정답률과 theta 조합)
    user_cr = user_logs['is_correct'].mean()
    z_score = 6 * (user_cr - 0.5) + float(current_user['theta'])
    pass_prob = 1 / (1 + math.exp(-z_score))
    pass_prob_percent = int(pass_prob * 100)

    return {
        "name": current_user['name'],
        "radar": {"labels": topics, "user": radar_user, "class": radar_class},
        "scatter": scatter_data,
        "line": {
            "x": [1, 2, 3, 4, 5],
            "y": [round(v, 2) for v in trend_y],
            "trend": [round(v, 2) for v in trend_line],
            "pred": round(next_pred, 2)
        },
        "cf_insight": peer_weak_topic,
        "logistic_prob": pass_prob_percent
    }
