"""Review a course's scripts before any audio is made.

  python3 tools/review.py <slug>                  build without voice and serve the review page
  python3 tools/review.py <slug> --comments       print the open comments
  python3 tools/review.py <slug> --close <id>...  close comments
  python3 tools/review.py <slug> --export         write the outline to review/<slug>/00-outline.txt and each
                                                  module's narration to review/<slug>/NN-<stem>.txt
  python3 tools/review.py <slug> --import FOLDER  read those files back into the scripts in FOLDER
  python3 tools/review.py <slug> --approve-outline all | N...
                                                  record the owner's approval of the outline, after review
                                                  in the text file
  python3 tools/review.py <slug> --approve all | N...
                                                  record the owner's approval of these modules' scripts

The comments and approvals are saved to review/<slug>.json, which is the record of what was approved.
The text files are working copies and are not tracked; the scripts are the record of the wording.
The server listens on 127.0.0.1 only.
"""
import argparse
import json
import mimetypes
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import outline as outlines  # noqa: E402
import review_page  # noqa: E402
import review_state as rs  # noqa: E402
import narration_text as nt  # noqa: E402
import outline_text as ot  # noqa: E402
import script as scripts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PORT = 8780
LETTERS = {"vault": "V", "backup": "B", "vpc": "N", "rovs": "R"}
SCRATCH = Path("/private/tmp/claude-501/-Users-neiltaylor-Projects-rovs-tutorials/"
               "f3aa05c3-29fa-491b-8f00-433add9e3834/scratchpad")


class Review:
    """One course under review: its scripts, its build folder and its saved record."""

    def __init__(self, slug, cfg, out, state_path, letter=None):
        self.slug, self.cfg, self.out, self.state_path = slug, cfg, Path(out), Path(state_path)
        self.letter = letter or LETTERS.get(slug, slug[:1].upper())
        self.lock = threading.RLock()
        self.loaded, self.problems, self.build_error, self._signature = [], [], None, None

    @property
    def source(self) -> Path:
        return Path(self.cfg["source"])

    def _sig(self):
        files = list(self.source.glob("*.json")) + list(self.source.parent.glob("*.html"))
        return sorted((str(f), f.stat().st_mtime_ns) for f in files)

    def refresh(self):
        """Load and check the scripts and rebuild the pages when a script or unit page has changed."""
        with self.lock:
            sig = self._sig() if self.source.is_dir() else []
            if sig == self._signature:
                return
            self.loaded, self.problems = build.load_video(self.slug, self.cfg)
            self.build_error = None
            try:
                build.write_video(self.out, self.slug, self.cfg, self.loaded, None, {}, estimate=True)
            except Exception as e:  # a malformed script must not stop the page from opening
                self.build_error = "The slide pictures could not be built: %s" % e
            self._signature = sig

    def number(self, stem) -> int:
        return [s for s, _ in self.loaded].index(stem) + 1

    def module_problems(self, stem) -> list:
        prefix = "%s: %s.json: " % (self.slug, stem)
        return [p[len(prefix):] for p in self.problems if p.startswith(prefix)]

    def general_problems(self) -> list:
        stems = {s for s, _ in self.loaded}
        out = [p for p in self.problems if not any(p.startswith("%s: %s.json: " % (self.slug, s)) for s in stems)]
        return out + ([self.build_error] if self.build_error else [])

    def outline(self):
        path = self.source / "outline.json"
        if not path.is_file():
            return None, []
        data = outlines.load_outline(path)
        units = sorted(p.stem for p in self.source.parent.glob("*.html") if p.stem != "index")
        return data, outlines.check_outline(data, units)

    def state(self) -> dict:
        return rs.load_state(self.state_path)

    def course_page(self) -> str:
        st = self.state()
        rows = [(stem, n, s.get("title", stem), rs.module_status(st, stem, s, self.letter, n))
                for n, (stem, s) in enumerate(self.loaded, 1)]
        return review_page.render_course(self.slug, self.cfg["title"], self.letter, rows, self.general_problems())

    def module_page(self, stem):
        script = dict(self.loaded).get(stem)
        if script is None:
            return None
        return review_page.render_module(self.slug, self.letter, self.number(stem), stem, script,
                                         self.module_problems(stem), scripts.notes(script), self.state())

    def narration_page(self, stem):
        script = dict(self.loaded).get(stem)
        if script is None:
            return None
        return review_page.render_narration(self.slug, self.letter, self.number(stem), stem, script, self.state())

    def outline_page(self) -> str:
        data, problems = self.outline()
        numbers = {stem: n for n, (stem, _) in enumerate(self.loaded, 1)}
        return review_page.render_outline(self.slug, self.letter, data, numbers, problems, self.state())

    def post(self, route, body):
        """Apply a POST. Returns (status, json). Every change is saved before it is answered."""
        with self.lock:
            st = self.state()
            if route == "/api/comment":
                ref, text = str(body.get("ref", "")).strip(), str(body.get("text", "")).strip()
                if not ref or not text:
                    return 400, {"error": "A comment needs a reference and some text."}
                new = rs.add_comment(st, ref, str(body.get("say", "")), text)
                rs.save_state(self.state_path, st)
                return 200, {"id": new}
            stem = str(body.get("stem", ""))
            if route == "/api/approve-outline":
                data, problems = self.outline()
                mod = next((m for m in (data or {}).get("modules", []) if m.get("unit") == stem), None)
                if mod is None or problems:
                    return 400, {"error": "The outline has problems or has no such module."}
                st["outline"][stem] = {"approved": rs.outline_hash(mod)}
            elif route in ("/api/approve", "/api/seen"):
                script = dict(self.loaded).get(stem)
                if script is None:
                    return 404, {"error": "No such module."}
                n = self.number(stem)
                if route == "/api/approve":
                    if self.module_problems(stem):
                        return 400, {"error": "This script has problems. Fix them before approving."}
                    rs.approve(st, stem, script, self.letter, n)
                else:
                    rs.mark_seen(st, stem, script, self.letter, n)
            else:
                return 404, {"error": "No such route."}
            rs.save_state(self.state_path, st)
            return 200, {"ok": True}


