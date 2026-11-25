# 구현 계획: URL 단축기

## 목표와 공통 규칙

SPEC.md 1~7절을 기준으로 URL 단축기를 단계별 구현한다. 각 기능은 테스트를 먼저 작성하고, 명세된 경계 사례와 완료 기준을 통과하도록 구현한다. 이미 완료된 `src/base62.py`와 `tests/test_base62.py`는 유지한다.

- Python 표준 라이브러리만 사용한다. 외부 의존성을 추가하지 않는다.
- 애플리케이션, 테스트, 실험 코드 어디에서도 내장 `dict`, `set`, `hash()`를 사용하지 않는다. 저장소별 키-값 매핑은 직접 구현하는 체이닝 해시 테이블을 사용하고, 보조 데이터는 리스트와 튜플 등으로 관리한다.
- 기존 `Makefile`의 `make test`, `make serve`, `make experiment` 명령을 사용한다.
- 실험 CSV는 표준 라이브러리 `csv` 모듈로, 그래프 SVG는 표준 라이브러리만으로 생성한다. 그래프·표 생성용 외부 라이브러리는 추가하지 않는다.
- 진행 중 명세의 모호함이나 충돌을 발견하면 코드를 임의로 맞추지 말고 SPEC.md를 먼저 검토한다.

## 프로젝트 파일 구조와 역할

### 현재 파일

| 경로 | 역할 |
| --- | --- |
| `README.md` | 과제 목적, 개발 환경, 실행 명령 안내 |
| `SPEC.md` | 구현 요구사항과 경계 사례의 기준 |
| `PLAN.md` | 이 문서. 구현 순서, API, 테스트 및 검증 계획 |
| `Makefile` | `make test`, `make serve`, `make experiment`, `make clean` 진입점 |
| `src/base62.py` | 완료된 `encode(n)`·`decode(s)` 변환 함수 |
| `tests/test_base62.py` | 완료된 Base62 정상값, 경계값, 예외, 왕복 테스트 |
| `src/`, `tests/`, `experiments/`의 `.gitkeep` | 아직 내용이 없는 폴더를 저장소에 유지하는 자리표시자 |
| `tools/catchup.sh` | 샘플 단계 상태를 가져오는 수업 보조 스크립트 |
| `Dockerfile`, `compose.yml` | 표준 Python 및 개발 도구가 있는 실습 컨테이너 구성 |
| `.devcontainer/devcontainer.json` | Codespaces·VS Code 개발 컨테이너 설정과 8000 포트 전달 |
| `.vscode/settings.json`, `tasks.json`, `extensions.json` | 편집기 Python 분석, 테스트 및 명령 설정 |
| `.gitignore` | Python 캐시와 빌드 산출물 제외 규칙 |

### 추가할 파일

| 경로 | 역할 |
| --- | --- |
| `src/hash_table.py` | 연결 리스트 노드와 개별 체이닝 해시 테이블 |
| `src/shortener.py` | URL 검증, 순번 발급, Base62 코드 및 양방향 URL 매핑 |
| `src/server.py` | 브라우저 화면, 단축 URL 리다이렉트, `/table` 화면을 제공하는 HTTP 서버 |
| `tests/test_hash_table.py` | 해시, 충돌, 체인, 탐색 비용, 확장 및 재해시 검증 |
| `tests/test_shortener.py` | URL 검증, 중복 URL, 순번·코드 및 양방향 조회 검증 |
| `tests/test_server.py` | HTTP 상태 코드, HTML, 폼, 리다이렉트 및 테이블 화면 검증 |
| `experiments/probe_experiment.py` | 적재율별 성공·실패 탐색 비용 측정과 이론값 비교 |
| `tests/test_probe_experiment.py` | 실험 범위, 측정값 집계 및 이론 기준값 검증 |
| `experiments/results.csv` | 실험 설정과 적재율별 성공·실패 실측·이론 비용을 저장하는 생성 결과 |
| `experiments/probe_costs.svg` | 적재율별 성공·실패 실측값과 이론값을 비교하는 생성 그래프 |

## 구현 API 초안

### 기존 Base62 모듈 — 수정하지 않음

`src/base62.py`의 현재 인터페이스와 예외 동작을 그대로 사용한다.

| 함수 | 입력 | 반환 및 오류 |
| --- | --- | --- |
| `encode(n)` | 정수 `n` | 0 이상 정수를 Base62 문자열로 반환. 음수는 `ValueError`, 정수가 아니거나 불리언이면 `TypeError` |
| `decode(s)` | 문자열 `s` | Base62 문자열을 정수로 반환. 빈 문자열·잘못된 문자는 `ValueError`, 문자열이 아니면 `TypeError` |

