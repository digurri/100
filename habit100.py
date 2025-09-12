#!/usr/bin/env python3
"""
Habit100 TUI — "인생 개조 매뉴얼 100"용 터미널 앱
- Windows/macOS/Linux, Python 3.10+
- Textual 기반(설치: pip install textual)
- 저장 경로(Windows): %APPDATA%\habit100\{habits.json, entries.json}
- 기존 CLI(habit100.py) JSON 포맷과 호환

키 가이드
  ↑/↓ : 항목 이동
  Space : 오늘 체크 토글(체크형)
  Enter : 기록 입력(기록형)
  a : 새 습관 추가
  e : 선택 항목 수정
  d : 삭제
  f : 태그 필터 토글
  t : 오늘/날짜 선택
  r : 오늘 리포트 표시
  s : 저장(자동 저장도 됨)
  F1 : 도움말
  q : 종료
"""
from __future__ import annotations
import json, os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, Input, Button, SelectionList
from textual.containers import Horizontal, Vertical
from textual import events

APPDIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "habit100"
HABITS = APPDIR / "habits.json"   # {"habits": [{id,title,tags,type,active}]}
ENTRIES = APPDIR / "entries.json"  # {"days": {"YYYY-MM-DD":[{"id":1,"ts":"..","val": true|str}]}}
DATEFMT = "%Y-%m-%d"
TIMEFMT = "%H:%M:%S"

THEMES = [
    "수면·환경","몸·에너지","정신·태도","사회·관계","재정·소비","창의·학습","정체성·자기표현"
]

@dataclass
class Habit:
    id: int
    title: str
    tags: List[str] = field(default_factory=list)
    type: str = "check"  # check | log
    active: bool = True

