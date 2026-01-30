
# Sample Auth API

모바일 앱 서비스를 위한 FastAPI 기반 JWT 인증 API

## 주요 기능

- **회원가입 / 로그인 / 로그아웃** - 이메일 기반 인증
- **Device 기반 토큰 관리** - Access Token / Refresh Token을 디바이스별로 분리 관리
- **Refresh Token Rotation (RTR)** - 갱신 시 새 RT 발급, 재사용 탐지
- **다중 디바이스 지원** - 동시 로그인, 디바이스 목록 조회, 특정 디바이스 강제 로그아웃
- **Redis 토큰 저장소** - 디바이스별 RT 저장, Access Token Blacklist
- **완전한 비동기 처리** - async/await 기반 전체 I/O

## 기술 스택

| 구분 | 기술 |
|------|------|
| Language | Python 3.12+ |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| DB | SQLite (로컬) / MySQL 8.0 (운영) |
| Cache | Redis 7 |
| JWT | PyJWT (RS256) |
| Password | passlib + bcrypt |
| Logging | structlog (JSON / Console) |
| Validation | Pydantic v2 |
| Migration | Alembic |

## 빠른 시작

### 1. 의존성 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. RSA 키 생성

```bash
python scripts/generate_keys.py
```

`keys/private.pem`, `keys/public.pem` 파일이 생성됩니다.

### 3. 환경 변수 설정

```bash
cp .env.example .env
```

로컬 개발 시 기본값(SQLite + Redis localhost)으로 바로 실행 가능합니다.

### 4. 서버 실행

```bash
uvicorn app.main:app --reload
```

- API 문서: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

### Docker로 실행 (MySQL + Redis 포함)

```bash
python scripts/generate_keys.py   # 최초 1회
docker-compose up
```

## 프로젝트 구조

```
app/
├── main.py                  # FastAPI 앱 진입점
├── core/                    # 핵심 설정
│   ├── config.py            # Pydantic Settings
│   ├── database.py          # SQLAlchemy async engine
│   ├── redis.py             # Redis async client
│   ├── security.py          # Password hashing
│   └── logging.py           # structlog 설정
├── models/                  # SQLAlchemy ORM Models
│   ├── base.py              # Timestamp, SoftDelete mixins
│   ├── user.py
│   ├── user_device.py
│   └── login_history.py
├── schemas/                 # Pydantic Schemas
│   ├── common.py            # APIResponse<T>, ErrorResponse
│   ├── auth.py
│   ├── user.py
│   └── device.py
├── repositories/            # Data Access Layer
│   ├── user.py
│   ├── user_device.py
│   └── login_history.py
├── services/                # Business Logic
│   ├── auth.py              # 인증 서비스
│   ├── jwt.py               # JWT 생성/검증
│   ├── token_store.py       # Redis 토큰 저장소
│   ├── user.py              # 사용자 서비스
│   ├── device.py            # 디바이스 서비스
│   └── auth_event_logger.py # 인증 이벤트 로깅
├── api/v1/                  # API Routers
│   ├── router.py            # v1 라우터 통합
│   ├── auth.py              # /api/v1/auth/*
│   ├── users.py             # /api/v1/users/*
│   └── devices.py           # /api/v1/users/me/devices/*
├── dependencies/            # FastAPI Dependencies
│   ├── auth.py              # JWT 인증 의존성
│   ├── database.py          # DB 세션
│   └── redis.py             # Redis 클라이언트
├── middleware/               # ASGI 미들웨어
│   ├── request_id.py        # X-Request-Id 생성
│   └── logging.py           # structlog context 바인딩
└── exceptions/              # 예외 처리
    ├── base.py              # AppException
    ├── auth.py              # AUTH_001 ~ AUTH_009
    ├── user.py              # USER_001 ~ DEVICE_003
    └── handlers.py          # 글로벌 예외 핸들러
```

## API 엔드포인트

### 인증 (Public)

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/auth/signup` | 회원가입 |
| POST | `/api/v1/auth/login` | 로그인 (토큰 발급) |
| POST | `/api/v1/auth/refresh` | 토큰 갱신 (RTR) |
| POST | `/api/v1/auth/logout` | 로그아웃 (현재 디바이스) |
| POST | `/api/v1/auth/logout/all` | 전체 디바이스 로그아웃 |

### 사용자 (Protected)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/users/me` | 내 정보 조회 |
| PATCH | `/api/v1/users/me` | 내 정보 수정 |
| PUT | `/api/v1/users/me/password` | 비밀번호 변경 |
| DELETE | `/api/v1/users/me` | 회원 탈퇴 |

### 디바이스 관리 (Protected)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/users/me/devices` | 로그인된 디바이스 목록 |
| DELETE | `/api/v1/users/me/devices/{device_id}` | 특정 디바이스 강제 로그아웃 |

## 공통 Request Headers

모든 요청에 다음 헤더가 필요합니다:

```
X-Device-Id: <UUID>          # 디바이스 고유 식별자 (필수)
X-App-Version: 1.0.0         # 앱 버전 (필수)
X-OS-Type: iOS               # OS 종류 - iOS / Android (필수)
X-OS-Version: 17.2           # OS 버전 (필수)
X-Device-Name: iPhone 15 Pro # 디바이스 이름 (로그인 시 권장)
Authorization: Bearer <token> # 인증 토큰 (Protected API)
```

