# Excel MCP (Windows)

Excel 파일을 로컬 폴더 범위 안에서 읽고 쓰는 보조 MCP 서버입니다. 메인 HVDC MCP와 분리되어 동작하며, 기본 로컬 엔드포인트는 `http://127.0.0.1:8002/mcp`입니다.

## 1. 환경 점검

`excel-mcp` 폴더에서 먼저 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\env_check.ps1
```

확인 기준:

- Python 3.12 이상
- `8002` 포트 비어 있음
- 필요 시 `ngrok`로만 외부 노출

## 2. 설치

레포 루트에서:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-excel-mcp.ps1 -InstallDeps
```

또는 수동 설치:

```powershell
cd .\excel-mcp
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. 로컬 실행

레포 루트에서:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-excel-mcp.ps1
```

포트/루트 오버라이드:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-excel-mcp.ps1 -Port 8012 -RootPath C:\data\excel-mcp-workbooks
```

수동 실행:

```powershell
cd .\excel-mcp
$env:EXCEL_MCP_ROOT = "$PWD\workbooks"
$env:EXCEL_MCP_HOST = "127.0.0.1"
$env:EXCEL_MCP_PORT = "8002"
python server.py
```

기본 엔드포인트:

```text
http://127.0.0.1:8002/
http://127.0.0.1:8002/health
http://127.0.0.1:8002/mcp
```

## 4. Smoke Test

실행/환경 변수/MCP initialize까지 한 번에 확인합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-excel-mcp.ps1 -SmokeTest
```

## 5. 제공 툴

- `ping`
- `create_workbook`
- `list_workbooks`
- `get_workbook_info`
- `list_sheets`
- `read_sheet`
- `read_range`
- `append_rows`
- `write_cells`
- `write_range`
- `sheet_dimensions`
- `apply_hvdc_export`

## 6. HVDC 연동

메인 대시보드에 Excel MCP readiness를 표시하려면 메인 HVDC MCP 환경에 다음을 추가합니다.

```text
HVDC_EXCEL_MCP_URL=http://127.0.0.1:8002
```

그러면 메인 `/dashboard/status`의 `subservices.excel_mcp`에 health / initialize 결과가 같이 보입니다.

## 7. ChatGPT Developer Mode 연결

기본 권장 모드는 로컬/private 운영입니다. 외부 공개가 필요할 때만 HTTPS로 노출합니다.

```powershell
ngrok http 8002
```

생성된 HTTPS URL 예시:

```text
https://example.ngrok.app
```

ChatGPT Developer Mode / MCP Server 등록 시 입력:

```text
https://example.ngrok.app/mcp
```

## 8. 보안 기준

- 루트 폴더 밖 경로 접근 차단
- `.xlsx`, `.xlsm`만 허용
- 기본 바인드는 `127.0.0.1:8002`
- write 계열 작업은 workbook lock + `.bak` 백업 사용
- `workbooks` 실제 업무 파일은 Git 추적 제외 권장
- 장기 공개 URL 대신 필요 시에만 외부 노출