### `src/hash_table.py`

| 클래스·함수 | 입력 | 반환 및 동작 |
| --- | --- | --- |
| `Node` | `key: str`, `value: str`, `next_node: Node | None` | 연결 리스트의 키, 값, 다음 노드를 보관 |
| `ChainedHashTable(initial_capacity=8, max_load=0.75)` | 양의 정수 용량, 양수 유한 최대 적재율 또는 `None` | 빈 테이블 생성. 잘못된 설정은 `ValueError` |
| `hash_index(key)` | 문자열 키 | 현재 버킷 수에 대한 Horner 해시 버킷 인덱스 반환 |
| `hash_trace(key)` | 문자열 키 | 각 문자 처리 후의 `(문자, 중간 해시값)`을 순서대로 담은 튜플 반환. 빈 키는 빈 추적이며 인덱스는 0 |
| `put(key, value)` | 문자열 키와 문자열 값 | 신규 삽입 또는 기존 값 갱신. 신규 삽입 뒤 확장 조건을 확인 |
| `get(key)` | 문자열 키 | 값을 반환하거나 키가 없으면 `None` |
| `get_with_probes(key)` | 문자열 키 | `(값 또는 None, 비교한 노드 수)` 반환. 빈 버킷은 비용 0 |
| `iter_buckets()` | 없음 | 버킷 인덱스와 해당 버킷의 체인 항목을 버킷 순서로 순회 |
| `size`, `capacity`, `load_factor` | 속성 | 항목 수, 버킷 수, `size / capacity` 반환 |
| `_resize()` | 없음 | 버킷 수를 두 배로 늘리고 모든 기존 노드를 새 용량으로 재해시 |

`Node`의 다음 노드는 같은 체인의 다음 항목을 가리킨다. `ChainedHashTable`은 버킷 머리를 보관하는 리스트와 항목 수를 관리한다. 키 비교는 체인 노드를 앞에서부터 확인한다.

#### Horner 해시 및 체이닝

버킷 수가 `M`일 때 `h = 0`에서 시작한다. 문자열의 각 문자 `c`에 대해 왼쪽부터 `h = (31 * h + ord(c)) % M`을 계산한다. 마지막 `h`가 버킷 인덱스다. `hash_trace(key)`도 같은 계산을 수행하여 `/table`에서 각 단계와 최종 인덱스를 보여 줄 수 있게 한다. Python 내장 `hash()`는 호출하지 않는다.

서로 다른 키가 같은 인덱스를 얻으면 해당 버킷의 연결 리스트에 함께 둔다. `put`은 먼저 체인에서 키가 이미 있는지 찾고, 있으면 값을 갱신하여 항목 수를 유지한다. 없으면 체인 머리에 노드를 추가하고 항목 수를 1 증가시킨다.

#### 확장 및 재해시

신규 삽입 이후 `max_load`가 `None`이 아니고 `size / capacity > max_load`이면 용량을 두 배로 늘린다. 기존 체인의 모든 노드를 순회하며 **새 용량**으로 Horner 해시를 다시 계산해 새 버킷 리스트에 연결한다. 적재율이 최대값 이하가 될 때까지 두 배 확장과 재해시를 반복한다. 기존 키와 값은 모두 보존한다. `max_load=None`이면 충돌 체이닝은 계속하지만 자동 확장·재해시는 하지 않는다.

### `src/shortener.py`

| 클래스·함수 | 입력 | 반환 및 동작 |
| --- | --- | --- |
| `URLShortener(initial_capacity=8, max_load=0.75)` | 테이블 초기 용량과 최대 적재율 설정 | URL→코드·코드→URL `ChainedHashTable` 두 개와 다음 일련번호 1로 초기화 |
| `shorten(url)` | URL 문자열 | 단축 코드 문자열 반환. 비문자열은 `TypeError`; 길이 초과·기타 잘못된 URL은 `ValueError` |
| `expand(code)` | 단축 코드 문자열 | 원본 URL 반환. 잘못된 Base62는 `ValueError`, 등록되지 않은 코드는 `KeyError`, 비문자열은 `TypeError` |
| `tables()` | 없음 | 시각화에 필요한 두 테이블을 이름과 함께 순서가 보존되는 튜플로 반환 |