OUTLINE_FILE = "00-outline.txt"


def export_texts(review, folder) -> Path:
    """Write the outline to <folder>/<slug>/00-outline.txt and each module's narration to
    <folder>/<slug>/NN-<stem>.txt. A file that has changes not yet imported is kept."""
    review.refresh()
    target = Path(folder) / review.slug
    target.mkdir(parents=True, exist_ok=True)
    files = [(target / ("%02d-%s.txt" % (n, stem)), nt.export_text(script, review.letter, n))
             for n, (stem, script) in enumerate(review.loaded, 1)]
    data, _ = review.outline()
    if data is not None:
        files.insert(0, (target / OUTLINE_FILE, ot.export_outline(data, review.letter)))
    for path, text in files:
        if path.is_file() and path.read_text(encoding="utf-8") != text:
            print("kept %s: it has changes not yet imported" % path.name)
            continue
        path.write_text(text, encoding="utf-8")
    print(target)
    return target


def approve_texts(review, folder, kind, which) -> list:
    """Record the owner's approval of the outline ("outline") or of module scripts ("module") for the module
    numbers in which, or "all". Only what the owner read is approved: nothing is approved while the text file
    has changes not yet imported. A module with open comments or problems is skipped. Returns the numbers
    approved."""
    review.refresh()
    target = Path(folder) / review.slug
    st, approved = review.state(), []
    if kind == "outline":
        data, problems = review.outline()
        if data is None or problems:
            print("outline not approved: it has problems or there is no outline")
            return []
        path = target / OUTLINE_FILE
        if path.is_file() and path.read_text(encoding="utf-8") != ot.export_outline(data, review.letter):
            print("outline not approved: %s has changes not imported" % OUTLINE_FILE)
            return []
        modules = list(enumerate(data.get("modules", []), 1))
    else:
        modules = list(enumerate(review.loaded, 1))
    for n, item in modules:
        if which != "all" and n not in which:
            continue
        label = "%s %d" % (review.letter, n)
        if rs.open_in_module(st, review.letter, n):
            print("%s: has open comments" % label)
            continue
        if kind == "outline":
            st["outline"][item["unit"]] = {"approved": rs.outline_hash(item)}
        else:
            stem, script = item
            path = target / ("%02d-%s.txt" % (n, stem))
            if path.is_file() and path.read_text(encoding="utf-8") != nt.export_text(script, review.letter, n):
                print("%s: %s has changes not yet imported" % (label, path.name))
                continue
            if review.module_problems(stem):
                print("%s: the script has problems" % label)
                continue
            rs.approve(st, stem, script, review.letter, n)
        approved.append(n)
    rs.save_state(review.state_path, st)
    what = "outline approved" if kind == "outline" else "modules approved"
    print("%s: %s" % (what, ", ".join("%s %d" % (review.letter, n) for n in approved) or "none"))
    return approved


