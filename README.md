# HVDC Knowledge MCP Server

> Samsung C&T x ADNOC x DSV | UAE HVDC Project Logistics  
> Claude용 stdio MCP + ChatGPT용 remote MCP(`/mcp`) 겸용 서버

## 개요

이 저장소는 HVDC 물류/통관/창고/해상운송 도메인 문서를 MCP 도구로 노출합니다.

- Claude Code / Claude Desktop에서는 `stdio` MCP 서버로 사용
- ChatGPT Apps / Connectors에서는 `streamable-http` MCP 서버로 사용
- ChatGPT 호환용 표준 `search` / `fetch` 도구 포함
- 기존 도메인 전용 도구(`hvdc_*`)는 그대로 유지

상세 인수인계 문서:

- [CHATGPT_CODEX_CURSOR_HANDOFF.md](./CHATGPT_CODEX_CURSOR_HANDOFF.md)
- [WINDOWS_MULTI_PC_PACKAGE.md](./WINDOWS_MULTI_PC_PACKAGE.md)

## 지원 아키텍처

- `tool-first` MCP server with optional widget flows
- ChatGPT remote usage is primarily tool-driven, with widget support for CSV/XLSX upload flows
- 회사 지식/문서 검색 용도에 맞춰 `search` / `fetch` 스키마 적용

## 프로젝트 구조

```text
hvdc-knowledge-gpt-mcp/
├── config/
│   └── domain_rules.yaml
├── server.py
├── README.md
├── requirements.txt
├── install.py
├── .codex/
│   └── config.toml
├── .cursor/
│   ├── mcp.json
│   └── rules/
│       └── hvdc-domain-background.mdc
├── hvdc_ops/
├── excel-mcp/
├── widgets/
├── scripts/
│   ├── validate.py
│   ├── deploy.py
│   ├── remote_mcp.py
│   ├── start-excel-mcp.ps1
│   ├── export_domain_context.py
│   └── lint_repo_links.py
└── docs/
    ├── Logi ontol core doc/
    └── architecture/
```

## 요구사항

- Python 3.10+
- `pip install -r requirements.txt`

`requirements.txt`:

- `mcp`
- `pandas`
- `openpyxl`
- `pydantic`
- `uvicorn`

## 빠른 시작

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

Windows 다른 PC로 옮겨 바로 쓰는 경우:

- 더블클릭: [SETUP_WINDOWS_CLIENT.cmd](./SETUP_WINDOWS_CLIENT.cmd)
- 풀옵 원클릭: [SETUP_WINDOWS_FULL.cmd](./SETUP_WINDOWS_FULL.cmd)
- 문서: [WINDOWS_MULTI_PC_PACKAGE.md](./WINDOWS_MULTI_PC_PACKAGE.md)
- 패키지 생성 스크립트: [build_windows_portable_bundle.ps1](./scripts/build_windows_portable_bundle.ps1)

### 1a. Excel MCP 동반 실행

Excel 서브 MCP는 메인 HVDC MCP와 분리되어 동작합니다.

- 기본 포트: `127.0.0.1:8002`
- 설치/실행 스크립트: [start-excel-mcp.ps1](./scripts/start-excel-mcp.ps1)
- 문서: [excel-mcp/README_KR.md](./excel-mcp/README_KR.md)

설치:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-excel-mcp.ps1 -InstallDeps
```

로컬 실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-excel-mcp.ps1
```

