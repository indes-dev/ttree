"""TASK-002 legacy DOC probes through the real LibreOffice reader. Synthetic only.

Run inside an isolated network namespace (see run_doc.sh):
    unshare -Urn python probe_doc.py WORKDIR
The script brings up the namespace loopback, starts an HTTP listener on
127.0.0.1:8765 and records every request. Fixtures reference only that listener
and a synthetic sentinel file. LibreOffice detects formats by content, so a file
named `.doc` may be imported as HTML, RTF or flat ODF.

For each fixture it runs ttree's extract_doc() and records: issue, extracted text
length, whether the sentinel text was pulled in, whether a macro marker appeared,
listener requests, surviving reader processes and leftover temporary files.
Positive controls convert the same fixtures with a deliberately permissive
profile to show that the vectors are live in this LibreOffice build.
"""

import http.server
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
SENTINEL = "SENTINEL-LOCAL-FILE-CONTENT-7f3a"
REQUESTS: list[str] = []


class Listener(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        REQUESTS.append(self.path)
        body = b"REMOTE-CONTENT-9c1e" if "text" in self.path or "section" in self.path else b"GIF89a"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_HEAD = do_GET  # noqa: N815

    def log_message(self, *args):
        pass


def network_namespace_ready() -> None:
    subprocess.run(["ip", "link", "set", "lo", "up"], check=True)
    with socket.socket() as probe:
        probe.settimeout(1)
        try:
            probe.connect(("1.1.1.1", 443))
        except OSError:
            pass
        else:
            raise SystemExit("network is reachable; run under unshare -Urn")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Listener)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def fodt(body: str, scripts: str = "") -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
 xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
 xmlns:script="urn:oasis:names:tc:opendocument:xmlns:script:1.0"
 xmlns:xlink="http://www.w3.org/1999/xlink"
 xmlns:ooo="http://openoffice.org/2004/office"
 office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.text">
{scripts}<office:body><office:text>{body}</office:text></office:body></office:document>
'''


def make_fixtures(work: Path) -> dict[str, Path]:
    fixtures = work / "fixtures"
    fixtures.mkdir()
    sentinel = work / "sentinel.txt"
    sentinel.write_text(SENTINEL + "\n")
    marker = work / "macro-marker.txt"
    out: dict[str, Path] = {}

    out["html_as_doc"] = fixtures / "html_as.doc"
    out["html_as_doc"].write_text(
        f'<html><head><link rel="stylesheet" href="{BASE}/html-css"></head><body>'
        f'<p>HTML carrier</p><img src="{BASE}/html-img.gif"><iframe src="{BASE}/html-iframe-text"></iframe>'
        f'</body></html>')

    out["rtf_as_doc"] = fixtures / "rtf_as.doc"
    out["rtf_as_doc"].write_text(
        "{\\rtf1\\ansi{\\fonttbl{\\f0 Times;}}\\f0 RTF carrier\\par\n"
        f'{{\\field{{\\*\\fldinst INCLUDETEXT "{BASE}/rtf-text"}}{{\\fldrslt cached-remote}}}}\\par\n'
        f'{{\\field{{\\*\\fldinst INCLUDEPICTURE "{BASE}/rtf-pic.gif" \\\\d}}{{\\fldrslt }}}}\\par\n'
        f'{{\\field{{\\*\\fldinst INCLUDETEXT "{sentinel}"}}{{\\fldrslt cached-local}}}}\\par\n}}\n')

    macro = f'''<office:scripts>
 <office:script script:language="ooo:Basic"><ooo:libraries>
  <ooo:library-embedded ooo:name="Standard"><ooo:module ooo:name="Module1"><ooo:source-code>Sub Main
  Dim n As Integer
  n = FreeFile
  Open "{marker}" For Output As #n
  Print #n, "macro ran"
  Close #n
End Sub</ooo:source-code></ooo:module></ooo:library-embedded>
 </ooo:libraries></office:script>
 <office:event-listeners><script:event-listener script:language="ooo:script" script:event-name="dom:load"
  xlink:href="vnd.sun.star.script:Standard.Module1.Main?language=Basic&amp;location=document" xlink:type="simple"/></office:event-listeners>
</office:scripts>'''
    out["fodt_macro_as_doc"] = fixtures / "fodt_macro.doc"
    out["fodt_macro_as_doc"].write_text(fodt("<text:p>Macro carrier</text:p>", macro))

    out["fodt_links_as_doc"] = fixtures / "fodt_links.doc"
    out["fodt_links_as_doc"].write_text(fodt(
        "<text:p>Link carrier</text:p>"
        f'<text:section text:name="Remote"><text:section-source xlink:href="{BASE}/fodt-section" xlink:type="simple" text:filter-name="Text"/></text:section>'
        f'<text:section text:name="Local"><text:section-source xlink:href="{sentinel.as_uri()}" xlink:type="simple" text:filter-name="Text"/></text:section>'
        f'<text:p><draw:frame svg:width="1cm" svg:height="1cm"><draw:image xlink:href="{BASE}/fodt-image.gif" xlink:type="simple"/></draw:frame></text:p>'))
    # Calc content named .doc: external table source and WEBSERVICE() with a cached value.
    # ttree's profile only sets Writer link/field updates, not Calc's.
    out["fods_as_doc"] = fixtures / "fods.doc"
    out["fods_as_doc"].write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2"
 office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.spreadsheet">
<office:body><office:spreadsheet>
 <table:table table:name="Sheet1"><table:table-row>
  <table:table-cell office:value-type="string"><text:p>Calc carrier</text:p></table:table-cell>
  <table:table-cell table:formula="of:=WEBSERVICE(&quot;{BASE}/calc-webservice-text&quot;)" office:value-type="string"><text:p>cached</text:p></table:table-cell>
 </table:table-row></table:table>
 <table:table table:name="Linked"><table:table-source xlink:type="simple" xlink:href="{BASE}/calc-source-text" table:filter-name="Text - txt - csv (StarCalc)" table:mode="copy-all"/>
  <table:table-row><table:table-cell><text:p>cached</text:p></table:table-cell></table:table-row></table:table>
</office:spreadsheet></office:body></office:document>
''')
    return out


