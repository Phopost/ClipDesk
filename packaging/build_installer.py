"""Build a one-click standalone Windows installer (ClipDesk-Setup.exe).

How it works:
1. Compresses `dist/ClipDesk` into a compact `payload.zip` archive.
2. Generates a lightweight C# WinForms one-click installer stub (`InstallerStub.cs`)
   and compiles it with the built-in Windows .NET compiler (`csc.exe`) with the
   ClipDesk icon and zero UAC elevation required (`asInvoker`).
3. Appends `payload.zip` + 8-byte trailer (`[zip_offset:int64]`) + 8-byte magic
   (`CLIPDESK`) to the compiled stub executable, producing a single standalone
   `ClipDesk-Setup.exe` on the user's Desktop.

When the user double-clicks `ClipDesk-Setup.exe` (or runs with `--silent`):
- Extracts all files to `%LocalAppData%\\Programs\\ClipDesk`
- Creates a Desktop shortcut (`ClipDesk.lnk`) and Start Menu shortcut
- Launches `ClipDesk.exe` immediately!
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_APP_DIR = os.path.join(ROOT, "dist", "ClipDesk")
ICON_PATH = os.path.join(ROOT, "app", "assets", "icons", "clipdesk.ico")
DESKTOP_SETUP_EXE = os.path.join(os.path.expanduser("~"), "Desktop", "ClipDesk-Setup.exe")
MAGIC = b"CLIPDESK"

CSHARP_INSTALLER_SOURCE = r"""
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("ClipDesk Setup")]
[assembly: AssemblyDescription("ClipDesk One-Click Installer")]
[assembly: AssemblyProduct("ClipDesk")]
[assembly: AssemblyVersion("1.0.0.0")]

namespace ClipDeskSetup
{
    static class Program
    {
        [STAThread]
        static int Main(string[] args)
        {
            bool silent = false;
            bool noLaunch = false;
            string customTarget = null;

            foreach (string a in args)
            {
                if (a.Equals("--silent", StringComparison.OrdinalIgnoreCase) ||
                    a.Equals("/S", StringComparison.OrdinalIgnoreCase))
                    silent = true;
                else if (a.Equals("--no-launch", StringComparison.OrdinalIgnoreCase))
                    noLaunch = true;
                else if (a.StartsWith("--target=", StringComparison.OrdinalIgnoreCase))
                    customTarget = a.Substring("--target=".Length).Trim('"');
            }

            string installDir = customTarget ?? Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Programs",
                "ClipDesk"
            );

            if (silent)
            {
                return RunSilentInstall(installDir, !noLaunch);
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            using (var form = new InstallerForm(installDir, !noLaunch))
            {
                Application.Run(form);
                return form.ExitCode;
            }
        }

        public static int RunSilentInstall(string installDir, bool launchAfter)
        {
            try
            {
                KillRunningClipDesk();
                ExtractPayload(installDir, null);
                CreateShortcuts(installDir);
                if (launchAfter)
                {
                    string exePath = Path.Combine(installDir, "ClipDesk.exe");
                    if (File.Exists(exePath))
                    {
                        Process.Start(new ProcessStartInfo(exePath) { WorkingDirectory = installDir });
                    }
                }
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("Install error: " + ex.Message);
                return 1;
            }
        }

        public static void KillRunningClipDesk()
        {
            try
            {
                foreach (var p in Process.GetProcessesByName("ClipDesk"))
                {
                    try { p.Kill(); p.WaitForExit(3000); } catch { }
                }
            }
            catch { }
        }

        public static void ExtractPayload(string installDir, Action<int, string> onProgress)
        {
            string selfPath = Process.GetCurrentProcess().MainModule.FileName;
            using (FileStream fs = new FileStream(selfPath, FileMode.Open, FileAccess.Read, FileShare.Read))
            {
                if (fs.Length < 16)
                    throw new InvalidDataException("Installer payload is missing.");

                fs.Seek(-16, SeekOrigin.End);
                byte[] footer = new byte[16];
                fs.Read(footer, 0, 16);

                long zipOffset = BitConverter.ToInt64(footer, 0);
                string magic = Encoding.ASCII.GetString(footer, 8, 8);
                if (magic != "CLIPDESK" || zipOffset <= 0 || zipOffset >= fs.Length - 16)
                    throw new InvalidDataException("Invalid installer signature.");

                long zipLength = (fs.Length - 16) - zipOffset;
                fs.Seek(zipOffset, SeekOrigin.Begin);

                using (var subStream = new SubReadStream(fs, zipOffset, zipLength))
                using (var archive = new ZipArchive(subStream, ZipArchiveMode.Read))
                {
                    int total = Math.Max(1, archive.Entries.Count);
                    int current = 0;

                    Directory.CreateDirectory(installDir);

                    foreach (var entry in archive.Entries)
                    {
                        current++;
                        string relPath = entry.FullName.Replace('/', Path.DirectorySeparatorChar);
                        string fullPath = Path.Combine(installDir, relPath);

                        if (string.IsNullOrEmpty(entry.Name))
                        {
                            Directory.CreateDirectory(fullPath);
                            continue;
                        }

                        string parent = Path.GetDirectoryName(fullPath);
                        if (!string.IsNullOrEmpty(parent))
                            Directory.CreateDirectory(parent);

                        entry.ExtractToFile(fullPath, true);

                        if (onProgress != null && (current % 5 == 0 || current == total))
                        {
                            int pct = (int)((current * 100L) / total);
                            onProgress(pct, entry.Name);
                        }
                    }
                }
            }
        }