class Store:
    def __init__(self) -> None:
        APPDIR.mkdir(parents=True, exist_ok=True)
        if not HABITS.exists():
            HABITS.write_text(json.dumps({"habits": []}, ensure_ascii=False, indent=2), encoding="utf-8")
        if not ENTRIES.exists():
            ENTRIES.write_text(json.dumps({"days": {}}, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> tuple[Dict[str, Any], Dict[str, Any]]:
        habits = json.loads(HABITS.read_text(encoding="utf-8"))
        entries = json.loads(ENTRIES.read_text(encoding="utf-8"))
        return habits, entries

    def save(self, habits: Dict[str, Any], entries: Dict[str, Any]) -> None:
        HABITS.write_text(json.dumps(habits, ensure_ascii=False, indent=2), encoding="utf-8")
        ENTRIES.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    def next_id(self, habits: Dict[str, Any]) -> int:
        ids = [x["id"] for x in habits["habits"]]
        return (max(ids) + 1) if ids else 1

class HabitTUI(App):
    CSS = """
    Screen { layout: vertical; }
    .bar { dock: top; padding: 0 1; height: 3; }
    #status { height: 3; }
    #report { height: 6; overflow: auto; }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "add_habit", "Add"),
        ("e", "edit_habit", "Edit"),
        ("d", "delete_habit", "Delete"),
        ("f", "toggle_filter", "Filter"),
        ("t", "pick_date", "Date"),
        ("r", "show_report", "Report"),
        ("s", "save", "Save"),
        ("f1", "help", "Help"),
        ("space", "toggle_check", "Check/Log"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.store = Store()
        self.habits_json, self.entries_json = self.store.load()
        self.current_date = date.today()
        self.filter_tag: Optional[str] = None

    # ---------- Helpers ----------
    def day_key(self) -> str:
        return self.current_date.strftime(DATEFMT)

    def today_done_ids(self) -> set[int]:
        arr = self.entries_json.get("days", {}).get(self.day_key(), [])
        done = set()
        for r in arr:
            if r.get("val") is True or isinstance(r.get("val"), str):
                done.add(r["id"])
        return done

    def refresh_table(self) -> None:
        table: DataTable = self.query_one("DataTable")
        table.clear(columns=True)
        table.add_columns("Done", "ID", "Type", "Title", "Tags")
        rows = []
        done = self.today_done_ids()
        for h in sorted(self.habits_json["habits"], key=lambda x: x["id"]):
            if not h.get("active", True):
                continue
            if self.filter_tag and self.filter_tag not in (h.get("tags") or []):
                continue
            mark = "✅" if h["id"] in done else "□"
            rows.append([mark, str(h["id"]), h.get("type","check"), h["title"], ",".join(h.get("tags") or [])])
        for r in rows:
            table.add_row(*r, key=int(r[1]))
        status = self.query_one("#status", Static)
        status.update(f"[b]{self.day_key()}[/b]  총 {len(rows)}개  필터: {self.filter_tag or '-'}  진행: {len(done)}개")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("[F1] 도움말  [A]추가 [E]수정 [D]삭제  [Space]체크/기록  [F]필터  [T]날짜  [R]리포트  [Q]종료", classes="bar")
        yield DataTable(zebra_stripes=True)
        yield Static(id="status")
        yield Static(id="report")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_table()

    # ---------- Actions ----------
    def action_toggle_check(self) -> None:
        table: DataTable = self.query_one("DataTable")
        if table.cursor_row is None: return
        row = table.get_row_at(table.cursor_row)
        hid = int(row[1])
        habit = next((x for x in self.habits_json["habits"] if x["id"]==hid), None)
        if not habit: return
        dkey = self.day_key()
        self.entries_json.setdefault("days", {}).setdefault(dkey, [])
        if habit.get("type","check") == "check":
            # toggle
            arr = self.entries_json["days"][dkey]
            ex = next((r for r in arr if r["id"]==hid and r.get("val") is True), None)
            if ex:
                arr.remove(ex)
            else:
                arr.append({"id":hid, "ts":datetime.now().strftime(TIMEFMT), "val":True})
        else:
            # log input
            self.push_screen(LogInputScreen(habit, self))
            return
        self.store.save(self.habits_json, self.entries_json)
        self.refresh_table()

    def action_add_habit(self) -> None:
        self.push_screen(EditScreen(self, title="새 습관 추가"))

    def action_edit_habit(self) -> None:
        table: DataTable = self.query_one("DataTable")
        if table.cursor_row is None: return
        hid = int(table.get_row_at(table.cursor_row)[1])
        habit = next((x for x in self.habits_json["habits"] if x["id"]==hid), None)
        if habit:
            self.push_screen(EditScreen(self, habit, title="습관 수정"))

    def action_delete_habit(self) -> None:
        table: DataTable = self.query_one("DataTable")
        if table.cursor_row is None: return
        hid = int(table.get_row_at(table.cursor_row)[1])
        self.habits_json["habits"] = [x for x in self.habits_json["habits"] if x["id"]!=hid]
        # 해당 기록도 제거
        for d, arr in list(self.entries_json.get("days", {}).items()):
            self.entries_json["days"][d] = [r for r in arr if r["id"]!=hid]
        self.store.save(self.habits_json, self.entries_json)
        self.refresh_table()

    def action_toggle_filter(self) -> None:
        # 태그 필터: None -> 주요 테마 순환
        if self.filter_tag is None:
            self.filter_tag = THEMES[0]
        else:
            idx = THEMES.index(self.filter_tag) if self.filter_tag in THEMES else -1
            self.filter_tag = THEMES[(idx+1) % len(THEMES)] if idx>=0 else None
        self.refresh_table()

    def action_pick_date(self) -> None:
        self.push_screen(DateScreen(self))

    def action_show_report(self) -> None:
        # 오늘 리포트 간단 출력
        dkey = self.day_key()
        arr = self.entries_json.get("days", {}).get(dkey, [])
        by_id: Dict[int, List[Dict[str,Any]]] = {}
        for r in arr:
            by_id.setdefault(r["id"], []).append(r)
        lines = [f"[b]Report {dkey}[/b]"]
        for h in sorted(self.habits_json["habits"], key=lambda x:x["id"]):
            if not h.get("active", True):
                continue
            logs = by_id.get(h["id"], [])
            if h.get("type","check") == "check":
                if any(r.get("val") is True for r in logs):
                    lines.append(f"- [x] #{h['id']} {h['title']}")
            else:
                for r in logs:
                    if isinstance(r.get("val"), str):
                        lines.append(f"- #{h['id']} {h['title']} — {r['val']} ({r['ts']})")
        self.query_one("#report", Static).update("\n".join(lines))

    def action_save(self) -> None:
        self.store.save(self.habits_json, self.entries_json)

    def action_help(self) -> None:
        help_text = (
            "↑/↓ 이동  Space 체크/기록  A 추가  E 수정  D 삭제  F 태그필터  T 날짜  R 리포트  Q 종료"
        )
        self.query_one("#report", Static).update(help_text)

class EditScreen(App):
    def __init__(self, main: HabitTUI, habit: Optional[Dict[str,Any]] = None, title: str = ""):
        super().__init__()
        self.main = main
        self.habit = habit
        self.window_title = title

    def compose(self) -> ComposeResult:
        title = self.habit["title"] if self.habit else ""
        tags = ",".join(self.habit.get("tags") or []) if self.habit else ""
        typ = self.habit.get("type","check") if self.habit else "check"
        yield Static(self.window_title)
        yield Static("제목:")
        self.title_input = Input(value=title, placeholder="제목 입력")
        yield self.title_input
        yield Static("태그(쉼표 구분):")
        self.tags_input = Input(value=tags, placeholder="예: 수면·환경,몸·에너지")
        yield self.tags_input
        yield Static("유형(check/log):")
        self.type_input = Input(value=typ)
        yield self.type_input
        with Horizontal():
            yield Button("저장", id="save")
            yield Button("취소", id="cancel")

    def on_button_pressed(self, e: Button.Pressed) -> None:
        if e.button.id == "save":
            title = self.title_input.value.strip()
            tags = [t.strip() for t in self.tags_input.value.split(",") if t.strip()]
            typ = self.type_input.value.strip() or "check"
            hjson = self.main.habits_json
            if self.habit:
                self.habit.update({"title": title, "tags": tags, "type": typ})
            else:
                hid = self.main.store.next_id(hjson)
                hjson["habits"].append({"id":hid, "title":title, "tags":tags, "type":typ, "active":True})
            self.main.store.save(self.main.habits_json, self.main.entries_json)
            self.main.refresh_table()
            self.exit()
        else:
            self.exit()

class LogInputScreen(App):
    def __init__(self, habit: Dict[str,Any], main: HabitTUI):
        super().__init__()
        self.habit = habit
        self.main = main

    def compose(self) -> ComposeResult:
        yield Static(f"기록 입력 — #{self.habit['id']} {self.habit['title']}")
        self.text_input = Input(placeholder="내용 입력 후 Enter")
        yield self.text_input
        with Horizontal():
            yield Button("저장", id="save")
            yield Button("취소", id="cancel")

    def on_mount(self) -> None:
        self.text_input.focus()

    def on_button_pressed(self, e: Button.Pressed) -> None:
        if e.button.id == "save":
            txt = self.text_input.value.strip()
            if txt:
                dkey = self.main.day_key()
                self.main.entries_json.setdefault("days", {}).setdefault(dkey, []).append({
                    "id": self.habit["id"],
                    "ts": datetime.now().strftime(TIMEFMT),
                    "val": txt,
                })
                self.main.store.save(self.main.habits_json, self.main.entries_json)
                self.main.refresh_table()
            self.exit()
        else:
            self.exit()

class DateScreen(App):
    def __init__(self, main: HabitTUI):
        super().__init__()
        self.main = main

    def compose(self) -> ComposeResult:
        yield Static("날짜 이동: 어제로 [-], 오늘로 [0], 내일로 [+]. Close로 닫기.")
        with Horizontal():
            yield Button("-", id="prev")
            yield Button("오늘", id="today")
            yield Button("+", id="next")
            yield Button("Close", id="close")

    def on_button_pressed(self, e: Button.Pressed) -> None:
        if e.button.id == "prev":
            self.main.current_date -= timedelta(days=1)
        elif e.button.id == "next":
            self.main.current_date += timedelta(days=1)
        elif e.button.id == "today":
            self.main.current_date = date.today()
        self.main.refresh_table()
        if e.button.id == "close":
            self.exit()

if __name__ == "__main__":
    HabitTUI().run()