Windows smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-excel-mcp.ps1 -SmokeTest
```

### 2. Claude용 실행

기본 실행은 기존과 동일하게 `stdio` transport입니다.

```bash
python server.py
```

Claude Code / Desktop 등록은 기존 `scripts/deploy.py`를 그대로 사용하면 됩니다.

### Cursor용 실행

Cursor에서는 프로젝트 루트의 `.cursor/mcp.json`으로 MCP 서버를 연결하고, `.cursor/rules/*.mdc`로 도메인 규칙을 항상 적용하는 편이 맞습니다.

이 저장소에는 이미 다음 파일이 포함돼 있습니다.

- [mcp.json](./.cursor/mcp.json)
- [hvdc-domain-background.mdc](./.cursor/rules/hvdc-domain-background.mdc)
- [cursor_mcp.cmd](./scripts/cursor_mcp.cmd)

설정 내용:

- `hvdc-knowledge` MCP 서버를 `stdio` 모드로 실행
- Python 절대경로를 쓰지 않고 repo 내부 wrapper가 `.venv`, `py -3`, `python` 순서로 런타임을 탐색
- Cursor 에이전트가 이 저장소에서 HVDC 도메인 규칙을 항상 배경 컨텍스트로 사용
- Flow Code, node, KPI, regulation, ZERO gate 관련 코드 변경 시 MCP 조회를 우선하도록 유도

사용 순서:

1. Cursor에서 이 저장소를 엽니다.
2. MCP 설정이 감지되지 않으면 Cursor를 재시작하거나 window reload를 한 번 합니다.
3. Agent 채팅에서 `hvdc-knowledge` 도구가 보이는지 확인합니다.
4. 도메인 로직 작업 시 `.cursor/rules`가 항상 붙고, 세부 근거가 필요하면 MCP 도구가 호출됩니다.

멀티 PC 권장 조건:

- 각 PC에 Python 또는 `py` launcher가 설치되어 있어야 합니다.
- 가능하면 저장소 루트에 `.venv`를 만들어 두는 편이 가장 안정적입니다.
- 같은 저장소를 3대 모두에서 열면 `.cursor/mcp.json`과 `.cursor/rules`는 그대로 재사용됩니다.

### Codex용 실행

Codex는 이 저장소의 프로젝트 스코프 설정 파일 `.codex/config.toml`을 통해 `hvdc-knowledge` MCP를 읽을 수 있습니다.

이 저장소에는 이미 다음 파일이 포함돼 있습니다.

- [config.toml](./.codex/config.toml)
- [cursor_mcp.cmd](./scripts/cursor_mcp.cmd)

설정 내용:

- `hvdc-knowledge` MCP 서버를 `stdio` 모드로 실행
- 경로를 PC별 절대경로가 아니라 repo-relative wrapper로 유지
- 다른 Windows PC에서도 같은 저장소를 trusted project로 열면 같은 MCP 구성을 재사용 가능

사용 순서:

1. Codex에서 이 저장소를 엽니다.
2. 이 프로젝트를 `trusted`로 승인합니다.
3. `python -m venv .venv` 후 `pip install -r requirements.txt`를 준비합니다.
4. Codex에서 `hvdc-knowledge` MCP가 보이는지 확인합니다.

빠른 점검 예시:

```bash
codex exec --skip-git-repo-check "Call hvdc_get_domain_summary and return only a 3-bullet summary."
```

중요:

- `.codex/config.toml`은 프로젝트 단위 설정입니다.
- 같은 저장소를 다른 PC에 복사하거나 clone하면 Codex MCP 설정도 같이 따라갑니다.
- 전역 `%USERPROFILE%\\.codex\\config.toml` 등록은 이제 선택 사항입니다.
- `.claude/settings.json`은 로컬 머신별 경로를 담는 환경 파일이므로 공개 저장소 기준 설정 문서에 포함하지 않습니다.

#### HVDC Domain Rules - Coding-Safe One Pager

<!-- GENERATED_DOMAIN_ONE_PAGER:START -->

<!-- generated from config/domain_rules.yaml; do not edit manually -->

이 섹션은 Cursor/Agent가 읽을 배경지식과 사람이 구현 규칙을 빠르게 확인하는 용도로 씁니다.

- Scope: SCM/Logistics (Invoice Audit, Customs, Marine Ops, WH Management)
- Scale: ~400 TEU / 100 BL per month, 6 sites
- Sites: MIR, SHU, DAS, AGI plus import ports and MOSB hub

Core nodes:

- Zayed Port (`AEZYD`): Bulk/Heavy cargo
- Khalifa Port (`AEAUH`): Container cargo
- Jebel Ali (`AEJEA`): Freezone / ADOPT
- MOSB: Central hub, 20,000 sqm, SCT resident team
- MIR: SPMT operations, DOT > 90t
- SHU: SPMT operations, DOT > 90t
- DAS: 20h LCT, MOSB leg mandatory
- AGI: 10h LCT, MOSB leg mandatory

Flow Code v3.5:

- `0`: Pre Arrival
- `1`: Port -> Site (direct, no WH)
- `2`: Port -> WH -> Site
- `3`: Port -> MOSB -> Site
- `4`: Port -> WH -> MOSB -> Site
- `5`: Mixed / Waiting / Incomplete

Flow calculation rule:

- `FLOW = 0 if PreArrival else clip(wh_count + offshore + 1, 1, 4)`
- `wh_count` means warehouse legs excluding MOSB
- `offshore = 1 if a MOSB leg exists, otherwise 0`

Mandatory flow overrides:

- If destination is `AGI` or `DAS`, Flow Code `0`, `1`, or `2` must be upgraded to `3`
- For `AGI` and `DAS`, `Flow < 3` is invalid
- Valid offshore paths are typically `3` and `4`

MOSB interpretation:

- MOSB is the central hub and has a 20,000 sqm capacity limit.
- Do not hardcode "all cargo always passes MOSB" as a universal rule
- Direct and non-MOSB flows remain valid for onshore cases unless another rule blocks them.
- Enforce MOSB strictly for `AGI` and `DAS`

Onshore transport rule:

- `MIR` and `SHU` are onshore SPMT destinations
- `DOT` approval is required only when cargo weight is greater than `90 tons`
- Do not block all MIR/SHU movements by default; block only `> 90t` cases without DOT approval

Regulatory gates:

- `FANR`: 방사선 수입허가 (60일)
- `MOIAT_ECAS`: 적합성 인증
- `MOIAT_EQM`: 규제 제품 품질 마크 / 관련 인증
- `DOT`: 중량물 운송 허가
- `CICPA`: 게이트패스
- `ADNOC_FRA`: 리프팅 위험성 평가

ZERO gate triggers:

- eBL mismatch -> Hold berth confirmation
- BOE field gaps -> Stop customs filing
- FANR permit missing -> Hold arrival approval
- MOSB capacity exceeded -> Stop additional intake (>20,000 sqm)
- DOT permit missing -> Stop inland move (>90t)
- Weather alert -> Delay LCT departure

KPI gates:

- `invoice-ocr >= 98.0%`
- `invoice-audit delta <= 2.0%`
- `cost-guard warn rate <= 5.0%`
- `hs-risk misclass <= 0.5%`
- `cert-chk auto-pass >= 90.0%`
- `wh-forecast util <= 85.0%`
- `weather-tie ETA MAPE <= 12.0%`

Coding constants:

- Offshore nodes: `AGI, DAS`
- Onshore nodes: `MIR, SHU`
- MOSB capacity: `20,000 sqm`
- DOT threshold: `90 tons`
- AGI/DAS minimum flow: `3`

Safe implementation rules:

- Never infer DOT requirement unless weight is known and `> 90`
- Never allow `AGI` or `DAS` to remain on Flow `0`, `1`, or `2`
- Treat missing regulatory evidence as `not_evaluated` or `blocked`, not implicit pass
- Keep `MOIAT_ECAS` and `MOIAT_EQM` separable in code even if documentation sometimes groups them
- Distinguish summary wording from enforced logic; enforce only explicit rules

MCP usage pattern:

- Call `hvdc_get_domain_summary` at session start for baseline context
- Use `hvdc_get_flow_code` for flow validation
- Use `hvdc_get_node_info` for node-specific constraints
- Use `hvdc_get_kpi` for threshold lookup
- Use `hvdc_get_regulations` for permit and block actions
- Use `hvdc_search_docs` or `hvdc_read_doc` for detailed evidence before making abnormality judgments

Practical decision rule:

- If a shipment is for `AGI` or `DAS`, first validate MOSB leg and Flow Code
- If a shipment is for `MIR` or `SHU`, first validate gross weight and DOT threshold
- If evidence for permits, BOE, eBL, or weather is missing, do not return a clean pass

<!-- GENERATED_DOMAIN_ONE_PAGER:END -->

#### Cursor Prompt Cookbook

아래 프롬프트는 Cursor Agent에서 그대로 붙여 넣어 쓰는 용도입니다. 권장 흐름은 `domain refresh -> targeted validation -> review` 입니다.

Flow Code:

1. ```text
   hvdc_get_domain_summary를 먼저 호출하고, 이어서 hvdc_get_flow_code와 hvdc_get_node_info를 사용해 이 모듈의 Flow Code 로직이 AGI/DAS minimum Flow 3 규칙을 지키는지 점검해줘.
   ```
2. ```text
   이 함수의 routing 판정을 리뷰해줘. AGI/DAS는 Flow 0/1/2를 3으로 강제 승급하고, MIR/SHU는 MOSB를 무조건 요구하지 않는 방향으로만 수정해줘.
   ```
3. ```text
   hvdc_search_docs로 Flow Code v3.5 근거 문서를 찾고, 이 구현이 공식 규칙과 어긋나는 부분만 파일/라인 기준으로 지적해줘.
   ```

Customs / Regulations:

1. ```text
   hvdc_get_regulations를 사용해서 이 통관 로직이 FANR, MOIAT_ECAS, MOIAT_EQM, CICPA, ADNOC_FRA 조건을 빠뜨리지 않았는지 검토해줘.
   ```
2. ```text
   이 customs validation 코드를 수정해줘. BOE field gaps는 blocked, FANR evidence missing은 hold, missing data는 implicit pass가 아니라 not_evaluated로 처리해줘.
   ```
3. ```text
   hvdc_read_doc와 hvdc_get_regulations를 근거로, 이 import workflow에서 실제 block action과 warning action을 분리해서 다시 설계해줘.
   ```

Dashboard:

1. ```text
   이 대시보드가 HVDC 운영 판단에 필요한 값만 보여주는지 점검해줘. health score, ZERO alerts, MOSB capacity, DOT blockers, upload readiness가 빠져 있으면 추가해줘.
   ```
2. ```text
   hvdc_get_kpi와 도메인 규칙을 기준으로 대시보드 KPI 카드가 실제 threshold와 일치하는지 검토하고, 잘못된 라벨이나 수식을 수정해줘.
   ```
3. ```text
   이 dashboard/status payload를 리뷰해줘. 운영팀이 backlog risk와 ZERO candidate를 바로 판단할 수 있도록 필요한 필드만 추가하고 중복 필드는 정리해줘.
   ```

Excel / Backlog Analysis:

1. ```text
   hvdc_analyze_backlog_batch를 사용해서 이 파일을 분석해줘: <파일경로>. site별 backlog, mode별 hotspot, ZERO candidate, KPI breach를 먼저 요약해줘.
   ```
2. ```text
   이 엑셀 데이터를 hvdc_analyze_shipment_case와 hvdc_zero_gate_check 기준으로 해석해서 AGI/DAS flow 위반, >90t DOT 누락, MOSB capacity 위험만 우선 추려줘.
   ```
3. ```text
   이 backlog 파일을 분석한 뒤, 결과를 바탕으로 코드에서 어떤 validation rule을 추가해야 하는지까지 연결해서 제안해줘. 문서 근거가 있으면 hvdc_search_docs로 같이 확인해줘.
   ```

Review pattern:

1. ```text
   hvdc_get_domain_summary를 먼저 호출하고, 필요한 경우 hvdc_get_flow_code / hvdc_get_regulations / hvdc_get_kpi를 추가 호출해서 관련 규칙만 추려줘. 그다음 그 규칙을 깨지 않는 최소 수정안으로 구현하고 회귀 테스트까지 추가해줘.
   ```
2. ```text
   이 변경사항을 코드 리뷰해줘. 버그, 규칙 위반, 회귀 위험을 우선으로 보고, hvdc_search_docs와 hvdc_read_doc로 근거 문서를 찾아서 파일/라인 기준으로 지적해줘.
   ```

### 3. ChatGPT용 실행

ChatGPT에서는 원격 MCP 엔드포인트가 필요하므로 `streamable-http`로 실행합니다.

```bash
python server.py --transport streamable-http --host 127.0.0.1 --port 8000
```

로컬 개발에서 ngrok를 쓰는 경우:

```bash
python server.py --transport streamable-http --host 127.0.0.1 --port 8000 --public-base-url https://abc123.ngrok.app
```

중요:

- ChatGPT는 HTTPS `/mcp` 엔드포인트로 연결해야 합니다.
- `--public-base-url`을 주면 `search` / `fetch` 결과의 문서 URL과 Host/Origin 보안 설정이 같이 맞춰집니다.
- `--public-base-url` 없이도 dev 모드 실행은 되지만, `search` / `fetch` URL은 localhost 기준으로 생성됩니다.

### 4. ChatGPT remote MCP 원클릭 실행

ChatGPT 연결까지 한 번에 끝내려면 관리 스크립트를 쓰는 편이 안전합니다.

```bash
python scripts/remote_mcp.py start
```

Tailscale Funnel을 쓰는 경우:

```bash
python scripts/remote_mcp.py start --tailscale-funnel
```

이 스크립트는 다음을 자동으로 처리합니다.

- Windows에서는 `cloudflared`가 없으면 `.runtime/tools/` 아래로 자동 다운로드
- `trycloudflare.com` HTTPS URL 생성
- `HVDC_PUBLIC_BASE_URL`을 public URL로 설정한 뒤 `streamable-http` MCP 서버 기동
- 상태를 `.runtime/chatgpt_remote_state.json`에 저장

`--tailscale-funnel` 모드에서는 다음처럼 동작합니다.

- 로컬 `tailscale` CLI를 사용해 현재 머신의 `https://<hostname>.ts.net` Funnel을 관리
- 고정 `ts.net` 호스트를 `public_base_url`로 광고
- `cloudflared` 없이 같은 스크립트의 `status` / `stop` / `supervise` 흐름을 그대로 사용

중요:

- `start`는 빠른 개발/테스트용입니다.
- `trycloudflare.com` quick tunnel은 URL이 바뀔 수 있으므로 장기 운영용 고정 URL로 보지 않는 편이 맞습니다.
- `--tailscale-funnel`은 Tailscale 로그인, MagicDNS, Funnel 활성화가 선행되어야 합니다.

유용한 명령:

```bash
python scripts/remote_mcp.py status
python scripts/remote_mcp.py stop
python scripts/remote_mcp.py supervise
```

`start`가 성공하면 출력된 `https://.../mcp` URL을 그대로 ChatGPT app 생성 화면에 넣으면 됩니다.
브라우저 상태 대시보드는 같은 public host의 `/dashboard` 에서 확인할 수 있습니다.
대시보드는 health score, alert panel, restart history, probe latency, 최근 1시간 trend, 탭형 로그 뷰를 포함합니다.

### 5. 안정 운영 모드

장기 운영에서는 다음 두 가지 중 하나를 권장합니다.

1. Tailscale Funnel로 이 PC를 고정 주소로 노출하는 경우  

```bash
python scripts/remote_mcp.py supervise --tailscale-funnel
```

이 모드는 현재 Tailscale 머신의 `https://<hostname>.ts.net` 주소를 public MCP host로 사용합니다. `tailscale funnel --bg --yes <port>`를 스크립트가 직접 관리하며, 같은 `ts.net` 호스트를 ChatGPT connector에 계속 사용할 수 있습니다.

2. 외부 고정 HTTPS 엔드포인트가 이미 있는 경우  

```bash
python scripts/remote_mcp.py supervise --skip-tunnel --public-base-url https://mcp.example.com
```

이 모드는 로컬 MCP 서버만 감시/재기동합니다. 외부 reverse proxy, Cloudflare named tunnel, nginx, Vercel/Fly/AWS 등의 고정 HTTPS 엔드포인트가 이미 `127.0.0.1:<port>`로 연결되어 있어야 합니다.

3. Windows 자동 시작이 필요한 경우  

```bash
python scripts/remote_mcp.py install-task --skip-tunnel --public-base-url https://mcp.example.com
```

작업 스케줄러에 감독 프로세스를 등록해서 로그인 시 자동 시작되게 할 수 있습니다. 작업 스케줄러 등록이 권한 문제로 막히는 환경에서는 Startup 폴더 launcher로 자동 fallback 됩니다.

Tailscale Funnel 자동 시작 예시:

```bash
python scripts/remote_mcp.py install-task --tailscale-funnel
python scripts/remote_mcp.py install-startup --tailscale-funnel
```

관련 명령:

```bash
python scripts/remote_mcp.py remove-task
python scripts/remote_mcp.py install-startup
python scripts/remote_mcp.py remove-startup
```

### 6. Railway 배포

Railway로 옮길 때는 저장소에 포함된 배포 파일을 그대로 쓰면 됩니다.

- [Dockerfile](./Dockerfile)
- [railway.json](./railway.json)
- [railway_run.py](./scripts/railway_run.py)

기본 배포 순서:

```bash
railway login
railway init -n hvdc-knowledge-mcp
railway up
railway domain
```

이 구성은 다음을 자동 처리합니다.

- Dockerfile 기반 배포
- `/health` 기준 health check
- Railway `PORT` 자동 bind
- `RAILWAY_PUBLIC_DOMAIN`이 있으면 `https://<domain>`을 `public_base_url`로 자동 적용

배포 후 ChatGPT connector URL:

```text
https://<railway-public-domain>/mcp
```

배포 후 대시보드 URL:

```text
https://<railway-public-domain>/dashboard
```

## ChatGPT 연결 방법

OpenAI Apps SDK 문서 기준으로, 이 서버는 `tool-first MCP server with optional widget flows` 구성입니다.

1. `python server.py --transport streamable-http ...` 로 서버 실행
2. `ngrok http 8000` 또는 Cloudflare Tunnel로 HTTPS URL 확보
3. ChatGPT에서 `Settings → Apps & Connectors → Advanced settings` 에서 Developer Mode 활성화
4. `Settings → Connectors → Create` 로 이동
5. Connector URL에 `https://<public-host>/mcp` 입력
6. 새 채팅에서 해당 app을 추가 후 도구 호출

중요:

- upload widget은 ChatGPT 업로드 흐름을 여는 optional UI입니다.
- authoritative backlog result는 `hvdc_analyze_backlog_batch`가 반환합니다.
- authoritative machine-readable payload는 `structuredContent`입니다.

원클릭 스크립트를 쓴 경우에는 `python scripts/remote_mcp.py start` 출력의 `Connector URL` 값을 그대로 사용하면 됩니다.
Tailscale Funnel 모드에서는 `https://<hostname>.ts.net/mcp` 를 그대로 사용하면 됩니다.
Railway에서는 `https://<railway-public-domain>/mcp` 를 그대로 사용하면 됩니다.
안정 운영 모드에서는 고정 HTTPS 엔드포인트의 `/mcp` URL을 사용하면 됩니다.

권장 Connector 메타데이터:

- Name: `HVDC Knowledge`
- Description: `Searches HVDC UAE logistics documents, flow-code rules, site constraints, KPI thresholds, and UAE regulatory requirements.`

## HTTP 엔드포인트

`streamable-http` 실행 시 다음 경로가 열립니다.

- `GET /` : 서버 상태/도구 목록
- `GET /health` : 헬스체크
- `GET /dashboard` : 운영 대시보드 HTML
- `GET /dashboard/status` : 대시보드용 상태 JSON
- `GET /dashboard/self-test` : on-demand MCP self-test JSON
- `POST|GET|DELETE /mcp` : MCP endpoint
- `GET /docs` : 문서 인덱스
- `GET /docs/{doc_id}` : 문서 원문

운영 대시보드에 Excel MCP readiness를 표시하려면 선택적으로 다음 env를 설정합니다.

```text
HVDC_EXCEL_MCP_URL=http://127.0.0.1:8002
```

`/mcp` 전체 URL을 넣어도 동작하지만, 기본값은 Excel MCP base URL입니다.

## MCP 도구

### ChatGPT 표준 도구

| Tool | 용도 | 입력 |
|------|------|------|
| `search` | ChatGPT company knowledge / deep research 호환 문서 검색 | `query` |
| `fetch` | `search` 결과 문서 원문 조회 | `id` |

### 도메인 전용 도구

| Tool | 용도 | 주요 파라미터 |
|------|------|--------------|
| `hvdc_get_domain_summary` | 전체 도메인 요약 | — |
| `hvdc_search_docs` | 로컬 markdown 키워드 검색 + 스니펫 | `keyword`, `max_results` |
| `hvdc_read_doc` | 특정 문서/섹션 읽기 | `filename`, `section` |
| `hvdc_list_docs` | 문서 목록, doc id, URL 조회 | — |
| `hvdc_get_node_info` | 8개 노드 상세 정보 | `node_name` |
| `hvdc_get_flow_code` | Flow Code v3.5 조회/검증 | `code`, `destination` |
| `hvdc_get_kpi` | KPI 임계값 조회 | `kpi_name` |
| `hvdc_get_regulations` | UAE 규제 요건 조회 | `regulation_name` |
| `hvdc_hs_code_lookup` | HS Code 예시 조회 | `query` |
| `hvdc_analyze_shipment_case` | 단건 shipment를 Flow Code, ZERO gate, KPI 기준으로 판정 | `shipment` 또는 `file`/`local_path`, `row_number`/`shipment_id`, `sheet_name`, `column_map` |
| `hvdc_render_backlog_upload_widget` | ChatGPT widget에서 CSV/XLSX 업로드 후 backlog 분석 실행 | `snapshot_name`, `sheet_name`, `column_map` |
| `hvdc_analyze_backlog_batch` | CSV/XLSX backlog 배치 분석 + snapshot 저장 | `file`/`local_path`, `sheet_name`, `column_map`, `snapshot_name` |
| `hvdc_zero_gate_check` | 단건 운영 컨텍스트 ZERO gate 판정 | `destination`, `gross_weight_tons`, `weather_alert`, `boe_complete`, ... |
| `hvdc_compare_snapshots` | 저장된 backlog snapshot 2개 비교 | `baseline_snapshot`, `candidate_snapshot` |
| `hvdc_mcp_self_test` | `/mcp`, dashboard, connector freshness 진단 | `target`, `include_tool_calls` |

## 사용 예시

### Claude / ChatGPT 공통

```text
MOSB 경유 여부에 따라 Flow Code를 계산하는 Python 함수 작성해줘
```

```text
AGI 현장 LCT 출항 연기 관련 규제 리스크 정리해줘
```

```text
DOT permit 기준과 MIR/SHU 제약을 한 번에 알려줘
```

```text
tests/fixtures/analysis_backlog_sample.csv를 기준으로 AGI, DAS, MIR backlog를 ZERO 기준으로 분석해줘
```

```text
Backlog upload widget을 열어서 XLSX를 올리고 ZERO 후보를 분석해줘
```

```text
snapshot ops-baseline 과 ops-candidate 를 비교해서 새 ZERO 후보만 정리해줘
```

### ChatGPT company knowledge 스타일

`search("flow code")` → 관련 문서 id 목록  
`fetch("<document-id>")` → 문서 본문 + citation URL

## 검증

전체 검증:

```bash
python scripts/validate.py
```

빠른 검증:

```bash
python scripts/validate.py --quick
```

현재 검증 범위:

- `server.py` 문법 검사
- `install.py` / `deploy.py` / `remote_mcp.py` / `railway_run.py` / `hvdc_ops/*` 문법 검사
- 핵심 import 검사
- 기존 `hvdc_*` 도구 통합 테스트
- `hvdc_analyze_shipment_case` CSV file param / XLSX local path / `column_map` 테스트
- `hvdc_analyze_backlog_batch` snapshot 저장 / overwrite 테스트
- `hvdc_zero_gate_check` `not_evaluated` 동작 테스트
- `hvdc_compare_snapshots` delta 계산 테스트
- `hvdc_mcp_self_test` stale connector 감지 테스트
- `APP_INSTRUCTIONS` widget-first / authoritative `structuredContent` guidance 테스트
- ChatGPT 표준 `search` / `fetch` 응답 형식 테스트
- path traversal 차단 테스트

## 알려진 제한

- `search` / `fetch`는 너무 큰 통합 문서(`LOGI_ONTOL_CORE_MERGED.md`)를 기본 인덱스에서 제외합니다.
- `hvdc_search_docs`는 `.md`만 검색합니다.
- HS Code 조회는 내장 예시 5건 기준입니다.
- `hvdc_analyze_*`의 `local_path`는 보안상 `stdio` 실행에서만 허용됩니다.
- Railway 같은 remote MCP 서버는 ChatGPT의 `sandbox:/...` 경로를 직접 읽을 수 없습니다.
- ChatGPT에서 CSV/XLSX를 올릴 때는 `hvdc_render_backlog_upload_widget`을 사용해 temporary HTTP `download_url`을 받아야 합니다.
- upload widget은 optional UI일 뿐이며, authoritative backlog result와 snapshot 생성은 `hvdc_analyze_backlog_batch`가 담당합니다.
- authoritative machine-readable output은 `structuredContent`입니다.
- 대시보드의 `ChatGPT Upload` 카드에서 widget readiness, 허용 확장자, `sandbox:/...` 직접 읽기 불가 여부를 바로 확인할 수 있습니다.
- 대시보드의 `Client Surfaces` 카드에서 `ChatGPT`, `Cursor`, `Codex`별 준비 상태와 다음 조치를 바로 확인할 수 있습니다.
- 대시보드의 `Self Test` 섹션은 `/dashboard/self-test`를 호출해 local/public health, dashboard, MCP initialize, tools/list, sample tool call을 재검증합니다.
- `GET /health` 는 `status`, `checks`, `docs_ready`, `mcp_ready`, `public_probe_ok`, `correlation_id`를 포함하는 additive JSON health payload를 반환합니다.
- `HVDC_EXCEL_MCP_URL`이 설정되면 `/dashboard/status`의 `subservices.excel_mcp`에 Excel health / initialize 상태가 같이 노출됩니다.
- widget resource에는 Apps SDK 제출 기준에 맞춰 `_meta.ui.domain`, `_meta.ui.csp`, `openai/widgetDomain`, `openai/widgetCSP`가 포함됩니다.
- 공개 배포가 아니라면 인증/OAuth는 아직 붙어 있지 않습니다.
- `scripts/remote_mcp.py`는 Windows amd64에서 `cloudflared` 자동 다운로드를 지원합니다. 다른 OS는 PATH에 `cloudflared`가 있어야 합니다.
- `scripts/remote_mcp.py --tailscale-funnel` 모드는 `tailscale` CLI가 PATH에 있고, 해당 tailnet에서 Funnel이 활성화돼 있어야 합니다.
- Railway 배포는 Railway CLI 로그인과 서비스 public domain 생성이 끝나야 ChatGPT connector로 쓸 수 있습니다.
- Railway에서는 `RAILWAY_PUBLIC_DOMAIN`이 주어지기 전까지 `search` / `fetch` citation URL이 localhost 기준으로 보일 수 있습니다.
- `trycloudflare.com` quick tunnel은 개발 편의를 위한 임시 URL입니다. ChatGPT app URL을 장기 고정하려면 stable HTTPS host 또는 named tunnel을 써야 합니다.

## Claude 배포

기존 배포 방식은 그대로 유지됩니다.

```bash
python install.py
python scripts/deploy.py
```

## 참고

ChatGPT 연결/구현 방향은 OpenAI 공식 문서 기준으로 맞췄습니다.

- Apps SDK Quickstart
- Build your MCP server
- Connect from ChatGPT
- Company knowledge compatibility
