#!/usr/bin/env python3
"""
Desktop UI wrapper for Iconik Storage Locator.

The lookup behavior is intentionally delegated to iconik_locator.py so the GUI,
CLI, and tests share the same conversion logic.
"""

from __future__ import annotations

import json
import csv
import queue
import re
import threading
import tkinter as tk
import webbrowser
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Sequence

import iconik_locator as loc

ICONIK_API_DOCS_URL = "https://app.iconik.io/docs/api.html#setup-your-access"


class LocatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{loc.APP_NAME} {loc.VERSION}")
        self.geometry("980x720")
        self.minsize(780, 560)

        self.result_queue: "queue.Queue[tuple[str, Any]]" = queue.Queue()
        cfg = loc.ConfigStore.load()

        self.host_var = tk.StringVar(value=str(cfg.get("host") or "https://app.iconik.io"))
        self.app_id_var = tk.StringVar(value=loc.KeychainStore.get(loc.KEYCHAIN_ACCOUNT_APP_ID))
        self.auth_token_var = tk.StringVar(value=loc.KeychainStore.get(loc.KEYCHAIN_ACCOUNT_AUTH_TOKEN))
        saved_output = cfg.get("output") if cfg.get("config_version") == loc.VERSION else None
        self.output_var = tk.StringVar(value=str(saved_output or "S3"))
        self.share_multi_var = tk.StringVar(value=str(cfg.get("multi_share") or cfg.get("multi") or loc.DEFAULT_SHARE_MULTI))
        self.file_multi_var = tk.StringVar(value=str(cfg.get("file_multi") or loc.DEFAULT_FILE_MULTI))
        self.save_var = tk.BooleanVar(value=True)
        self.advanced_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        self.bulk_inputs: List[str] = []
        self.bulk_rows: List[Dict[str, str]] = []

        self._build_ui()
        self.after(100, self._drain_queue)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(5, weight=1)

        credentials = ttk.LabelFrame(outer, text="Iconik API Access", padding=12)
        credentials.grid(row=0, column=0, sticky="ew")
        credentials.columnconfigure(1, weight=1)
        credentials.columnconfigure(3, weight=1)

        ttk.Label(credentials, text="App-ID").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(credentials, textvariable=self.app_id_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(credentials, text="Auth-Token").grid(row=0, column=2, sticky="w", padx=(16, 8))
        ttk.Entry(credentials, textvariable=self.auth_token_var, show="*").grid(row=0, column=3, sticky="ew")
        ttk.Label(
            credentials,
            text="Ask your Iconik admin for an App-ID and Auth-Token with asset/file lookup access.",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))
        credential_actions = ttk.Frame(credentials)
        credential_actions.grid(row=1, column=3, sticky="e", pady=(10, 0))
        ttk.Button(credential_actions, text="Test API Access", command=self.test_api_access).grid(row=0, column=0, sticky="e", padx=(0, 8))
        ttk.Button(credential_actions, text="Need these?", command=self._open_credential_help).grid(row=0, column=1, sticky="e")

        options = ttk.Frame(outer)
        options.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        options.columnconfigure(2, weight=1)

        ttk.Label(options, text="Output").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Combobox(options, textvariable=self.output_var, values=loc.VALID_OUTPUTS, state="readonly", width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(options, text="Default: show every asset represented by the Iconik URL.").grid(row=0, column=2, sticky="w", padx=(18, 8))
        ttk.Checkbutton(options, text="Advanced settings", variable=self.advanced_var, command=self._toggle_advanced).grid(row=0, column=3, sticky="e")

        self.advanced_frame = ttk.LabelFrame(outer, text="Advanced Settings", padding=12)
        self.advanced_frame.columnconfigure(1, weight=1)
        self.advanced_frame.columnconfigure(3, weight=1)
        ttk.Label(self.advanced_frame, text="Iconik host").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(self.advanced_frame, textvariable=self.host_var).grid(row=0, column=1, columnspan=3, sticky="ew")
        ttk.Label(self.advanced_frame, text="If share has multiple assets").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(10, 0))
        ttk.Combobox(self.advanced_frame, textvariable=self.share_multi_var, values=loc.VALID_MULTI, state="readonly", width=10).grid(row=1, column=1, sticky="w", pady=(10, 0))
        ttk.Label(self.advanced_frame, text="If selected file has multiple online copies").grid(row=1, column=2, sticky="w", padx=(18, 8), pady=(10, 0))
        ttk.Combobox(self.advanced_frame, textvariable=self.file_multi_var, values=loc.VALID_MULTI, state="readonly", width=10).grid(row=1, column=3, sticky="w", pady=(10, 0))
        ttk.Checkbutton(self.advanced_frame, text="Save credentials and settings locally", variable=self.save_var).grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))

        tabs = ttk.Notebook(outer)
        tabs.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        outer.rowconfigure(3, weight=1)

        single_tab = ttk.Frame(tabs, padding=12)
        single_tab.columnconfigure(0, weight=1)
        single_tab.rowconfigure(2, weight=0, minsize=46)
        tabs.add(single_tab, text="Single Lookup")

        ttk.Label(single_tab, text="Lookup input").grid(row=0, column=0, sticky="w")
        self.target_text = tk.Text(single_tab, height=4, wrap="word")
        self.target_text.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(4, 0))
        self.target_text.insert("1.0", "")
        single_actions = ttk.Frame(single_tab)
        single_actions.grid(row=2, column=0, columnspan=5, sticky="ew", pady=(12, 10))
        ttk.Button(single_actions, text="Locate", command=self.lookup).grid(row=0, column=0, sticky="w", ipady=2)
        ttk.Button(single_actions, text="Copy S3 Only", command=self.copy_s3_output).grid(row=0, column=1, sticky="w", padx=(8, 0), ipady=2)
        ttk.Button(single_actions, text="Copy All Text", command=self.copy_output).grid(row=0, column=2, sticky="w", padx=(8, 0), ipady=2)
        ttk.Button(single_actions, text="Clear", command=self.clear).grid(row=0, column=3, sticky="w", padx=(8, 0), ipady=2)
        ttk.Label(single_actions, textvariable=self.status_var).grid(row=0, column=4, sticky="e", padx=(16, 0), pady=(2, 0))
        single_actions.columnconfigure(4, weight=1)

        self.output_text = tk.Text(single_tab, wrap="word", height=18)
        self.output_text.grid(row=3, column=0, columnspan=5, sticky="nsew", pady=(12, 0))
        self.output_text.configure(font=("Menlo", 12))
        single_tab.rowconfigure(3, weight=1)

        bulk_tab = ttk.Frame(tabs, padding=12)
        bulk_tab.columnconfigure(0, weight=1)
        bulk_tab.rowconfigure(3, weight=1)
        tabs.add(bulk_tab, text="Bulk Lookup")

        ttk.Label(bulk_tab, text="Paste one Iconik URL, share URL, UUID, or s3:// URI per line. CSV/XLSX files must use header: iconik_url").grid(row=0, column=0, sticky="w")
        self.bulk_text = tk.Text(bulk_tab, height=8, wrap="word")
        self.bulk_text.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        bulk_actions = ttk.Frame(bulk_tab)
        bulk_actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(bulk_actions, text="Run Bulk Lookup", command=self.run_bulk_lookup).grid(row=0, column=0, sticky="w")
        ttk.Button(bulk_actions, text="Load CSV/XLSX", command=self.load_bulk_file).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(bulk_actions, text="Export CSV", command=self.export_bulk_csv).grid(row=0, column=2, sticky="w", padx=(8, 0))
        ttk.Button(bulk_actions, text="Export XLSX", command=self.export_bulk_xlsx).grid(row=0, column=3, sticky="w", padx=(8, 0))
        ttk.Button(bulk_actions, text="Copy S3 Only", command=self.copy_bulk_s3_output).grid(row=0, column=4, sticky="w", padx=(8, 0))
        ttk.Button(bulk_actions, text="Clear", command=self.clear_bulk).grid(row=0, column=5, sticky="w", padx=(8, 0))
        self.bulk_output_text = tk.Text(bulk_tab, wrap="word", height=18)
        self.bulk_output_text.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        self.bulk_output_text.configure(font=("Menlo", 12))

    def _toggle_advanced(self) -> None:
        if self.advanced_var.get():
            self.advanced_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        else:
            self.advanced_frame.grid_remove()

    def _open_credential_help(self) -> None:
        webbrowser.open(ICONIK_API_DOCS_URL)

    def lookup(self) -> None:
        target = self.target_text.get("1.0", "end").strip()
        if not target:
            messagebox.showerror("Missing Input", "Paste an Iconik link, share link, asset UUID, or S3 URI.")
            return
        app_id = self.app_id_var.get().strip()
        auth_token = self.auth_token_var.get().strip()
        if not app_id or not auth_token:
            messagebox.showerror("Missing Credentials", "App-ID and Auth-Token are required.")
            return

        self.status_var.set("Looking up...")
        self.output_text.delete("1.0", "end")
        worker = threading.Thread(target=self._lookup_worker, args=(target,), daemon=True)
        worker.start()

    def test_api_access(self) -> None:
        app_id = self.app_id_var.get().strip()
        auth_token = self.auth_token_var.get().strip()
        if not app_id or not auth_token:
            messagebox.showerror("Missing Credentials", "App-ID and Auth-Token are required.")
            return
        self.status_var.set("Testing API access...")
        self.output_text.delete("1.0", "end")
        worker = threading.Thread(target=self._test_api_worker, daemon=True)
        worker.start()

    def _test_api_worker(self) -> None:
        try:
            host = self.host_var.get().strip().rstrip("/") or "https://app.iconik.io"
            client = loc.IconikClient(loc.Auth(host=host, app_id=self.app_id_var.get().strip(), auth_token=self.auth_token_var.get().strip()))
            data = client.get("/API/files/v1/storages/?page=1&per_page=1")
            total = data.get("total") if isinstance(data, dict) else None
            lines = [
                "API access test passed.",
                "",
                "Iconik accepted the App-ID and Auth-Token.",
                "The token can access the files/storages API used by this locator.",
                f"Host: {host}",
            ]
            if total is not None:
                lines.append(f"Visible storage records: {total}")
            self.result_queue.put(("ok", "\n".join(lines)))
        except Exception as exc:
            self.result_queue.put(("error", loc.friendly_error(exc)))

    def _lookup_worker(self, target: str) -> None:
        try:
            host = self.host_var.get().strip().rstrip("/") or "https://app.iconik.io"
            output_mode = loc.normalize_mode(self.output_var.get(), "S3", loc.VALID_OUTPUTS)
            share_multi = loc.normalize_mode(self.share_multi_var.get(), loc.DEFAULT_SHARE_MULTI, loc.VALID_MULTI)
            file_multi = loc.normalize_mode(self.file_multi_var.get(), loc.DEFAULT_FILE_MULTI, loc.VALID_MULTI)
            client = loc.IconikClient(loc.Auth(host=host, app_id=self.app_id_var.get().strip(), auth_token=self.auth_token_var.get().strip()))
            result = loc.resolve_input(client, target, output_mode, share_multi, file_multi)
            self._save_settings(host, output_mode, share_multi, file_multi)
            self.result_queue.put(("ok", self._format_result(client, result)))
        except Exception as exc:
            self.result_queue.put(("error", loc.friendly_error(exc)))

    def _save_settings(self, host: str, output_mode: str, share_multi: str, file_multi: str) -> None:
        if not self.save_var.get():
            return
        loc.ConfigStore.update(
            host=host,
            config_version=loc.VERSION,
            output=output_mode,
            multi_share=share_multi,
            multi=share_multi,
            file_multi=file_multi,
        )
        loc.KeychainStore.set(loc.KEYCHAIN_ACCOUNT_APP_ID, self.app_id_var.get().strip())
        loc.KeychainStore.set(loc.KEYCHAIN_ACCOUNT_AUTH_TOKEN, self.auth_token_var.get().strip())

    def _format_result(self, client: loc.IconikClient, result: Dict[str, Any]) -> str:
        if result["type"] == "collection":
            lines = [f"Collection: {result['id']}", f"Total items: {result['total']}", "", "First items:"]
            for obj in result.get("objects") or []:
                lines.append(f"- {obj.get('object_type', 'Item')}: {obj.get('title', 'Untitled')}")
            return "\n".join(lines)

        if result["type"] == "reverse_list":
            lines = [f"S3 URI: {result['id']}", ""]
            objects = result.get("results") or []
            if not objects:
                return "\n".join(lines + ["No Iconik assets found matching that storage path."])
            for idx, obj in enumerate(objects, 1):
                asset_id = obj.get("id")
                lines.extend([
                    f"Asset {idx}: {obj.get('title') or '(untitled)'}",
                    str(asset_id),
                    f"{client.auth.host.rstrip('/')}/asset/{asset_id}",
                    "",
                ])
            return "\n".join(lines).strip()

        results: List[Dict[str, Any]] = list(result.get("results") or [])
        lines = []
        if len(results) > 1:
            lines.extend([
                f"This Iconik URL resolved to {len(results)} assets.",
                "Each asset output is listed below.",
                "",
            ])
        locations = []
        for item in results:
            locations.extend(item.get("locations") or [])
        if locations:
            lines.append("Located URIs")
            lines.extend(loc.location_lines(locations))
            lines.append("")
        for idx, item in enumerate(results, 1):
            label = f"Asset {idx}" if len(results) > 1 else "Asset"
            lines.extend([
                label,
                f"{item.get('asset_title') or '(untitled)'}",
                str(item.get("asset_id")),
                f"Selected file: {item.get('file_name') or '(unnamed)'}",
                "",
            ])
            paths = item.get("paths") or []
            lines.append("Output" if len(paths) == 1 else f"Outputs ({len(paths)})")
            lines.extend(str(path) for path in paths)
            lines.append("")
        return "\n".join(lines).strip()

    def _drain_queue(self) -> None:
        try:
            kind, payload = self.result_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._drain_queue)
            return
        if kind == "ok":
            self.output_text.delete("1.0", "end")
            self.output_text.insert("1.0", str(payload))
            self.status_var.set("Done")
        elif kind == "bulk_progress":
            self.bulk_output_text.delete("1.0", "end")
            self.bulk_output_text.insert("1.0", str(payload))
        elif kind == "bulk_ok":
            self.bulk_rows = list(payload)
            self.bulk_output_text.delete("1.0", "end")
            self.bulk_output_text.insert("1.0", self._format_bulk_rows(self.bulk_rows))
            self.status_var.set(f"Bulk done: {len(self.bulk_rows)} row(s)")
        elif kind == "bulk_error":
            self.bulk_output_text.delete("1.0", "end")
            self.bulk_output_text.insert("1.0", f"Bulk lookup failed\n\n{payload}")
            self.status_var.set("Error")
        else:
            self.status_var.set("Error")
            messagebox.showerror("Lookup Failed", str(payload))
        self.after(100, self._drain_queue)

    def _format_bulk_rows(self, rows: Sequence[Dict[str, str]]) -> str:
        if not rows:
            return "No bulk results."
        lines = [f"Bulk results ({len(rows)} row(s))", ""]
        for row in rows:
            lines.append(f"{row.get('status', '')}: {row.get('input', '')}")
            if row.get("asset_title") or row.get("asset_id"):
                lines.append(f"  Asset: {row.get('asset_title', '')} {row.get('asset_id', '')}".rstrip())
            if row.get("file_name"):
                lines.append(f"  File: {row['file_name']}")
            if row.get("output"):
                lines.append(f"  Output: {row['output']}")
            if row.get("iconik_url"):
                lines.append(f"  Iconik URL: {row['iconik_url']}")
            if row.get("error"):
                lines.append(f"  Error: {row['error']}")
            lines.append("")
        return "\n".join(lines).strip()

    def copy_output(self) -> None:
        value = self.output_text.get("1.0", "end").strip()
        if not value:
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.status_var.set("Copied")

    def copy_s3_output(self) -> None:
        self._copy_lines(re.findall(r"s3://[^\s|]+", self.output_text.get("1.0", "end")))

    def copy_bulk_s3_output(self) -> None:
        rows = self.bulk_rows or []
        outputs = [row["output"] for row in rows if row.get("output", "").startswith("s3://")]
        if not outputs:
            outputs = re.findall(r"s3://[^\s|]+", self.bulk_output_text.get("1.0", "end"))
        self._copy_lines(outputs)

    def _copy_lines(self, lines: Sequence[str]) -> None:
        clean = [line.strip() for line in lines if line.strip()]
        if not clean:
            self.status_var.set("No S3 output to copy")
            return
        self.clipboard_clear()
        self.clipboard_append("\n".join(clean))
        self.status_var.set(f"Copied {len(clean)} S3 output(s)")

    def run_bulk_lookup(self) -> None:
        values = self._bulk_inputs_from_text()
        if not values:
            messagebox.showerror("Missing Input", "Paste one value per line or load a CSV/XLSX file with header: iconik_url")
            return
        if not self.app_id_var.get().strip() or not self.auth_token_var.get().strip():
            messagebox.showerror("Missing Credentials", "App-ID and Auth-Token are required.")
            return
        self.bulk_inputs = values
        self.bulk_rows = []
        self.bulk_output_text.delete("1.0", "end")
        self.bulk_output_text.insert("1.0", f"Running {len(values)} lookup(s)...")
        self.status_var.set("Running bulk lookup...")
        threading.Thread(target=self._bulk_worker, args=(values,), daemon=True).start()

    def _bulk_worker(self, values: Sequence[str]) -> None:
        rows: List[Dict[str, str]] = []
        try:
            host = self.host_var.get().strip().rstrip("/") or "https://app.iconik.io"
            output_mode = loc.normalize_mode(self.output_var.get(), "S3", loc.VALID_OUTPUTS)
            share_multi = loc.normalize_mode(self.share_multi_var.get(), loc.DEFAULT_SHARE_MULTI, loc.VALID_MULTI)
            file_multi = loc.normalize_mode(self.file_multi_var.get(), loc.DEFAULT_FILE_MULTI, loc.VALID_MULTI)
            client = loc.IconikClient(loc.Auth(host=host, app_id=self.app_id_var.get().strip(), auth_token=self.auth_token_var.get().strip()))
            self._save_settings(host, output_mode, share_multi, file_multi)
            for idx, raw in enumerate(values, 1):
                try:
                    data = loc.resolve_input(client, raw, output_mode, share_multi, file_multi)
                    rows.extend(self._rows_from_result(client, raw, data))
                except Exception as exc:
                    rows.append(self._bulk_row(raw, status="ERROR", error=loc.friendly_error(exc)))
                self.result_queue.put(("bulk_progress", f"Processed {idx}/{len(values)} lookup(s)..."))
            self.result_queue.put(("bulk_ok", rows))
        except Exception as exc:
            self.result_queue.put(("bulk_error", loc.friendly_error(exc)))

    def _rows_from_result(self, client: loc.IconikClient, raw: str, data: Dict[str, Any]) -> List[Dict[str, str]]:
        if data["type"] == "reverse_list":
            objects = data.get("results") or []
            if not objects:
                return [self._bulk_row(raw, status="NO_MATCH")]
            return [
                self._bulk_row(
                    raw,
                    status="OK",
                    asset_id=str(obj.get("id") or ""),
                    asset_title=str(obj.get("title") or ""),
                    iconik_url=f"{client.auth.host.rstrip('/')}/asset/{obj.get('id')}",
                )
                for obj in objects
            ]
        if data["type"] == "collection":
            return [self._bulk_row(raw, status="COLLECTION", error=f"Collection contains {data.get('total', 0)} item(s); bulk storage lookup expects asset/share URLs, UUIDs, or s3:// URIs.")]
        rows: List[Dict[str, str]] = []
        for result in data.get("results") or []:
            paths = result.get("paths") or []
            if not paths:
                rows.append(self._bulk_row(raw, status="NO_OUTPUT", asset_id=str(result.get("asset_id") or ""), asset_title=str(result.get("asset_title") or ""), file_name=str(result.get("file_name") or "")))
            for path in paths:
                rows.append(self._bulk_row(raw, status="OK", asset_id=str(result.get("asset_id") or ""), asset_title=str(result.get("asset_title") or ""), file_name=str(result.get("file_name") or ""), output=str(path)))
        return rows or [self._bulk_row(raw, status="NO_OUTPUT")]

    def _bulk_row(self, raw: str, status: str, asset_id: str = "", asset_title: str = "", file_name: str = "", output: str = "", iconik_url: str = "", error: str = "") -> Dict[str, str]:
        return {
            "input": raw,
            "status": status,
            "asset_id": asset_id,
            "asset_title": asset_title,
            "file_name": file_name,
            "output": output,
            "iconik_url": iconik_url,
            "error": error,
        }

    def _bulk_inputs_from_text(self) -> List[str]:
        values = []
        for line in self.bulk_text.get("1.0", "end").splitlines():
            value = line.strip().strip('"').strip("'")
            if value and value.lower() != "iconik_url":
                values.append(value)
        return values

    def load_bulk_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Spreadsheet files", "*.csv *.xlsx"), ("CSV files", "*.csv"), ("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            values = self._read_bulk_file(path)
        except Exception as exc:
            messagebox.showerror("Could Not Load File", str(exc))
            return
        self.bulk_text.delete("1.0", "end")
        self.bulk_text.insert("1.0", "\n".join(values))
        self.status_var.set(f"Loaded {len(values)} input(s)")

    def _read_bulk_file(self, path: str) -> List[str]:
        if path.lower().endswith(".csv"):
            with open(path, newline="", encoding="utf-8-sig") as f:
                rows = csv.DictReader(f)
                if not rows.fieldnames or "iconik_url" not in rows.fieldnames:
                    raise ValueError("CSV must include header: iconik_url")
                return [str(row.get("iconik_url") or "").strip() for row in rows if str(row.get("iconik_url") or "").strip()]
        if path.lower().endswith(".xlsx"):
            return self._read_xlsx_iconik_url(path)
        raise ValueError("Use a CSV or XLSX file with header: iconik_url")

    def _read_xlsx_iconik_url(self, path: str) -> List[str]:
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        with zipfile.ZipFile(path) as zf:
            shared: List[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for item in root.findall("m:si", ns):
                    shared.append("".join(text.text or "" for text in item.findall(".//m:t", ns)))
            sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall(".//m:row", ns):
            values = []
            for cell in row.findall("m:c", ns):
                raw = cell.findtext("m:v", default="", namespaces=ns)
                values.append(shared[int(raw)] if cell.get("t") == "s" and raw else raw)
            rows.append(values)
        if not rows or "iconik_url" not in rows[0]:
            raise ValueError("XLSX first sheet must include header: iconik_url")
        idx = rows[0].index("iconik_url")
        return [str(row[idx]).strip() for row in rows[1:] if len(row) > idx and str(row[idx]).strip()]

    def export_bulk_csv(self) -> None:
        if not self.bulk_rows:
            messagebox.showerror("No Results", "Run a bulk lookup before exporting.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile=f"iconik_locator_results_{loc.VERSION}.csv")
        if not path:
            return
        fields = ["input", "status", "asset_id", "asset_title", "file_name", "output", "iconik_url", "error"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.bulk_rows)
        self.status_var.set(f"Exported {len(self.bulk_rows)} row(s)")

    def export_bulk_xlsx(self) -> None:
        if not self.bulk_rows:
            messagebox.showerror("No Results", "Run a bulk lookup before exporting.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")], initialfile=f"iconik_locator_results_{loc.VERSION}.xlsx")
        if not path:
            return
        fields = ["input", "status", "asset_id", "asset_title", "file_name", "output", "iconik_url", "error"]
        self._write_xlsx(path, fields, self.bulk_rows)
        self.status_var.set(f"Exported {len(self.bulk_rows)} row(s)")

    def _write_xlsx(self, path: str, fields: Sequence[str], rows: Sequence[Dict[str, str]]) -> None:
        all_rows = [list(fields)] + [[str(row.get(field, "")) for field in fields] for row in rows]

        def cell_ref(row_idx: int, col_idx: int) -> str:
            letters = ""
            col = col_idx
            while col:
                col, rem = divmod(col - 1, 26)
                letters = chr(65 + rem) + letters
            return f"{letters}{row_idx}"

        sheet_rows = []
        for row_idx, row in enumerate(all_rows, 1):
            cells = []
            for col_idx, value in enumerate(row, 1):
                ref = cell_ref(row_idx, col_idx)
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
            sheet_rows.append(f'<row r="{row_idx}">{"".join(cells)}</row>')
        sheet_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(sheet_rows)}</sheetData>'
            '</worksheet>'
        )
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                '</Types>'
            ))
            zf.writestr("_rels/.rels", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                '</Relationships>'
            ))
            zf.writestr("xl/workbook.xml", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="Iconik Results" sheetId="1" r:id="rId1"/></sheets>'
                '</workbook>'
            ))
            zf.writestr("xl/_rels/workbook.xml.rels", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                '</Relationships>'
            ))
            zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    def clear_bulk(self) -> None:
        self.bulk_text.delete("1.0", "end")
        self.bulk_output_text.delete("1.0", "end")
        self.bulk_rows = []
        self.status_var.set("Ready")

    def clear(self) -> None:
        self.target_text.delete("1.0", "end")
        self.output_text.delete("1.0", "end")
        self.status_var.set("Ready")


def main() -> None:
    app = LocatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
