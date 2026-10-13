# AI EduBank

학습자의 **문항 풀이 결과와 소요 시간**을 기록하고, 추천 문항·복습 문항·학습 리포트를 제공하는 교육용 웹 애플리케이션입니다. 교수자는 단원별 정답률과 지연 오답 기록을 확인해 보충 지도가 필요한 학생을 살펴볼 수 있습니다.

> **시작 안내:** Python과 Supabase 프로젝트를 준비한 뒤 [로컬 실행](#로컬-실행)을 따라가세요. 추천·분석은 현재 코드에 구현된 계산을 사용하며, 학습 효과나 합격 가능성을 검증한 모델을 뜻하지 않습니다.

## 주요 기능

| 기능 | 현재 구현 |
| --- | --- |
| 학생 선택 | 학생 번호를 브라우저 `localStorage`에 저장하고 대시보드로 이동 |
| 학습 대시보드 | 풀이 기록 수·정답률·평균 소요 시간, 저장된 수준·능력치·학습 성향 표시 |
| 문제은행·문제 풀이 | 전체 문항 조회, 정답 비교, 소요 시간과 응답 패턴 기록 |
| 맞춤 추천 | 풀이 패턴의 코사인 유사도와 필수 문항 가중치로 미풀이 문항 최대 3개 추천 |
| 복습 추천 | 지연 오답으로 기록된 문항 최대 3개 조회 |
| 교수자 대시보드 | 학급 통계·단원별 정답률·지연 오답 3회 이상인 학생 조회 |
| 학생 상세·리포트 | 취약 단원, 규칙 기반 지도 코멘트, 정답률·풀이 시간·예시 성장 추세 시각화 |

**학습 흐름:** 학생 선택 → 문제 풀이 → 로그 저장 → 통계·추천 갱신 → 결과 확인·교수자 지도.

### 풀이 패턴

`quiz.html`은 **10초 이하**를 빠른 응답으로 구분합니다. 이 기준은 수업용 고정값입니다.

| 패턴 | 정오답 | 소요 시간 |
| --- | --- | --- |
| 1 | 정답 | 10초 이하 |
| 2 | 정답 | 10초 초과 |
| 3 | 오답 | 10초 이하 |
| 4 | 오답 | 10초 초과 |

현재 정답은 입력값의 앞뒤 공백을 제거한 뒤 문항의 `answer`와 **문자열로 정확히 비교**합니다. 같은 문항을 다시 풀면 로그가 추가되며, 대시보드의 풀이 수는 고유 문항 수가 아니라 기록 수입니다.

## 기술과 파일 구성

- **서버:** FastAPI, Uvicorn, Pydantic
- **저장:** Supabase 클라이언트와 PostgreSQL 테이블
- **분석:** Pandas, NumPy, scikit-learn
- **화면:** HTML·JavaScript, Tailwind CSS·Lucide·Chart.js CDN

| 파일 | 역할 |
| --- | --- |
| [main.py](main.py) | HTML 제공, API, Supabase 조회·등록, 통계·추천·리포트 계산 |
| [login.html](login.html) | 학생 번호 입력 |
| [index.html](index.html) | 학생 대시보드·추천 문항 |
| [quiz.html](quiz.html) | 문항 조회·시간 측정·정답 비교·제출 |
| [bank.html](bank.html) | 전체 문항 목록 |
| [teacher.html](teacher.html) | 학급 통계·단원별 차트·지도 대상 |
| [student_detail.html](student_detail.html) | 교수자용 학생 상세 분석 |
| [report.html](report.html) | 학생 개인 리포트 |
| [requirements.txt](requirements.txt) | Python 의존성 목록 |
| [vercel.json](vercel.json) | Vercel Python 빌드·라우팅 설정 |

화면은 FastAPI 서버를 통해 여세요. HTML 파일을 직접 열거나 Live Server만 실행하면 `/api` 요청을 처리할 서버가 연결되지 않습니다.

## 로컬 실행

### 1. 설치

Python 실행 환경과 Git을 준비합니다. 저장소는 Python·패키지 버전을 고정하지 않으므로 사용할 환경에서 설치와 실행을 확인하세요.

**Windows PowerShell**

```powershell
git clone https://github.com/ejkim9090/ai-edubank.git
cd ai-edubank

py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux**

```bash
git clone https://github.com/ejkim9090/ai-edubank.git
cd ai-edubank

python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

### 2. Supabase와 환경변수

Supabase 프로젝트에 아래 [데이터 구조](#데이터-구조)의 테이블과 실습 데이터를 준비합니다. 저장소 루트에 `.env`를 직접 만드세요.

```dotenv
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=YOUR_SERVER_SIDE_KEY
```

- 환경변수 이름은 위 두 개와 정확히 일치해야 합니다.
- 서버에 사용할 키에는 테이블 조회와 `logs` 등록 권한이 필요합니다. 키 종류와 RLS 정책을 확인하세요.
- `secret`·`service_role`처럼 권한이 높은 키는 서버 환경변수에만 보관합니다. HTML·GitHub·화면 캡처에 넣지 않습니다.
- `main.py`는 import 시 Supabase 클라이언트를 생성하므로 접속값이 없으면 서버 시작부터 실패할 수 있습니다.
- `.env`는 현재 `.gitignore`에 포함되어 있습니다.

### 3. 서버 시작

```powershell
# Windows PowerShell
.\venv\Scripts\python.exe -m uvicorn main:app --reload
```

```bash
# macOS / Linux
venv/bin/python -m uvicorn main:app --reload
```

- 학생 시작: [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
- 문제은행: [http://127.0.0.1:8000/bank](http://127.0.0.1:8000/bank)
- 교수자: [http://127.0.0.1:8000/teacher](http://127.0.0.1:8000/teacher)
- API 문서: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

`users`에 실제 존재하는 학생 번호를 입력합니다. 번호 입력은 현재 데모용 학생 선택이며 비밀번호 인증이 아닙니다.

## 데이터 구조

코드가 사용하는 테이블은 `users`, `questions`, `logs`입니다. **DDL·초기 데이터·RLS 정책 파일은 저장소에 포함되어 있지 않습니다.** 기존 DB를 연결한다면 다음 필드와 자료형을 먼저 대조하세요.

| 테이블 | 코드에서 사용하는 필드 |
| --- | --- |
| `users` | `user_id`, `name`, `level`, `theta`, `ai_literacy_level`, `learning_tendency` |
| `questions` | `question_id`, `topic`, `content`, `answer`, `difficulty`, `is_essential`, `essential_weight` |
| `logs` | `log_id`, `user_id`, `question_id`, `is_correct`, `time_spent`, `pattern_class` |

학생 ID는 정수, 문항 ID와 정답은 문자열, 정오답은 Boolean, 소요 시간은 초 단위 정수로 준비합니다. `log_id`는 서버가 직접 보내지 않으므로 DB에서 자동 생성해야 합니다.

<details>
<summary>새 실습 프로젝트용 최소 SQL 예시</summary>

아래는 **코드에서 사용하는 필드를 바탕으로 작성한 준비 예시**입니다. 실제 운영 DB의 스키마나 마이그레이션을 확인한 결과는 아닙니다. 새 실습 프로젝트의 Supabase SQL Editor에서 사용하고, 기존 테이블이 있으면 타입·제약조건을 먼저 확인하세요. `CREATE TABLE IF NOT EXISTS`는 기존 구조를 변경하지 않습니다.

```sql
CREATE TABLE IF NOT EXISTS public.users (
    user_id integer PRIMARY KEY,
    name text NOT NULL,
    level integer NOT NULL DEFAULT 1,
    theta double precision NOT NULL DEFAULT 0,
    ai_literacy_level integer NOT NULL DEFAULT 1,
    learning_tendency text NOT NULL DEFAULT '자율형'
);

CREATE TABLE IF NOT EXISTS public.questions (
    question_id text PRIMARY KEY,
    topic text NOT NULL,
    content text NOT NULL,
    answer text NOT NULL,
    difficulty double precision NOT NULL DEFAULT 0,
    is_essential boolean NOT NULL DEFAULT false,
    essential_weight double precision NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS public.logs (
    log_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id integer NOT NULL REFERENCES public.users(user_id),
    question_id text NOT NULL REFERENCES public.questions(question_id),
    is_correct boolean NOT NULL,
    time_spent integer NOT NULL CHECK (time_spent >= 0),
    pattern_class integer NOT NULL CHECK (pattern_class BETWEEN 1 AND 4)
);

-- 브라우저 직접 접근을 허용하는 정책은 이 예시에 포함하지 않습니다.
-- 서버에서 쓰는 키와 테이블 권한에 맞게 접근을 구성하세요.
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.logs ENABLE ROW LEVEL SECURITY;

-- 아래 학생·문항은 실습용 예시이며, 기존 ID의 행을 덮어쓰지 않습니다.
INSERT INTO public.users (user_id, name)
VALUES (1, '실습 학생 A'), (2, '실습 학생 B')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO public.questions
    (question_id, topic, content, answer, difficulty, is_essential, essential_weight)
VALUES
    ('Q001', '기초 연산', '2 + 3의 결과는?', '5', 0, false, 1),
    ('Q002', '파이썬 연산', '10 // 3의 결과는?', '3', 0, false, 1),
    ('Q003', '리스트', 'len([1, 2, 3])의 결과는?', '3', 0, true, 2)
ON CONFLICT (question_id) DO NOTHING;
```

최초에는 풀이 로그가 없어 일부 통계·리포트를 사용할 수 없습니다. 문제를 풀어 `logs`를 만든 뒤 확인하세요. 학생·문항 ID가 기존 데이터와 겹치면 예시 데이터를 별도 프로젝트에 준비합니다.

</details>

## API와 실행 확인

| 메서드 | 경로 | 역할 |
| --- | --- | --- |
| GET | `/api/dashboard/{user_id}` | 학생 기본 통계 |
| GET | `/api/recommend/{user_id}` | 새 문항·복습 문항 추천 |
| GET | `/api/questions` | 전체 문항 |
| GET | `/api/question/{q_id}` | 문항 1개 |
| POST | `/api/submit` | 풀이 로그 등록 |
| GET | `/api/teacher/stats` | 학급 통계·지도 대상 |
| GET | `/api/teacher/student/{user_id}` | 학생 상세·취약 단원 |
| GET | `/api/report/{user_id}` | 개인 리포트 |

제출 데이터의 구조는 다음과 같습니다. 실제 제출 시 등록된 학생·문항 ID를 사용합니다.

```json
{
  "user_id": 1,
  "question_id": "Q001",
  "is_correct": true,
  "time_spent": 8,
  "pattern_class": 1
}
```

**⭐ 처음 확인할 순서**

1. `/docs`에서 `GET /api/questions`가 준비한 문항을 반환하는지 확인합니다.
2. `/login`에서 학생을 선택하고 `/bank`에서 문항을 엽니다.
3. 정답·오답을 제출하고 Supabase `logs`에 실제 행이 추가됐는지 확인합니다.
4. 대시보드의 기록 수·정답률·평균 시간을 DB 값과 대조합니다.
5. 두 학생이 일부 같은 문항을 풀게 한 뒤 추천 결과를 확인합니다. 데이터가 없으면 신규 학습자 안내나 빈 추천이 반환될 수 있습니다.
6. 같은 문항에 10초 초과 오답을 3번 기록해 교수자 지도 대상 조건을 확인합니다.

현재 화면은 DB 저장이 끝나기 전에 결과 메시지를 표시하고, HTTP 오류 여부도 충분히 검사하지 않습니다. **‘기록 완료’ 표시만으로 저장 성공을 판단하지 말고 DB 행과 응답을 확인하세요.** 존재하지 않는 ID를 조회하는 일부 API도 HTTP 404 대신 `error`·`message` JSON을 반환합니다.

## 추천·분석을 읽는 기준

| 항목 | 실제 계산과 해석 |
| --- | --- |
| 협업 필터링 | 정답 +1·오답 −1·미풀이 0의 사용자–문항 행렬에서 코사인 유사도 계산. 반복 풀이는 문항별 평균으로 집계 |
| 새 문항 점수 | 해당 문항을 맞힌 유사 이웃 수 × 양의 유사도를 가진 전체 이웃의 평균 유사도. 필수 문항이면 가중치 적용 |
| 필수 문항 | 점수가 0이어도 후보에 포함. 점수순 정렬이므로 필수 문항을 항상 최상단에 보장하지는 않음 |
| 복습 문항 | 과거 패턴 4가 한 번이라도 있는 문항. 이후 정답을 맞혔는지는 복습 제외 조건에 반영하지 않음 |
| 지도 코멘트 | 지연 오답이 많은 단원에 따라 문장을 조합하는 규칙 기반 코멘트 |
| `theta`·수준·학습 성향 | DB에 저장된 값을 조회. 풀이 제출 시 재추정·갱신하는 코드는 없음 |
| 성장 추세 | 풀이 순서를 5개 구간으로 나누고 정답 비율을 누적한 예시 값에 선형 회귀 적용. 실제 회차별 IRT 추정값이 아님 |
| 목표 도달 지표 | 정답률과 저장된 `theta`를 고정식의 시그모이드에 입력. 데이터로 학습·보정한 로지스틱 회귀나 검증된 합격 확률이 아님 |
| 산점도 | 정오답 위치에 표시용 난수 jitter를 추가하므로 다시 조회하면 점 위치가 조금 달라질 수 있음 |

OpenAI·LLM 호출, 문항 자동 생성, IRT 모형 학습은 현재 구현되어 있지 않습니다. 화면의 ‘AI’·‘능력치’·‘확률’ 표현은 위 구현 범위 안에서 해석하세요.

## 배포와 현재 한계

[Vercel 설정](vercel.json)은 모든 경로를 `main.py`로 전달하도록 구성되어 있습니다. 배포 환경에도 `SUPABASE_URL`·`SUPABASE_KEY`를 설정하고 HTML 파일 포함 여부와 실제 API 동작을 확인하세요. 설정 파일이 있다는 사실만으로 배포 성공을 보장하지 않습니다.

현재 버전은 **가상 데이터로 학습 흐름을 확인하는 프로토타입**에 적합합니다.

- 학생 번호 선택과 교수자 경로에 서버 인증·역할별 접근 제어가 없습니다.
- 정답이 브라우저로 전달되고 정오답·소요 시간·패턴을 클라이언트가 보내며, 서버는 이를 다시 채점·검증하지 않습니다.
- 빈 데이터·누락된 필드·DB 오류 처리와 전체 로그 조회의 페이지 처리가 충분하지 않습니다.
- 자동 테스트, 의존성 버전 고정, DB 스키마·초기 데이터 파일은 포함되어 있지 않습니다.

실제 학생 데이터를 연결하는 운영 단계에서는 인증·권한, 서버 채점, 입력 검증, 데이터 조회 범위와 예외 처리를 먼저 보완해야 합니다.

## 참고 문서

- [FastAPI 시작하기](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [Supabase Python 클라이언트 초기화](https://supabase.com/docs/reference/python/initializing)
- [Supabase API 키와 접근 권한](https://supabase.com/docs/guides/getting-started/api-keys)
- [Vercel Python Runtime](https://vercel.com/docs/functions/runtimes/python)

이 README는 저장소의 코드·HTML·설정 파일을 검토해 작성했습니다. 실제 Supabase 프로젝트·브라우저 화면·Vercel 배포 결과는 이 문서 작성 과정에서 확인하지 않았습니다.