`shorten`은 먼저 입력 타입, 2048자 제한, 공백·제어 문자, `urlsplit` 결과의 HTTP/HTTPS scheme, hostname, 포트 범위를 검증한다. URL은 trim 또는 정규화하지 않고 원문 그대로 사용한다. URL→코드 테이블에서 이미 찾으면 기존 코드를 돌려주며 순번을 증가시키지 않는다. 새 URL이면 현재 순번을 `base62.encode`로 변환해 코드로 삼고 양쪽 테이블에 매핑을 넣은 뒤 다음 순번을 증가시킨다. 검증에 실패한 입력은 어떠한 매핑이나 순번도 소비하지 않는다.

`expand`는 먼저 Base62 문법을 검증한 다음 코드→URL 테이블에서 **문자열 그대로** 조회한다. 따라서 문법상 숫자값이 같더라도 `"01"`은 발급된 `"1"`과 다른 키다. 테이블 조회 결과가 없으면 `KeyError`를 발생시킨다.

### `src/server.py`

| 클래스·함수 | 입력 | 반환 및 동작 |
| --- | --- | --- |
| `ShortenerHandler(BaseHTTPRequestHandler)` | 표준 HTTP 요청 | `GET` 및 `POST`를 SPEC.md 경로에 맞게 처리 |
| `do_GET()` | 경로와 HTTP 헤더 | `/`, `/table`, `/r/<code>`를 처리하고 상태·헤더·응답 본문을 작성 |
| `do_POST()` | `/shorten` 폼 요청 | URL을 단축해 결과 HTML 또는 400 오류 HTML 반환 |
| `render_home()` | 없음 | URL 입력 폼의 UTF-8 HTML 문자열 반환 |
| `render_table()` | 두 테이블의 반복 가능한 상태 | 각 방향 테이블의 용량, 크기, 적재율, 버킷 체인, 키별 Horner 해시 단계를 표시한 HTML 문자열 반환 |
| `main()` | `--port` 인자(기본 8000) | 모든 인터페이스에서 HTTP 서버를 실행 |

`GET /r/<code>`는 등록된 URL을 `302 Found`와 `Location` 헤더로 전달한다. 등록되지 않은 코드나 코드 경로의 잘못된 입력은 404를 반환한다. `POST /shorten`은 `application/x-www-form-urlencoded` 본문에서 `url` 필드를 읽고, 없는 필드·잘못된 형식·잘못된 URL은 400으로 응답한다. 폼은 `urllib.parse.parse_qsl`의 키-값 쌍 목록에서 값을 찾고, 내장 딕셔너리로 변환하지 않는다.

응답은 UTF-8과 적절한 `Content-Type`을 설정한다. 동적 값은 `html.escape`로 이스케이프한다. 단축 링크는 요청 호스트와 접속 프로토콜을 사용한다. Codespaces처럼 TLS 종료 프록시 뒤에서 실행될 때는 신뢰하는 프록시가 전달한 프로토콜 정보(예: `X-Forwarded-Proto`)를 반영하여 HTTPS 링크를 생성하고, 로컬 HTTP 접속은 HTTP 링크를 생성한다.

### `experiments/probe_experiment.py`

| 함수 | 입력 | 반환 및 동작 |
| --- | --- | --- |
| `load_factors()` | 없음 | `0.25`부터 `4.0`까지 `0.25` 간격의 적재율 튜플 반환 |
| `measure_search_costs(table, successful_keys, missing_keys)` | 해시 테이블, 성공 키 목록, 미등록 키 목록 | 두 목록 모두 비어 있지 않을 때 `(평균 성공 비교 횟수, 평균 실패 비교 횟수)` 반환. 어느 한 목록이라도 비면 `ValueError` |
| `theoretical_costs(alpha)` | 적재율 α | `(성공 탐색 기준값, 실패 탐색 기준값)` 반환 |
| `run_experiment()` | 없음 | 고정 실험 설정으로 적재율별 비용 행을 계산하고 CSV와 SVG 결과를 저장 |
| `write_results_csv(rows, path="experiments/results.csv")` | 결과 행과 출력 경로 | 표준 라이브러리 `csv` 모듈로 결과 CSV 저장 |
| `write_results_svg(rows, path="experiments/probe_costs.svg")` | 결과 행과 출력 경로 | 표준 라이브러리만으로 실측·이론값 네 계열의 SVG 선 그래프 저장 |
| `main()` | 없음 | `run_experiment()` 실행. `make experiment` 진입점 |

