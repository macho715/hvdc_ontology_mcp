# HVDC Tool Contract

This document defines the v1 public contract for the structured `hvdc_*` analysis tools.

## Input shape policy

- File-based tools accept exactly one source:
  - `file` for ChatGPT / remote MCP usage
  - `local_path` for local `stdio` execution
- `file` uses the `FileParam` shape:

```json
{
  "file_id": "string",
  "download_url": "https://example.com/file.xlsx"
}
```

- `sandbox:/...` is not a valid remote `download_url`
- `column_map` is an override layer on top of semantic alias detection
- `sheet_name` is optional and defaults to the first worksheet for `.xlsx`

## Result shape policy

- All analysis tools return `structuredContent + content`.
- `structuredContent` is the authoritative machine-readable payload.
- `content` is a short Markdown summary intended for humans and chat transcripts.
- Markdown rendering remains in `hvdc_ops/reports.py`.
- Business logic remains in `hvdc_ops/rules.py`.

## Tool outputs

### `hvdc_analyze_shipment_case`

- Input: inline `shipment` or `file` / `local_path`
- Row selection:
  - `shipment_id`
  - or `row_number`
- Structured keys:
  - `normalized_case`
  - `flow_assessment`
  - `zero_gates`
  - `kpi_checks`
  - `verdict`
  - `input_source`
  - `markdown_summary`

### `hvdc_render_backlog_upload_widget`

- Purpose: prepare the ChatGPT widget for CSV/XLSX upload
- Input:
  - `snapshot_name`
  - `sheet_name`
  - `column_map`
- Structured keys:
  - `title`
  - `instructions`
  - `accepted_extensions`
  - `defaults.snapshot_name`
  - `defaults.sheet_name`
  - `defaults.column_map`
  - `tool_name`
  - `widget_uri`

### `hvdc_analyze_backlog_batch`

- Input: `file` / `local_path`
- Optional inputs:
  - `sheet_name`
  - `column_map`
  - `snapshot_name`
- Structured keys:
  - `snapshot_name`
  - `source`
  - `totals`
  - `by_status`
  - `by_site`
  - `by_mode`
  - `hotspots`
  - `breaches`
  - `zero_candidates`
  - `zero_candidate_ids`
  - `markdown_report`

### `hvdc_zero_gate_check`

- Input: one structured operation context
- Important semantic inputs:
  - `destination`
  - `gross_weight_tons`
  - `weather_alert`
  - `boe_complete`
  - `ebl_match`
  - `fanr_ready`
  - `ecas_ready`
  - `cicpa_ready`
  - `fra_ready`
  - `dot_ready`
  - `mosb_utilization_pct`
- Structured keys:
  - `gate_results`
  - `blocking_actions`
  - `warning_actions`
  - `verdict`
  - `markdown_summary`

### `hvdc_compare_snapshots`

- Input: `baseline_snapshot`, `candidate_snapshot`
- Structured keys:
  - `baseline_snapshot`
  - `candidate_snapshot`
  - `delta_totals`
  - `delta_by_status`
  - `delta_by_site`
  - `delta_by_mode`
  - `new_zero_candidates`
  - `resolved_zero_candidates`
  - `markdown_report`

### `hvdc_mcp_self_test`

- Input: `target`, `include_tool_calls`
- Structured keys:
  - `status`
  - `connector_url`
  - `public_base_url`
  - `checks`
  - `recommendations`
  - `markdown_summary`

## Widget handoff rules

- ChatGPT file uploads must flow through `hvdc_render_backlog_upload_widget`.
- The widget converts uploads into a temporary `http/https` `download_url`.
- `sandbox:/...` paths are not readable by Railway or other remote MCP hosts.
- `local_path` is allowed only in `stdio` execution.
- Widget defaults may prefill `snapshot_name`, `sheet_name`, and `column_map`, but the authoritative snapshot is created only by `hvdc_analyze_backlog_batch`.
- Default handoff flow:
  - upload file in widget
  - widget gets temporary `download_url`
  - widget calls `hvdc_analyze_backlog_batch`
  - batch tool persists `snapshot_name`
