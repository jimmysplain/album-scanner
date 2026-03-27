"""
Album Cover Scanner — Android Tablet App
Built with Kivy. Scans video files for visible album covers using Claude AI.
"""

import os, sys, json, base64, csv, threading
from pathlib import Path
from datetime import datetime

# ── Bootstrap pip packages at first run ──────────────────────────────────────
def ensure_packages():
    required = {"anthropic": "anthropic", "cv2": "opencv-python-headless"}
    for mod, pkg in required.items():
        try:
            __import__(mod)
        except ImportError:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

ensure_packages()

import cv2
import anthropic

# ── Kivy imports ─────────────────────────────────────────────────────────────
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.storage.jsonstore import JsonStore

# ── Android permissions ───────────────────────────────────────────────────────
try:
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    ANDROID = True
except ImportError:
    ANDROID = False

# ── Colours ───────────────────────────────────────────────────────────────────
BG       = get_color_from_hex("#0d0d14")
SURFACE  = get_color_from_hex("#14141e")
SURFACE2 = get_color_from_hex("#1e1e2e")
BORDER   = get_color_from_hex("#2e2e42")
ACCENT   = get_color_from_hex("#7c3aed")
ACCENT2  = get_color_from_hex("#a855f7")
ACCENT3  = get_color_from_hex("#c084fc")
GREEN    = get_color_from_hex("#22c55e")
RED      = get_color_from_hex("#ef4444")
TEXT     = get_color_from_hex("#f0f0ff")
MUTED    = get_color_from_hex("#6b6b8a")

# ── KV layout ────────────────────────────────────────────────────────────────
KV = """
#:import get_color_from_hex kivy.utils.get_color_from_hex
#:import dp kivy.metrics.dp

<RoundedButton@Button>:
    background_normal: ''
    background_color: get_color_from_hex('#7c3aed')
    color: get_color_from_hex('#f0f0ff')
    font_size: dp(15)
    bold: True
    size_hint_y: None
    height: dp(52)
    canvas.before:
        Color:
            rgba: self.background_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]

<GhostButton@Button>:
    background_normal: ''
    background_color: get_color_from_hex('#1e1e2e')
    color: get_color_from_hex('#6b6b8a')
    font_size: dp(14)
    bold: True
    size_hint_y: None
    height: dp(46)
    canvas.before:
        Color:
            rgba: self.background_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]

<SectionLabel@Label>:
    color: get_color_from_hex('#6b6b8a')
    font_size: dp(11)
    bold: True
    size_hint_y: None
    height: dp(24)
    halign: 'left'
    valign: 'middle'
    text_size: self.width, None

<CardBox@BoxLayout>:
    orientation: 'vertical'
    padding: dp(14)
    spacing: dp(8)
    size_hint_y: None
    height: self.minimum_height
    canvas.before:
        Color:
            rgba: get_color_from_hex('#14141e')
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(16)]
        Color:
            rgba: get_color_from_hex('#2e2e42')
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(16)]
            width: 1

<TrackCard@BoxLayout>:
    orientation: 'vertical'
    padding: [dp(16), dp(12), dp(12), dp(12)]
    spacing: dp(4)
    size_hint_y: None
    height: self.minimum_height
    canvas.before:
        Color:
            rgba: get_color_from_hex('#17171f')
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]
        Color:
            rgba: get_color_from_hex('#2e2e42')
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(14)]
            width: 1
        Color:
            rgba: get_color_from_hex('#7c3aed')
        RoundedRectangle:
            pos: self.x, self.y
            size: dp(3), self.height
            radius: [dp(2)]

<MainScreen>:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: get_color_from_hex('#0d0d14')
        Rectangle:
            pos: self.pos
            size: self.size

    # Header
    BoxLayout:
        size_hint_y: None
        height: dp(80)
        padding: [dp(22), dp(16), dp(22), dp(4)]
        canvas.before:
            Color:
                rgba: get_color_from_hex('#0d0d14')
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: '[b]Album Cover[/b]\n[size=12sp][color=#6b6b8a]VIDEO · VISION · IDENTIFY[/color][/size]'
            markup: True
            font_size: dp(24)
            color: get_color_from_hex('#f0f0ff')
            halign: 'left'
            valign: 'middle'
            text_size: self.width, None

    # Scrollable body
    ScrollView:
        do_scroll_x: False
        MainBody:
            id: body
            orientation: 'vertical'
            padding: [dp(16), dp(8), dp(16), dp(24)]
            spacing: dp(12)
            size_hint_y: None
            height: self.minimum_height

<MainBody>:
    pass
"""