        public static void CreateShortcuts(string installDir)
        {
            string exePath = Path.Combine(installDir, "ClipDesk.exe");
            if (!File.Exists(exePath)) return;

            try
            {
                string desktopDir = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                CreateLnk(Path.Combine(desktopDir, "ClipDesk.lnk"), exePath, installDir, "ClipDesk — ดาวน์โหลดวิดีโอและเสียงจาก YouTube & TikTok");

                string startMenuDir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.Programs),
                    "ClipDesk"
                );
                Directory.CreateDirectory(startMenuDir);
                CreateLnk(Path.Combine(startMenuDir, "ClipDesk.lnk"), exePath, installDir, "ClipDesk — ดาวน์โหลดวิดีโอและเสียงจาก YouTube & TikTok");
            }
            catch { }
        }

        private static void CreateLnk(string lnkPath, string targetExe, string workDir, string description)
        {
            Type shellType = Type.GetTypeFromProgID("WScript.Shell");
            if (shellType == null) return;
            dynamic shell = Activator.CreateInstance(shellType);
            dynamic shortcut = shell.CreateShortcut(lnkPath);
            shortcut.TargetPath = targetExe;
            shortcut.WorkingDirectory = workDir;
            shortcut.Description = description;
            shortcut.IconLocation = targetExe + ",0";
            shortcut.Save();
        }
    }

    internal sealed class SubReadStream : Stream
    {
        private readonly Stream _baseStream;
        private readonly long _start;
        private readonly long _length;
        private long _position;

        public SubReadStream(Stream baseStream, long start, long length)
        {
            _baseStream = baseStream;
            _start = start;
            _length = length;
            _position = 0;
            _baseStream.Seek(_start, SeekOrigin.Begin);
        }

        public override bool CanRead { get { return true; } }
        public override bool CanSeek { get { return true; } }
        public override bool CanWrite { get { return false; } }
        public override long Length { get { return _length; } }

        public override long Position
        {
            get { return _position; }
            set { Seek(value, SeekOrigin.Begin); }
        }

        public override void Flush() { }

        public override int Read(byte[] buffer, int offset, int count)
        {
            long remaining = _length - _position;
            if (remaining <= 0) return 0;
            if (count > remaining) count = (int)remaining;
            _baseStream.Seek(_start + _position, SeekOrigin.Begin);
            int read = _baseStream.Read(buffer, offset, count);
            _position += read;
            return read;
        }

        public override long Seek(long offset, SeekOrigin origin)
        {
            long newPos = _position;
            if (origin == SeekOrigin.Begin) newPos = offset;
            else if (origin == SeekOrigin.Current) newPos += offset;
            else if (origin == SeekOrigin.End) newPos = _length + offset;

            if (newPos < 0) newPos = 0;
            if (newPos > _length) newPos = _length;
            _position = newPos;
            _baseStream.Seek(_start + _position, SeekOrigin.Begin);
            return _position;
        }

        public override void SetLength(long value) { throw new NotSupportedException(); }
        public override void Write(byte[] buffer, int offset, int count) { throw new NotSupportedException(); }
    }

    internal sealed class InstallerForm : Form
    {
        private readonly string _installDir;
        private readonly bool _launchAfter;
        private readonly Label _titleLabel;
        private readonly Label _statusLabel;
        private readonly ProgressBar _progressBar;
        public int ExitCode { get; private set; }

        public InstallerForm(string installDir, bool launchAfter)
        {
            _installDir = installDir;
            _launchAfter = launchAfter;
            ExitCode = 0;

            Text = "ติดตั้ง ClipDesk (One-Click Installer)";
            Size = new Size(480, 210);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(236, 245, 255);

            _titleLabel = new Label
            {
                Text = "กำลังติดตั้ง ClipDesk...",
                Font = new Font("Segoe UI", 14f, FontStyle.Bold),
                ForeColor = Color.FromArgb(22, 43, 77),
                AutoSize = false,
                Bounds = new Rectangle(24, 22, 420, 32)
            };
            Controls.Add(_titleLabel);

            _statusLabel = new Label
            {
                Text = "เตรียมพร้อมไฟล์ติดตั้ง...",
                Font = new Font("Segoe UI", 9.5f, FontStyle.Regular),
                ForeColor = Color.FromArgb(74, 99, 136),
                AutoSize = false,
                Bounds = new Rectangle(24, 62, 420, 24)
            };
            Controls.Add(_statusLabel);

            _progressBar = new ProgressBar
            {
                Bounds = new Rectangle(24, 96, 416, 28),
                Minimum = 0,
                Maximum = 100,
                Value = 0,
                Style = ProgressBarStyle.Continuous
            };
            Controls.Add(_progressBar);

            Shown += OnShown;
        }

        private void OnShown(object sender, EventArgs e)
        {
            Thread worker = new Thread(RunInstallThread);
            worker.IsBackground = true;
            worker.Start();
        }

        private void RunInstallThread()
        {
            try
            {
                Program.KillRunningClipDesk();
                Program.ExtractPayload(_installDir, (pct, fname) =>
                {
                    try
                    {
                        BeginInvoke((Action)(() =>
                        {
                            _progressBar.Value = Math.Min(100, Math.Max(0, pct));
                            _statusLabel.Text = string.Format("กำลังติดตั้ง ({0}%) — {1}", pct, fname);
                        }));
                    }
                    catch { }
                });

                BeginInvoke((Action)(() =>
                {
                    _progressBar.Value = 100;
                    _statusLabel.Text = "กำลังสร้างทางลัดบนหน้าจอ Desktop...";
                }));

                Program.CreateShortcuts(_installDir);
                Thread.Sleep(350);

                if (_launchAfter)
                {
                    string exePath = Path.Combine(_installDir, "ClipDesk.exe");
                    if (File.Exists(exePath))
                    {
                        Process.Start(new ProcessStartInfo(exePath) { WorkingDirectory = _installDir });
                    }
                }

                BeginInvoke((Action)(() =>
                {
                    ExitCode = 0;
                    Close();
                }));
            }
            catch (Exception ex)
            {
                BeginInvoke((Action)(() =>
                {
                    ExitCode = 1;
                    MessageBox.Show(
                        this,
                        "เกิดข้อผิดพลาดในการติดตั้ง:\n" + ex.Message,
                        "ClipDesk Setup",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    Close();
                }));
            }
        }
    }
}
"""


def find_csc() -> str:
    candidates = [
        r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
        r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    raise SystemExit("csc.exe (.NET Framework compiler) not found")


def build_installer(output_exe: str = DESKTOP_SETUP_EXE) -> str:
    if not os.path.isdir(DIST_APP_DIR):
        raise SystemExit(f"Missing build directory: {DIST_APP_DIR}. Run build_windows.py first.")

    csc = find_csc()

    with tempfile.TemporaryDirectory() as tmp:
        cs_path = os.path.join(tmp, "InstallerStub.cs")
        stub_exe = os.path.join(tmp, "stub.exe")
        zip_path = os.path.join(tmp, "payload.zip")

        with open(cs_path, "w", encoding="utf-8-sig") as fh:
            fh.write(CSHARP_INSTALLER_SOURCE)

        cmd = [
            csc,
            "/nologo",
            "/target:winexe",
            "/optimize+",
            f"/out:{stub_exe}",
            "/r:System.dll",
            "/r:System.Drawing.dll",
            "/r:System.Windows.Forms.dll",
            "/r:System.IO.Compression.dll",
            "/r:System.IO.Compression.FileSystem.dll",
            "/r:Microsoft.CSharp.dll",
        ]
        if os.path.isfile(ICON_PATH):
            cmd.append(f"/win32icon:{ICON_PATH}")
        cmd.append(cs_path)

        print("Compiling installer stub:", " ".join(cmd))
        subprocess.run(cmd, check=True)

        print(f"Creating compressed payload from {DIST_APP_DIR} ...")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for root, _dirs, files in os.walk(DIST_APP_DIR):
                for file in files:
                    abs_file = os.path.join(root, file)
                    rel_file = os.path.relpath(abs_file, DIST_APP_DIR)
                    zf.write(abs_file, rel_file)

        os.makedirs(os.path.dirname(output_exe), exist_ok=True)
        with open(output_exe, "wb") as out_f:
            with open(stub_exe, "rb") as stub_f:
                shutil.copyfileobj(stub_f, out_f)
            zip_offset = out_f.tell()
            with open(zip_path, "rb") as zip_f:
                shutil.copyfileobj(zip_f, out_f)
            out_f.write(struct.pack("<q", zip_offset))
            out_f.write(MAGIC)

    size_mb = os.path.getsize(output_exe) / (1024 * 1024)
    print(f"Created one-click installer: {output_exe} ({size_mb:.1f} MB)")
    return output_exe


if __name__ == "__main__":
    build_installer()
