#!/usr/bin/env python3
"""
Desktop UI wrapper for Iconik Storage Locator.

The lookup behavior is intentionally delegated to iconik_locator.py so the GUI,
CLI, and tests share the same conversion logic.
"""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List

import iconik_locator as loc


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
        self.output_var = tk.StringVar(value=str(cfg.get("output") or "S3"))
        self.share_multi_var = tk.StringVar(value=str(cfg.get("multi_share") or cfg.get("multi") or loc.DEFAULT_SHARE_MULTI))
        self.file_multi_var = tk.StringVar(value=str(cfg.get("file_multi") or loc.DEFAULT_FILE_MULTI))
        self.save_var = tk.BooleanVar(value=True)
        self.advanced_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()
        self.after(100, self._drain_queue)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(5, weight=1)

        credentials = ttk.LabelFrame(outer, text="Iconik Credentials", padding=12)
        credentials.grid(row=0, column=0, sticky="ew")
        credentials.columnconfigure(1, weight=1)
        credentials.columnconfigure(3, weight=1)

        ttk.Label(credentials, text="Host").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(credentials, textvariable=self.host_var).grid(row=0, column=1, columnspan=3, sticky="ew")
        ttk.Label(credentials, text="App-ID").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(10, 0))
        ttk.Entry(credentials, textvariable=self.app_id_var).grid(row=1, column=1, sticky="ew", pady=(10, 0))
        ttk.Label(credentials, text="Auth-Token").grid(row=1, column=2, sticky="w", padx=(16, 8), pady=(10, 0))
        ttk.Entry(credentials, textvariable=self.auth_token_var, show="*").grid(row=1, column=3, sticky="ew", pady=(10, 0))

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
        ttk.Label(self.advanced_frame, text="If share has multiple assets").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Combobox(self.advanced_frame, textvariable=self.share_multi_var, values=loc.VALID_MULTI, state="readonly", width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(self.advanced_frame, text="If selected file has multiple online copies").grid(row=0, column=2, sticky="w", padx=(18, 8))
        ttk.Combobox(self.advanced_frame, textvariable=self.file_multi_var, values=loc.VALID_MULTI, state="readonly", width=10).grid(row=0, column=3, sticky="w")
        ttk.Checkbutton(self.advanced_frame, text="Save settings", variable=self.save_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=(10, 0))

        input_box = ttk.LabelFrame(outer, text="Lookup", padding=12)
        input_box.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        input_box.columnconfigure(0, weight=1)
        self.target_text = tk.Text(input_box, height=4, wrap="word")
        self.target_text.grid(row=0, column=0, columnspan=4, sticky="ew")
        self.target_text.insert("1.0", "")
        ttk.Button(input_box, text="Locate", command=self.lookup).grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Button(input_box, text="Copy Output", command=self.copy_output).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(10, 0))
        ttk.Button(input_box, text="Clear", command=self.clear).grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(10, 0))
        ttk.Label(input_box, textvariable=self.status_var).grid(row=1, column=3, sticky="e", pady=(10, 0))

        self.output_text = tk.Text(outer, wrap="word", height=20)
        self.output_text.grid(row=5, column=0, sticky="nsew", pady=(12, 0))
        self.output_text.configure(font=("Menlo", 12))

    def _toggle_advanced(self) -> None:
        if self.advanced_var.get():
            self.advanced_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        else:
            self.advanced_frame.grid_remove()

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

    def _lookup_worker(self, target: str) -> None:
        try:
            host = self.host_var.get().strip().rstrip("/") or "https://app.iconik.io"
            output_mode = loc.normalize_mode(self.output_var.get(), "S3", loc.VALID_OUTPUTS)
            share_multi = loc.normalize_mode(self.share_multi_var.get(), loc.DEFAULT_SHARE_MULTI, loc.VALID_MULTI)
            file_multi = loc.normalize_mode(self.file_multi_var.get(), loc.DEFAULT_FILE_MULTI, loc.VALID_MULTI)
            client = loc.IconikClient(loc.Auth(host=host, app_id=self.app_id_var.get().strip(), auth_token=self.auth_token_var.get().strip()))
            result = loc.resolve_input(client, target, output_mode, share_multi, file_multi)
            if self.save_var.get():
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
            self.result_queue.put(("ok", self._format_result(client, result)))
        except Exception as exc:
            self.result_queue.put(("error", str(exc)))

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
        else:
            self.status_var.set("Error")
            messagebox.showerror("Lookup Failed", str(payload))
        self.after(100, self._drain_queue)

    def copy_output(self) -> None:
        value = self.output_text.get("1.0", "end").strip()
        if not value:
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.status_var.set("Copied")

    def clear(self) -> None:
        self.target_text.delete("1.0", "end")
        self.output_text.delete("1.0", "end")
        self.status_var.set("Ready")


def main() -> None:
    app = LocatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