실험은 고정 난수 시드 `2026`, 버킷 수 `4000`, 적재율 `0.25`~`4.0`(간격 `0.25`)을 사용한다. 항목 수는 `적재율 * 버킷 수`로 정하고, 각 적재율에서 성공·실패 조회를 각각 항목 수만큼 수행한다. `max_load=None`으로 자동 확장을 끄며 별도 이름 공간의 키로 실패 탐색을 보장한다. 재현에 필요한 시드, 버킷 수, 항목 수, 성공·실패 조회 횟수를 CSV 각 행에 기록한다. CSV 열은 `load_factor`, `seed`, `bucket_count`, `item_count`, `successful_query_count`, `failed_query_count`, `measured_success_probes`, `theoretical_success_probes`, `measured_failure_probes`, `theoretical_failure_probes`로 구성한다. SVG에는 적재율을 x축, 비교 횟수를 y축으로 하여 성공 실측·이론 및 실패 실측·이론의 네 계열을 표시한다. 각 행의 데이터를 표준 출력에도 요약해 `make experiment` 실행 결과를 확인할 수 있게 한다.

## 단계별 테스트 우선 작업 및 완료 기준

### 단계 0 — 기준선과 작업 범위 확인

1. `make test`를 실행해 기존 Base62 테스트 기준선을 확인한다.
2. `src/base62.py`, `tests/test_base62.py`는 수정하지 않는다.
3. 이후 작업에서 `dict`, `set`, `hash()`가 새로 사용되지 않도록 변경 파일을 검토한다.

**검증 및 완료 기준:** 기존 Base62 테스트가 모두 통과하고, 신규 변경 범위가 단계별 계획과 일치한다.

### 단계 1 — 개별 체이닝 해시 테이블

1. 구현 전에 `tests/test_hash_table.py`를 작성한다.
2. 기본 설정과 잘못된 생성자 입력, 문자열 키 검증 테스트를 작성한다.
3. 빈 문자열 해시, 지정된 Horner 식의 결과, 키별 중간 해시 추적을 검증한다.
4. 충돌을 만드는 서로 다른 키의 삽입·조회, 동일 키 갱신, 없는 키 조회와 비교 횟수를 검증한다.
5. 확장 직전(`6/8`)에는 용량 8이 유지되고, 일곱 번째 신규 삽입 뒤에는 용량이 16 이상이 되는지 검증한다.
6. 재해시 이후 모든 키를 찾을 수 있는지, `max_load=None`일 때 용량 8이 유지되는지 검증한다.
7. 테스트를 통과하도록 `Node`와 `ChainedHashTable`을 구현한다.

**검증 및 완료 기준:** `python3 -m unittest discover -s tests -p 'test_hash_table.py' -v`와 `make test`가 통과한다. 충돌 키가 모두 조회되고, 재해시 후 데이터가 보존되며, probe 수가 실제 비교 노드 수와 일치한다.

### 단계 2 — URL 단축기

1. 구현 전에 `tests/test_shortener.py`를 작성한다.
2. 유효 URL과 잘못된 scheme·hostname·port·공백·제어 문자·비문자열을 포함한 입력 테스트를 작성한다.
3. 2048자 URL이 허용되고 2049자 URL이 `ValueError`를 발생시키며 새 코드나 매핑을 소비하지 않는지 테스트한다.
4. 첫 URL이 `"1"`을 받고, 다음 고유 URL이 다음 순번의 Base62 코드가 되는지 검증한다.
5. 동일 원문 URL의 중복 입력이 기존 코드를 반환하고 다음 순번을 소모하지 않는지 검증한다.
6. 양방향 매핑, 정규화하지 않는 비교, 정상 `expand`, 알 수 없는 코드의 `KeyError`, `"01"`의 별칭 비인정, 잘못된 Base62 문자의 `ValueError`를 테스트한다.
7. 테스트에 맞춰 두 해시 테이블을 연결하는 `URLShortener`를 구현한다.

**검증 및 완료 기준:** `python3 -m unittest discover -s tests -p 'test_shortener.py' -v`와 `make test` 통과. 잘못된 입력은 예외로 드러나고, 일련번호·매핑에는 부작용이 없다.

### 단계 3 — 탐색 비용 실험과 이론 비교

