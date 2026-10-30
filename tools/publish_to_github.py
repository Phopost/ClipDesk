"""Publish ClipDesk repository and releases to GitHub via REST API.

Supports dynamic versioning, custom commit messages, automated release publishing,
and multi-fallback token resolution.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error

OWNER = "Phopost"
REPO = "ClipDesk"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETUP_EXE = os.path.join(os.path.expanduser("~"), "Desktop", "ClipDesk-Setup.exe")


def get_current_app_version() -> str:
    """Read version from app/version.py if present, otherwise default to 1.0.0."""
    try:
        sys.path.insert(0, ROOT)
        from app.version import __version__
        return __version__
    except Exception:
        return "1.0.0"


def get_token() -> str:
    """Resolve GitHub token from environment or persistent secret paths."""
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok

    candidate_files = [
        os.path.expanduser(r"~\.gemini\antigravity\github_token.txt"),
        os.path.expanduser(r"~\.github_token"),
    ]
    for path in candidate_files:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tok = f.read().strip()
                if tok:
                    return tok
            except Exception:
                pass

    raise SystemExit("Missing GITHUB_TOKEN environment variable or persistent token file.")


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {get_token()}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ClipDesk-Publisher",
    }


def api_request(endpoint: str, data: dict = None, method: str = None) -> dict:
    url = f"https://api.github.com{endpoint}" if endpoint.startswith("/") else endpoint
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=payload, headers=get_headers(), method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"HTTPError {e.code} on {url}: {err_msg}", file=sys.stderr, flush=True)
        raise


def get_all_repo_files():
    exclude_dirs = {
        ".git", ".pytest_cache", "__pycache__", "build", "dist",
        ".venv", "venv", ".clipdesk",
    }
    files_to_commit = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for f in filenames:
            rel = os.path.relpath(os.path.join(dirpath, f), ROOT).replace("\\", "/")
            if rel.startswith("vendor/windows-x64/") and rel.endswith((".exe", ".dll", ".zip", ".7z")):
                continue
            if rel.endswith((".pyc", ".tmp", ".log", ".db")):
                continue
            abs_path = os.path.join(dirpath, f)
            files_to_commit.append((rel, abs_path))

    return files_to_commit


def create_blob(abs_path: str) -> str:
    with open(abs_path, "rb") as fh:
        content = fh.read()
    b64 = base64.b64encode(content).decode("ascii")
    payload = {
        "content": b64,
        "encoding": "base64",
    }
    res = api_request(f"/repos/{OWNER}/{REPO}/git/blobs", payload, method="POST")
    return res["sha"]


def push_code(commit_msg: str) -> str:
    print("Checking repository main branch...", flush=True)
    ref_info = api_request(f"/repos/{OWNER}/{REPO}/git/ref/heads/main")
    base_commit_sha = ref_info["object"]["sha"]
    print(f"Base commit SHA: {base_commit_sha}", flush=True)

    files = get_all_repo_files()
    print(f"Total files to commit: {len(files)}", flush=True)

    tree_items = []
    for i, (rel_path, abs_path) in enumerate(files, 1):
        sha = create_blob(abs_path)
        tree_items.append({
            "path": rel_path,
            "mode": "100644",
            "type": "blob",
            "sha": sha,
        })
        if i % 15 == 0 or i == len(files):
            print(f"Uploaded blobs: {i}/{len(files)} ({rel_path})", flush=True)

    print("Creating Git Tree...", flush=True)
    tree_res = api_request(f"/repos/{OWNER}/{REPO}/git/trees", {
        "tree": tree_items,
    }, method="POST")
    tree_sha = tree_res["sha"]

    print("Creating Git Commit...", flush=True)
    commit_res = api_request(f"/repos/{OWNER}/{REPO}/git/commits", {
        "message": commit_msg,
        "tree": tree_sha,
        "parents": [base_commit_sha],
    }, method="POST")
    new_commit_sha = commit_res["sha"]
    print(f"Git Commit created: {new_commit_sha}", flush=True)

    api_request(f"/repos/{OWNER}/{REPO}/git/refs/heads/main", {
        "sha": new_commit_sha,
        "force": True,
    }, method="PATCH")
    print(f"Successfully pushed code to branch 'main'!", flush=True)
    return new_commit_sha


def create_or_update_release(version: str, title: str, body: str, upload_installer: bool = True):
    tag = f"v{version}" if not version.startswith("v") else version
    print(f"Managing GitHub Release {tag}...", flush=True)

    payload = {
        "tag_name": tag,
        "target_commitish": "main",
        "name": title or f"ClipDesk {tag}",
        "body": body,
        "draft": False,
        "prerelease": False,
    }

    try:
        rel = api_request(f"/repos/{OWNER}/{REPO}/releases/tags/{tag}")
        print(f"Release {tag} exists (ID: {rel['id']}). Updating description...", flush=True)
        rel = api_request(f"/repos/{OWNER}/{REPO}/releases/{rel['id']}", payload, method="PATCH")
    except urllib.error.HTTPError:
        rel = api_request(f"/repos/{OWNER}/{REPO}/releases", payload, method="POST")
        print(f"Created new Release {tag} (ID: {rel['id']})", flush=True)

    release_id = rel["id"]

    if upload_installer and os.path.isfile(SETUP_EXE):
        size_mb = os.path.getsize(SETUP_EXE) / (1024 * 1024)
        print(f"Uploading installer asset: {SETUP_EXE} ({size_mb:.1f} MB)...", flush=True)

        for a in rel.get("assets", []):
            if a["name"] == "ClipDesk-Setup.exe":
                print("Deleting outdated installer asset...", flush=True)
                api_request(f"/repos/{OWNER}/{REPO}/releases/assets/{a['id']}", method="DELETE")

        upload_url = f"https://uploads.github.com/repos/{OWNER}/{REPO}/releases/{release_id}/assets?name=ClipDesk-Setup.exe"
        req = urllib.request.Request(
            upload_url,
            headers={
                "Authorization": f"Bearer {get_token()}",
                "Content-Type": "application/octet-stream",
                "User-Agent": "ClipDesk-Publisher",
            },
            method="POST",
        )
        with open(SETUP_EXE, "rb") as fh:
            req.data = fh.read()

        t0 = time.time()
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            dt = time.time() - t0
            print(f"Asset uploaded in {dt:.1f}s: {data.get('browser_download_url')}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Publish ClipDesk to GitHub")
    parser.add_argument("--version", default=get_current_app_version(), help="Target version tag (e.g. 1.0.0)")
    parser.add_argument("--message", default=None, help="Commit message")
    parser.add_argument("--title", default=None, help="Release title")
    parser.add_argument("--notes", default=None, help="Release notes body")
    parser.add_argument("--skip-installer", action="store_true", help="Do not upload installer")
    args = parser.parse_args()

    ver = args.version
    tag = f"v{ver}" if not ver.startswith("v") else ver

    commit_msg = args.message or f"Update ClipDesk {tag} — Source & Assets"
    title = args.title or f"ClipDesk {tag} — One-Click Setup"
    body = args.notes or (
        f"## 🌊 ClipDesk {tag}\n\n"
        f"อัปเดตเวอร์ชัน {tag} ล่าสุดของ ClipDesk พร้อมฟังก์ชันการทำงานครบถ้วน\n\n"
        f"- รองรับดาวน์โหลด YouTube & TikTok เต็มสปีด 16x Multi-Fragment\n"
        f"- Sky-Blue Wave Glass UI & Animations\n"
        f"- ฝังโลโก้และไอคอนแอปพลิเคชันอย่างสมบูรณ์\n\n"
        f"### 📥 ดาวน์โหลดตัวติดตั้ง:\n"
        f"- ดาวน์โหลด `ClipDesk-Setup.exe` ด้านล่าง แล้วดับเบิลคลิกเพื่อเริ่มใช้งานได้ทันที"
    )

    push_code(commit_msg)
    create_or_update_release(ver, title, body, upload_installer=not args.skip_installer)


if __name__ == "__main__":
    main()
