# 과제2 · 에이전트와 함께 만든 URL 단축기

2026-2 **고급알고리즘**(SIT2001-01) 과제2의 **시작 저장소**입니다.
명세에 따라 Base62, 해시 테이블, URL 단축 웹 서비스와 성능 비교 실험을 구현했습니다.

- 과제 안내: [lec-algorithm.github.io/lecture/article/hw2-2026](https://lec-algorithm.github.io/lecture/article/hw2-2026/)
- 수업 슬라이드: [lec-algorithm.github.io/lecture/slides/hw2-2026](https://lec-algorithm.github.io/lecture/slides/hw2-2026/)
- 해시 테이블 복습: [주제 08 해시 테이블](https://lec-algorithm.github.io/lecture/course/topic-08-hashing/)

## 구현 내용

| 파일 | 하는 일 |
| --- | --- |
| `src/base62.py` | 단축 코드의 Base62 인코딩·디코딩 |
| `src/hash_table.py` | 개별 체이닝 해시 테이블 |
| `src/linear_probing.py` | 선형 탐지 해시 테이블 |
| `src/shortener.py` · `src/server.py` | 두 해시 전략을 지원하는 URL 단축기와 웹 서버 |
| `tests/` | 단위·회귀 테스트 |
| `experiments/probe_experiment.py` | 기존 개별 체이닝 탐색 비용 실험 |
| `experiments/compare_experiment.py` | 체이닝과 선형 탐지 탐색 비용 비교 |
| `experiments/comparison_results.csv` · `experiments/comparison.svg` | 비교 실험의 실측 결과와 그래프 |
| `Makefile` | 테스트, 웹 서버 및 실험 명령 |

## 명령

컨테이너 안(Codespaces 터미널)에서 실행합니다.

| 하고 싶은 것 | 명령 |
| --- | --- |
| 테스트 | `make test` |
| 웹 서버 (포트 8000) | `make serve` |
| 충돌 실험 | `make experiment` |
| 체이닝과 선형 탐지 비교 | `make compare-experiment` |
| 놓친 단계 따라잡기 | `sh tools/catchup.sh <단계 번호>` |

외부 라이브러리는 쓰지 않습니다. Python 표준 모듈만으로 충분합니다.

비교 실험은 난수 시드 `42`, 버킷 `4093`개, 적재율 `0.1`~`0.9`를 사용합니다.
두 방식에 같은 URL 키, 삽입 순서, 성공·실패 조회 표본을 적용하고 자동 확장은 끕니다.
각 적재율에서 성공·실패 조회를 각각 10,000회 수행하며, 명령 실행 시 CSV와 SVG를 다시 생성합니다.

## 로컬에서 하기

```sh
git clone https://github.com/<본인 계정>/<내 저장소>.git
cd <내 저장소>
docker compose up -d
docker compose exec lab bash
```

**이후 모든 `docker compose` 명령은 이 폴더에서 칩니다.**