## 인증 흐름

### 로그인

```
App → POST /api/v1/auth/login (email, password + Device Headers)
    ← { access_token, refresh_token, expires_in, user }
```

- Access Token (30분): API 호출 시 `Authorization: Bearer <AT>` 헤더에 포함
- Refresh Token (30일): Redis에 `auth:rt:{user_id}:{device_id}` 키로 저장
- AT에 `device_id`가 포함되어 요청 시 헤더의 `X-Device-Id`와 대조 검증

### 토큰 갱신

```
App → POST /api/v1/auth/refresh (refresh_token + X-Device-Id)
    ← { new_access_token, new_refresh_token }
```

- Refresh Token Rotation: 갱신 시 기존 RT 폐기 + 새 RT 발급
- RT 재사용 탐지: 이미 사용된 RT로 요청 시 해당 디바이스 세션 즉시 무효화

### 로그아웃

```
App → POST /api/v1/auth/logout (Authorization + X-Device-Id)
    ← AT를 blacklist에 등록, RT 삭제, 디바이스 비활성화
```

## Redis 데이터 구조

```
auth:rt:{user_id}:{device_id}   # Refresh Token (TTL: 30일)
auth:blacklist:{jti}             # AT Blacklist (TTL: AT 잔여 시간)
auth:devices:{user_id}           # 활성 디바이스 Set
```

## 에러 코드

| Code | HTTP | 메시지 |
|------|------|--------|
| AUTH_001 | 401 | 이메일 또는 비밀번호가 올바르지 않습니다 |
| AUTH_002 | 401 | 인증이 만료되었습니다 |
| AUTH_003 | 401 | 유효하지 않은 인증 정보입니다 |
| AUTH_005 | 401 | 유효하지 않은 갱신 토큰입니다 |
| AUTH_006 | 401 | 로그아웃된 세션입니다 |
| AUTH_007 | 401 | 다른 기기에서 발급된 인증 정보입니다 |
| AUTH_009 | 429 | 로그인 시도가 너무 많습니다 |
| USER_002 | 409 | 이미 사용 중인 이메일입니다 |
| USER_004 | 400 | 현재 비밀번호가 일치하지 않습니다 |
| USER_005 | 400 | 새 비밀번호는 현재 비밀번호와 달라야 합니다 |
| SYS_001 | 500 | 서버 오류가 발생했습니다 |
| SYS_004 | 422 | 입력값 검증에 실패했습니다 |

## 테스트

```bash
# 전체 테스트 실행
pytest

# 커버리지 포함
pytest --cov=app

# 특정 테스트
pytest tests/unit/ -v
pytest tests/integration/ -v
```

테스트는 SQLite + Redis mock을 사용하여 외부 의존성 없이 실행됩니다.

## 환경 설정

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./test.db` | DB 연결 URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 연결 URL |
| `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` | `1800` | AT 만료 시간 (30분) |
| `JWT_REFRESH_TOKEN_EXPIRE_SECONDS` | `2592000` | RT 만료 시간 (30일) |
| `JWT_ALGORITHM` | `RS256` | JWT 서명 알고리즘 |
| `BCRYPT_ROUNDS` | `12` | BCrypt 해싱 라운드 |
| `LOG_JSON` | `true` | JSON 로그 출력 여부 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
| `ENVIRONMENT` | `local` | 실행 환경 (local/dev/staging/prod) |

전체 설정 목록은 `.env.example`을 참고하세요.

## 로깅

structlog 기반 구조화된 로깅을 사용합니다.

**로컬 개발** (`LOG_JSON=false`): 컬러 콘솔 출력

```
2025-01-24 10:00:00 [info] Request completed  status_code=200 duration_ms=12.5 trace_id=abc-123
```

**운영 환경** (`LOG_JSON=true`): JSON 형식 (ECS 호환)

```json
{
  "@timestamp": "2025-01-24T10:00:00.000Z",
  "log.level": "info",
  "message": "LOGIN_SUCCESS",
  "user.id": "550e8400-...",
  "device.id": "device-uuid",
  "client.ip": "192.168.1.100"
}
```

모든 요청에 자동으로 `trace_id`, `device_id`, `client_ip`, `request_method`, `request_uri` 컨텍스트가 바인딩됩니다.

## 보안

- **RS256 JWT** - 비대칭 키 서명 (private key로 서명, public key로 검증)
- **Device Binding** - 토큰에 디바이스 ID 포함, 요청 시 헤더와 대조
- **Refresh Token Rotation** - 갱신마다 새 RT 발급, 기존 RT 즉시 폐기
- **Token Blacklist** - 로그아웃/비밀번호 변경 시 AT 즉시 무효화
- **BCrypt** - 비밀번호 해싱 (12 rounds)
- **Password Policy** - 8자 이상, 영문 + 숫자 + 특수문자 조합
- **Soft Delete** - 회원 탈퇴 시 데이터 보존 (deleted_at 마킹)