def make_real_doc(work: Path, reader: str) -> Path:
    source = work / "real-source.txt"
    source.write_text("Synthetic legacy Word document text for ttree review.\n")
    profile = work / "real-profile"
    subprocess.run([reader, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--norestore",
                    "--convert-to", "doc:MS Word 97", "--outdir", str(work / "real"), str(source)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    return work / "real" / "real-source.doc"


def permissive_convert(reader: str, path: Path, work: Path) -> str:
    """Positive control: low macro security, links always updated, active content on."""
    control = Path(tempfile.mkdtemp(prefix="control-", dir=work))
    user = control / "profile/user"
    user.mkdir(parents=True)
    (user / "registrymodifications.xcu").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
        '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
        '<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>0</value></prop>'
        '<prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>false</value></prop></item>'
        '<item oor:path="/org.openoffice.Office.Writer/Content/Update">'
        '<prop oor:name="Link" oor:op="fuse"><value>0</value></prop>'
        '<prop oor:name="Field" oor:op="fuse"><value>true</value></prop></item></oor:items>')
    copy = control / "input.doc"
    shutil.copyfile(path, copy)
    subprocess.run([reader, f"-env:UserInstallation={(control / 'profile').as_uri()}", "--headless",
                    "--norestore", "--convert-to", "txt:Text (encoded):UTF8", "--outdir", str(control), str(copy)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    output = control / "input.txt"
    return output.read_text(encoding="utf-8-sig") if output.is_file() else ""


def surviving_readers() -> list[str]:
    found = []
    for proc in Path("/proc").iterdir():
        if proc.name.isdigit():
            try:
                cmdline = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            except OSError:
                continue
            if "ttree-doc-" in cmdline:
                found.append(proc.name)
    return found


def main():
    work = Path(sys.argv[1]).resolve()
    network_namespace_ready()
    reader = shutil.which("libreoffice") or shutil.which("soffice")
    print(f"reader={reader} version={subprocess.run([reader, '--version'], capture_output=True, text=True).stdout.strip()}")
    private_tmp = work / "tmpdir"
    private_tmp.mkdir()
    fixtures = make_fixtures(work)
    fixtures = {"real_doc": make_real_doc(work, reader), **fixtures}
    REQUESTS.clear()

    os.environ["TMPDIR"] = str(private_tmp)
    tempfile.tempdir = None
    from ttree.documents import extract_doc

    marker = work / "macro-marker.txt"
    for name, path in fixtures.items():
        before = path.read_bytes()
        siblings_before = sorted(p.name for p in path.parent.iterdir())
        REQUESTS.clear()
        start = time.monotonic()
        result = extract_doc(path)
        elapsed = time.monotonic() - start
        time.sleep(0.5)
        print(f"ttree case={name} issue={result.issue!r} text_chars={len(result.text)} seconds={elapsed:.1f} "
              f"sentinel_in_text={SENTINEL in result.text} remote_in_text={'REMOTE-CONTENT' in result.text} "
              f"macro_marker={marker.exists()} requests={REQUESTS} survivors={surviving_readers()} "
              f"tmp_leftovers={sorted(p.name for p in private_tmp.iterdir())} "
              f"original_unchanged={path.read_bytes() == before} "
              f"siblings_unchanged={sorted(p.name for p in path.parent.iterdir()) == siblings_before}")

    # End-to-end through the CLI entry point on the HTML carrier.
    REQUESTS.clear()
    from ttree.cli import main as ttree_main
    status = ttree_main([str(fixtures["html_as_doc"])])
    time.sleep(0.5)
    print(f"cli case=html_as_doc exit_status={status} requests={REQUESTS}")

    for name in ("rtf_as_doc", "fodt_macro_as_doc", "fodt_links_as_doc", "html_as_doc", "fods_as_doc"):
        REQUESTS.clear()
        marker.unlink(missing_ok=True)
        text = permissive_convert(reader, fixtures[name], work)
        time.sleep(0.5)
        print(f"control case={name} text_chars={len(text)} sentinel_in_text={SENTINEL in text} "
              f"remote_in_text={'REMOTE-CONTENT' in text} macro_marker={marker.exists()} requests={REQUESTS}")


if __name__ == "__main__":
    main()