1. 구현 전에 `tests/test_probe_experiment.py`를 작성해 적재율 범위, 성공·실패 비용의 분리, 빈 표본 입력의 `ValueError`, 이론 기준값 계산을 검증한다.
2. `experiments/probe_experiment.py`에서 시드 `2026`, 버킷 수 `4000`, 적재율 `0.25`부터 `4.0`까지 `0.25` 간격으로 실험한다.
3. `random.Random`에 고정 시드를 주어 키를 재현 가능하게 생성한다. 고정 버킷 수와 `max_load=None`을 사용하고 적재율에 맞춰 고유 키 개수를 설정한다. 실패 조회 키는 성공 키와 다른 이름 공간으로 만든다.
4. 저장 키 조회와 미등록 키 조회를 별도 목록으로 순회한다. 각 조회에서 `get_with_probes`가 반환한 비교 수를 합산하고 조회 횟수로 나눠 두 평균을 각각 계산한다.
5. 각 적재율에서 항목 수만큼 성공 조회와 실패 조회를 각각 수행한다. 균등 해싱 가정의 개별 체이닝 기준값인 성공 탐색 약 `1 + α/2`, 실패 탐색 약 `α`와 실측값을 비교한다. 이 값은 기대값 기준이며 입력 분포에 따라 실측은 달라질 수 있음을 결과 설명에 적는다.
6. 설정값, 조회 횟수, 적재율, 실측 및 이론값을 `experiments/results.csv`에 저장하고, 네 계열을 비교하는 `experiments/probe_costs.svg`를 생성한다. CSV와 SVG는 Python 표준 라이브러리만 사용한다.
7. `make experiment`로 실행해 모든 적재율 행이 출력되고 CSV와 SVG 파일이 생성되는지 확인한다.

**검증 및 완료 기준:** `python3 -m unittest discover -s tests -p 'test_probe_experiment.py' -v`와 `make test`가 통과한다. 적재율 범위가 양 끝값을 포함하고, 성공·실패 비용이 따로 출력되며, 내장 `dict`, `set`, `hash()` 없이 반복 실행 가능한 실험이 `make experiment`로 동작한다.

### 단계 4 — HTTP 서비스와 시각화

1. 구현 전에 `tests/test_server.py`를 작성하고 테스트용 서버를 임시 포트에서 띄울 준비를 한다. 테스트에는 `GET /`의 200·UTF-8·폼, `POST /shorten` 정상 응답과 누락·잘못된 URL의 400, `GET /r/<code>`의 302·`Location`·404, `/table`의 두 테이블 및 키별 Horner 중간값·최종 인덱스, HTML escaping, HTTPS 전달 프로토콜 링크를 포함한다.
2. 구현 전 `python3 -m unittest discover -s tests -p 'test_server.py' -v`를 실행한다. 구현이 없어 실패하는 테스트 이름과 실패 원인을 확인하고, 이 실패 결과를 이슈 #7 진행 댓글에 기록한다.
3. 테스트 실패를 확인한 뒤 `ShortenerHandler`, 화면 렌더링 함수, `main()`을 구현하고 기존 `make serve` 포트 인자를 유지한다.
4. 같은 테스트 명령을 다시 실행한다. 통과 여부와 통과 테스트 수를 기록하고, 실패가 남아 있으면 수정 후 다시 실행한다. 실패 결과와 통과 결과를 각각 이슈 #7 진행 댓글에 기록한다.
5. `make test`를 실행하고, `make serve`가 8000 포트에서 시작되는지 확인한다.
6. 브라우저에서 `/`, `/table`, 단축 및 리다이렉트 흐름을 확인한다. Codespaces에서는 전달 포트를 열어 HTTPS 단축 링크를 휴대폰 또는 브라우저에서 확인한다.

**검증 및 완료 기준:** `python3 -m unittest discover -s tests -p 'test_server.py' -v`와 `make test` 통과. `make serve`가 8000 포트에서 시작되고 브라우저의 `/`, `/table`, 단축 및 리다이렉트 흐름이 동작한다. Codespaces에서는 전달 포트를 열어 HTTPS 단축 링크를 휴대폰 또는 브라우저에서 확인한다.

### 단계 5 — 통합 회귀 검증 및 정리

1. `make test`, `make experiment`, `make serve`를 각각 실행해 전체 기능을 확인한다.
2. SPEC.md 6절과 7절의 각 사례가 테스트 또는 명시적인 수동 검증 절차에 반영되었는지 대조한다.
3. 앱·테스트·실험 변경분에서 `dict`, `set`, `hash()` 사용이 없는지 검색한다.
4. HTTP 상태, HTTPS 링크, HTML escaping, 재해시 전후 양방향 매핑을 점검한다.
5. 구현과 실험의 사용 방법 및 관찰된 이론-실측 차이를 README 또는 과제 보고 자료에 반영할 필요가 있는지 확인한다.
6. 선형 탐지 구현 및 체이닝과의 최종 성능 비교는 이 계획 범위에서 진행하지 않고 이슈 #8에서 별도로 수행한다.

**검증 및 완료 기준:** 모든 자동 테스트와 실험 명령이 성공하고, 6·7절 경계 사례와 파일별 완료 조건을 확인한다. 미완료 또는 환경 의존 수동 확인 사항은 결과에 따로 기록한다.