Builder.load_string(KV)


# ── Main Screen ───────────────────────────────────────────────────────────────
class MainScreen(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.store      = JsonStore("album_scanner_prefs.json")
        self.video_path = None
        self.frames     = []
        self.tracks     = []
        self._build_ui()

    def _build_ui(self):
        body = self.ids.body

        # ── API key card ──
        api_card = self._card()
        api_card.add_widget(self._section_label("🔑  ANTHROPIC API KEY"))

        self.api_input = TextInput(
            hint_text="sk-ant-api03-…",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=dp(46),
            font_size=dp(13),
            foreground_color=TEXT,
            background_color=SURFACE2,
            cursor_color=list(ACCENT),
            padding=[dp(12), dp(12)],
        )
        saved_key = self.store.get("key")["value"] if self.store.exists("key") else ""
        self.api_input.text = saved_key
        api_card.add_widget(self.api_input)

        save_btn = self._rounded_btn("Save Key", self._save_key)
        api_card.add_widget(save_btn)

        hint = Label(
            text="Get your key at console.anthropic.com",
            color=MUTED, font_size=dp(11),
            size_hint_y=None, height=dp(20),
            halign='left', text_size=(Window.width - dp(64), None)
        )
        api_card.add_widget(hint)
        body.add_widget(api_card)

        # ── Video select card ──
        vid_card = self._card()
        vid_card.add_widget(self._section_label("📽   VIDEO FILE"))

        self.video_label = Label(
            text="No video selected",
            color=MUTED, font_size=dp(13),
            size_hint_y=None, height=dp(36),
            halign='left', text_size=(Window.width - dp(64), None)
        )
        vid_card.add_widget(self.video_label)

        pick_btn = self._rounded_btn("📁  Select Video", self._open_picker)
        vid_card.add_widget(pick_btn)
        body.add_widget(vid_card)

        # ── Status / progress ──
        self.status_label = Label(
            text="", color=MUTED, font_size=dp(13),
            size_hint_y=None, height=dp(0),
            halign='center', text_size=(Window.width - dp(32), None),
            markup=True
        )
        body.add_widget(self.status_label)

        self.progress = ProgressBar(
            max=100, value=0,
            size_hint_y=None, height=dp(0)
        )
        body.add_widget(self.progress)

        # ── Scan button ──
        self.scan_btn = self._rounded_btn("🎨  Scan for Album Covers", self._start_scan)
        self.scan_btn.disabled = True
        body.add_widget(self.scan_btn)

        # ── Results area ──
        self.results_label = Label(
            text="", color=TEXT, font_size=dp(16),
            bold=True, size_hint_y=None, height=dp(0),
            halign='left', text_size=(Window.width - dp(32), None)
        )
        body.add_widget(self.results_label)

        self.tracks_container = BoxLayout(
            orientation='vertical', spacing=dp(8),
            size_hint_y=None, height=0
        )
        body.add_widget(self.tracks_container)

        self.export_btn = self._ghost_btn("⬇  Download CSV", self._export_csv)
        self.export_btn.opacity = 0
        self.export_btn.disabled = True
        body.add_widget(self.export_btn)

    # ── Helpers ──
    def _card(self):
        from kivy.uix.boxlayout import BoxLayout as BL
        c = BL(orientation='vertical', padding=dp(14), spacing=dp(8),
               size_hint_y=None)
        c.bind(minimum_height=c.setter('height'))
        with c.canvas.before:
            from kivy.graphics import Color, RoundedRectangle, Line
            Color(*SURFACE)
            c._bg = RoundedRectangle(pos=c.pos, size=c.size, radius=[dp(16)])
            Color(*BORDER)
            c._border = Line(rounded_rectangle=[c.x, c.y, c.width, c.height, dp(16)], width=1)
        def _update(inst, val):
            inst._bg.pos = inst.pos; inst._bg.size = inst.size
            inst._border.rounded_rectangle = [inst.x, inst.y, inst.width, inst.height, dp(16)]
        c.bind(pos=_update, size=_update)
        return c

    def _section_label(self, text):
        l = Label(text=text, color=MUTED, font_size=dp(11), bold=True,
                  size_hint_y=None, height=dp(22),
                  halign='left', text_size=(Window.width - dp(64), None))
        return l

    def _rounded_btn(self, text, callback):
        from kivy.uix.button import Button
        from kivy.graphics import Color, RoundedRectangle
        btn = Button(
            text=text, bold=True, font_size=dp(15),
            background_normal='', background_color=(0,0,0,0),
            color=TEXT, size_hint_y=None, height=dp(52)
        )
        with btn.canvas.before:
            btn._col = Color(*ACCENT)
            btn._rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(14)])
        def _upd(inst, val):
            inst._rect.pos = inst.pos; inst._rect.size = inst.size
        btn.bind(pos=_upd, size=_upd)
        btn.bind(on_release=lambda x: callback())
        return btn

    def _ghost_btn(self, text, callback):
        from kivy.uix.button import Button
        from kivy.graphics import Color, RoundedRectangle
        btn = Button(
            text=text, bold=True, font_size=dp(14),
            background_normal='', background_color=(0,0,0,0),
            color=MUTED, size_hint_y=None, height=dp(46)
        )
        with btn.canvas.before:
            btn._col = Color(*SURFACE2)
            btn._rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(12)])
        def _upd(inst, val):
            inst._rect.pos = inst.pos; inst._rect.size = inst.size
        btn.bind(pos=_upd, size=_upd)
        btn.bind(on_release=lambda x: callback())
        return btn

    # ── API key ──
    def _save_key(self):
        key = self.api_input.text.strip()
        if key:
            self.store.put("key", value=key)
            self._set_status("[color=#22c55e]✓ API key saved[/color]")

    def _get_key(self):
        return self.api_input.text.strip() or (
            self.store.get("key")["value"] if self.store.exists("key") else "")

    # ── File picker ──
    def _open_picker(self):
        if ANDROID:
            request_permissions([Permission.READ_EXTERNAL_STORAGE,
                                  Permission.WRITE_EXTERNAL_STORAGE])
            start_path = primary_external_storage_path()
        else:
            start_path = str(Path.home())

        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        fc = FileChooserListView(
            path=start_path,
            filters=["*.mp4","*.MP4","*.mov","*.MOV","*.avi","*.AVI",
                     "*.mkv","*.MKV","*.webm","*.3gp","*.m4v"],
            size_hint_y=1
        )
        content.add_widget(fc)

        btn_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        select_btn = Button(text="Select", bold=True, font_size=dp(14),
                            background_color=list(ACCENT) + [1],
                            background_normal='', color=TEXT)
        cancel_btn = Button(text="Cancel", font_size=dp(14),
                            background_color=list(SURFACE2) + [1],
                            background_normal='', color=MUTED)
        btn_row.add_widget(select_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)

        popup = Popup(title="Select Video File",
                      content=content,
                      size_hint=(0.95, 0.85),
                      background_color=list(SURFACE) + [1])

        def on_select(inst):
            if fc.selection:
                self._load_video(fc.selection[0])
            popup.dismiss()

        select_btn.bind(on_release=on_select)
        cancel_btn.bind(on_release=lambda x: popup.dismiss())
        fc.bind(on_submit=lambda inst, sel, touch: on_select(inst))
        popup.open()

    def _load_video(self, path):
        self.video_path = path
        name = Path(path).name
        size = Path(path).stat().st_size
        size_str = f"{size//(1024*1024)} MB" if size > 1024*1024 else f"{size//1024} KB"
        self.video_label.text = f"[b]{name}[/b]  [{size_str}]"
        self.video_label.markup = True
        self.video_label.color = TEXT
        self.scan_btn.disabled = False
        self.frames = []
        self._set_status(f"[color=#c084fc]Video loaded. Tap Scan to begin.[/color]")

    # ── Scan ──
    def _start_scan(self):
        key = self._get_key()
        if not key:
            self._set_status("[color=#ef4444]⚠ Please enter your Anthropic API key first.[/color]")
            return
        if not self.video_path:
            self._set_status("[color=#ef4444]⚠ Please select a video first.[/color]")
            return

        self.scan_btn.disabled = True
        self.tracks_container.clear_widgets()
        self.tracks_container.height = 0
        self.results_label.text = ""
        self.results_label.height = dp(0)
        self.export_btn.opacity = 0
        self.export_btn.disabled = True
        self._show_progress(True)
        self._set_status("Extracting frames…")
        self._set_progress(5)

        threading.Thread(target=self._scan_thread, args=(key,), daemon=True).start()

    def _scan_thread(self, key):
        try:
            self._ui_status("Extracting frames from video…")
            self._ui_progress(15)
            frames, duration, count = self._extract_frames(self.video_path)
            self.frames = frames

            self._ui_status(f"Sending {len(frames)} frames to Claude AI (1 per 3s of video)…")
            self._ui_progress(50)
            tracks = self._call_claude(frames, duration, key)

            self._ui_progress(95)
            Clock.schedule_once(lambda dt: self._on_results(tracks), 0)

        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_error(str(e)), 0)

    def _extract_frames(self, path):
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise ValueError("Cannot open video file.")
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps   = cap.get(cv2.CAP_PROP_FPS) or 30
        dur   = total / fps

        # 1 frame per 3 seconds of video, min 4, max 24
        count = max(4, min(24, int(dur / 3)))

        start = dur * 0.03
        end   = dur * 0.97
        step  = (end - start) / max(count - 1, 1)
        frames = []
        for i in range(count):
            t = start + step * i
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.resize(frame, (640, 360))
            ok2, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ok2:
                continue
            b64 = base64.b64encode(buf.tobytes()).decode()
            mm, ss = int(t // 60), int(t % 60)
            frames.append({"b64": b64, "timestamp": f"{mm:02d}:{ss:02d}"})
        cap.release()
        if not frames:
            raise ValueError("Could not extract frames from video.")
        return frames, dur, count

    def _call_claude(self, frames, duration, key):
        client = anthropic.Anthropic(api_key=key)
        content = [{"type": "image",
                     "source": {"type": "base64", "media_type": "image/jpeg", "data": f["b64"]}}
                   for f in frames]
        frame_list = "\n".join(f"  Frame {i+1} @ {f['timestamp']}"
                                for i, f in enumerate(frames))
        prompt = f"""You are an expert music album cover identifier.

I am giving you {len(frames)} frames from a video (~{round(duration)}s):
{frame_list}

Examine EVERY frame for visible album covers, record sleeves, vinyl jackets, CD cases, or cassette covers — physical or on-screen.

For each distinct album cover you can identify provide:
1. frameNumbers — frame(s) it appears in
2. timestamp — first appearance (MM:SS)
3. artist — artist/band name
4. album — album title
5. year — release year (4 digits)
6. usedPrice — estimated used price in USD (Discogs/eBay), e.g. "$8.99"
7. confidence — "high", "medium", or "low"

RULES:
- Only report albums you can actually SEE — never invent
- List each album ONCE (earliest timestamp)
- No duplicates
- Empty tracks array if nothing found

Respond ONLY with raw valid JSON, no markdown:
{{"tracks":[{{"frameNumbers":[1],"timestamp":"00:00","artist":"Artist","album":"Album","year":"YYYY","usedPrice":"$0.00","confidence":"high"}}]}}"""

        content.append({"type": "text", "text": prompt})
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": content}]
        )
        raw   = "".join(b.text for b in resp.content if hasattr(b, "text"))
        clean = raw.replace("```json","").replace("```","").strip()
        parsed = json.loads(clean)
        if not isinstance(parsed.get("tracks"), list):
            raise ValueError("Unexpected response from AI.")
        return parsed["tracks"]

    # ── Results ──
    @mainthread
    def _on_results(self, tracks):
        self._show_progress(False)
        self.scan_btn.disabled = False
        self.tracks = tracks

        if not tracks:
            self._set_status(
                "[color=#fca5a5]No album covers detected.\n"
                "Try a video where covers are clearly visible and front-facing.[/color]")
            return

        self._set_status(f"[color=#22c55e]✓ {len(tracks)} album(s) identified![/color]")
        self.results_label.text = f"Albums Found"
        self.results_label.height = dp(36)

        for i, t in enumerate(tracks):
            conf_color = {"high":"#22c55e","medium":"#fbbf24","low":"#ef4444"}.get(
                t.get("confidence",""), "#6b6b8a")
            card = self._card()
            row1 = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(8))
            row1.add_widget(Label(
                text=f"[b]#{i+1:02d}[/b]",
                markup=True, color=list(ACCENT3)+[1],
                font_size=dp(11), size_hint_x=None, width=dp(36),
                halign='left', text_size=(dp(36), None)
            ))
            row1.add_widget(Label(
                text=f"⏱ {t.get('timestamp','??:??')}",
                color=MUTED, font_size=dp(11),
                halign='left', text_size=(dp(80), None), size_hint_x=None, width=dp(80)
            ))
            row1.add_widget(Label(
                text=f"[color={conf_color}]{t.get('confidence','?').upper()}[/color]",
                markup=True, font_size=dp(11),
                halign='right'
            ))
            card.add_widget(row1)
            card.add_widget(Label(
                text=f"[b]{t.get('artist','Unknown')}[/b]",
                markup=True, color=TEXT, font_size=dp(15),
                size_hint_y=None, height=dp(24),
                halign='left', text_size=(Window.width - dp(64), None)
            ))
            card.add_widget(Label(
                text=t.get('album','Unknown'),
                color=MUTED, font_size=dp(13),
                size_hint_y=None, height=dp(20),
                halign='left', text_size=(Window.width - dp(64), None)
            ))
            chips = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(8))
            chips.add_widget(Label(
                text=f"📅 {t.get('year','?')}",
                color=list(GREEN)+[1], font_size=dp(12),
                size_hint_x=None, width=dp(80)
            ))
            chips.add_widget(Label(
                text=f"💰 {t.get('usedPrice','?')}",
                color=list(ACCENT3)+[1], font_size=dp(12),
                size_hint_x=None, width=dp(100)
            ))
            card.add_widget(chips)

            self.tracks_container.add_widget(card)

        # Recalculate container height
        self.tracks_container.height = sum(
            c.height + dp(8) for c in self.tracks_container.children)

        self.export_btn.opacity = 1
        self.export_btn.disabled = False

    @mainthread
    def _on_error(self, msg):
        self._show_progress(False)
        self.scan_btn.disabled = False
        self._set_status(f"[color=#ef4444]⚠  {msg}[/color]")

    # ── Export ──
    def _export_csv(self):
        if not self.tracks:
            return
        if ANDROID:
            out_dir = primary_external_storage_path()
        else:
            out_dir = str(Path.home() / "Downloads")
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        stem = Path(self.video_path).stem if self.video_path else "video"
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        out  = Path(out_dir) / f"{stem}_albums_{ts}.csv"

        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "#","Timestamp","Artist","Album",
                "Year Released","Used Retail Price (USD)","Confidence"])
            w.writeheader()
            for i, t in enumerate(self.tracks, 1):
                w.writerow({
                    "#": i,
                    "Timestamp":               t.get("timestamp",""),
                    "Artist":                  t.get("artist",""),
                    "Album":                   t.get("album",""),
                    "Year Released":           t.get("year",""),
                    "Used Retail Price (USD)": t.get("usedPrice",""),
                    "Confidence":              t.get("confidence",""),
                })
        self._set_status(f"[color=#22c55e]✓ Saved: {out.name}[/color]")

    # ── UI helpers ──
    def _set_status(self, msg):
        self.status_label.text = msg
        self.status_label.height = dp(40) if msg else dp(0)

    def _set_progress(self, val):
        self.progress.value = val

    def _show_progress(self, show):
        self.progress.height = dp(10) if show else dp(0)
        self.progress.value  = 0 if not show else self.progress.value

    @mainthread
    def _ui_status(self, msg):
        self._set_status(f"[color=#c084fc]{msg}[/color]")

    @mainthread
    def _ui_progress(self, val):
        self._set_progress(val)


# ── App ───────────────────────────────────────────────────────────────────────
class AlbumScannerApp(App):
    def build(self):
        Window.clearcolor = BG
        if ANDROID:
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.INTERNET,
            ])
        return MainScreen()

    def on_start(self):
        pass


if __name__ == "__main__":
    AlbumScannerApp().run()