def _numbers(values):
    if values == ["all"]:
        return "all"
    try:
        return [int(v) for v in values]
    except ValueError:
        raise SystemExit("give module numbers, or all")


def import_texts(review, folder, video_folder) -> None:
    """Read each text file in <folder>/<slug>/ into the script of the same module in video_folder."""
    video_folder = Path(video_folder)
    stems = sorted(f.stem for f in video_folder.glob("*.json") if f.name != "outline.json")
    state, changed_stems = review.state(), []
    outline_path = Path(folder) / review.slug / OUTLINE_FILE
    if outline_path.is_file():
        import_outline(review, outline_path, video_folder / "outline.json", state)
    for path in sorted((Path(folder) / review.slug).glob("*.txt")):
        if path.name == OUTLINE_FILE:
            continue
        m = re.match(r"(\d+)-(.+)$", path.stem)
        if not m or not (video_folder / (m.group(2) + ".json")).is_file():
            print("%s: no module script in %s for this file" % (path.name, video_folder))
            continue
        number, stem = int(m.group(1)), m.group(2)
        says, comments, problems = nt.parse_text(path.read_text(encoding="utf-8"))
        if problems:
            print("%s: not imported" % stem)
            print("\n".join("  " + p for p in problems))
            continue
        target = video_folder / (stem + ".json")
        script = json.loads(target.read_text(encoding="utf-8"))
        changed, apply_problems = nt.apply_text(script, review.letter, number, says)
        target.write_text(json.dumps(script, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        said = {r["ref"]: r["say"] for r in rs.refs(script, review.letter, number)}
        count = 0
        for n, texts in sorted(comments.items()):
            ref = "%s %d.%d" % (review.letter, number, n)
            for text in texts:
                rs.add_comment(state, ref, said.get(ref, ""), text)
                count += 1
        print("%s: %d sentences changed, %d comments" % (stem, len(changed), count))
        for p in apply_problems:
            print("  " + p)
        if changed:
            changed_stems.append((stem, script))
    rs.save_state(review.state_path, state)
    for stem, script in changed_stems:
        unit = video_folder.parent / (stem + ".html")
        found = scripts.check_script(script, unit.read_text(encoding="utf-8"), stem == stems[0])
        for p in found:
            print("%s: %s" % (stem, p))


def import_outline(review, path, target, state) -> None:
    """Read the outline text file into outline.json and add its comments to the module they are about."""
    if not target.is_file():
        print("outline: no outline.json in %s" % target.parent)
        return
    values, comments, problems = ot.parse_outline(path.read_text(encoding="utf-8"))
    if problems:
        print("outline: not imported")
        print("\n".join("  " + p for p in problems))
        return
    data = json.loads(target.read_text(encoding="utf-8"))
    changed, apply_problems = ot.apply_outline(data, review.letter, values)
    target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    modules, count = data.get("modules") or [], 0
    for (n, key), texts in sorted(comments.items()):
        if not 1 <= n <= len(modules):
            continue
        said = "%s: %s" % (ot.label(modules[n - 1], key), values.get((n, key), ""))
        for text in texts:
            rs.add_comment(state, "%s %d.0" % (review.letter, n), said, text)
            count += 1
    print("outline: %d changed, %d comments" % (len(changed), count))
    for p in apply_problems:
        print("  " + p)
    units = sorted(p.stem for p in target.parent.parent.glob("*.html") if p.stem != "index")
    for p in outlines.check_outline(data, units):
        print("outline: %s" % p)


def make_handler(review):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, status, body, ctype):
            data = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = unquote(urlparse(self.path).path)
            html = "text/html; charset=utf-8"
            review.refresh()
            if path == "/":
                return self._send(200, review.course_page(), html)
            if path == "/outline":
                return self._send(200, review.outline_page(), html)
            if path.startswith("/m/") and path.endswith("/narration"):
                page = review.narration_page(path[3:-len("/narration")])
                return self._send(200, page, html) if page else self._send(404, "No such module", "text/plain")
            if path.startswith("/m/"):
                page = review.module_page(path[3:])
                return self._send(200, page, html) if page else self._send(404, "No such module", "text/plain")
            target = (review.out / path.lstrip("/")).resolve()
            if target.is_file() and target.is_relative_to(review.out.resolve()):
                ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                return self._send(200, target.read_bytes(), ctype)
            self._send(404, "Not found", "text/plain")

        def do_POST(self):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                status, answer = review.post(urlparse(self.path).path, body)
            except (ValueError, TypeError):
                status, answer = 400, {"error": "The request was not JSON."}
            self._send(status, json.dumps(answer), "application/json")

    return Handler


def serve(review, port=PORT):
    review.refresh()
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(review))
    print("Review page for %s: http://127.0.0.1:%d/" % (review.slug, server.server_address[1]), flush=True)
    server.serve_forever()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", choices=sorted(build.VIDEO))
    ap.add_argument("--comments", action="store_true", help="print the open comments")
    ap.add_argument("--close", nargs="+", type=int, metavar="ID", help="close these comments")
    ap.add_argument("--export", action="store_true", help="write each module's narration to a text file")
    ap.add_argument("--import", dest="import_folder", metavar="FOLDER",
                    help="read the text files into the scripts in FOLDER (a working copy of the video folder)")
    ap.add_argument("--approve-outline", nargs="+", metavar="N", help="approve the outline of these modules, or all")
    ap.add_argument("--approve", nargs="+", metavar="N", help="approve these modules' scripts, or all")
    ap.add_argument("--out", help="build folder (default: a scratch folder)")
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args(argv)
    state_path = ROOT / "review" / (args.slug + ".json")
    if args.approve_outline or args.approve:
        review = Review(args.slug, build.VIDEO[args.slug], args.out or SCRATCH / ("review-" + args.slug), state_path)
        if args.approve_outline:
            approve_texts(review, ROOT / "review", "outline", _numbers(args.approve_outline))
        if args.approve:
            approve_texts(review, ROOT / "review", "module", _numbers(args.approve))
        return
    if args.export or args.import_folder:
        review = Review(args.slug, build.VIDEO[args.slug], args.out or SCRATCH / ("review-" + args.slug), state_path)
        if args.export:
            export_texts(review, ROOT / "review")
        else:
            import_texts(review, ROOT / "review", args.import_folder)
        return
    if args.comments or args.close:
        st = rs.load_state(state_path)
        if args.close:
            rs.close_comments(st, args.close)
            rs.save_state(state_path, st)
        if args.comments:
            print("\n".join(rs.comments_report(st)))
        return
    out = args.out or SCRATCH / ("review-" + args.slug)
    serve(Review(args.slug, build.VIDEO[args.slug], out, state_path), args.port)


if __name__ == "__main__":
    main()
