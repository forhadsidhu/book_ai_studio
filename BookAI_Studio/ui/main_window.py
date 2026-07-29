import os
import sys
import json
import threading
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QTextEdit, QPlainTextEdit, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QSlider,
    QTabWidget, QFrame, QFileDialog, QMessageBox, QDialog,
    QDialogButtonBox, QLineEdit, QFormLayout, QGroupBox, QScrollArea,
    QProgressBar, QToolBar, QStatusBar, QInputDialog, QSizePolicy,
    QGridLayout, QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import (
    QFont, QIcon, QPixmap, QImage, QAction, QColor,
    QTextCharFormat, QTextBlockFormat, QTextCursor,
)

from ui.styles import DARK_THEME
from models.llm import LLMClient
from models.book_parser import BookParser
from models.tts_engine import TTSEngine
from models.image_gen import ImageGenerator
from models.video_gen import VideoGenerator
from utils.storage import ProjectStorage
from config import load_config, save_config, IMAGES_DIR, VIDEO_DIR


# ─── Worker Threads ───────────────────────────────────────────────────────────

class LLMWorker(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, llm: LLMClient, mode: str, **kwargs):
        super().__init__()
        self.llm = llm
        self.mode = mode
        self.kwargs = kwargs
        self._result = ""

    def run(self):
        try:
            if self.mode == "continue":
                gen = self.llm.continue_chapter(**self.kwargs)
            elif self.mode == "generate_chapter":
                gen = self.llm.generate_chapter(**self.kwargs)
            elif self.mode == "suggestions":
                suggestions = self.llm.get_suggestions(**self.kwargs)
                self.finished.emit(json.dumps(suggestions))
                return
            elif self.mode == "extract_chars":
                chars = self.llm.extract_characters(**self.kwargs)
                self.finished.emit(json.dumps(chars))
                return
            elif self.mode == "extract_info":
                info = self.llm.extract_story_info(**self.kwargs)
                self.finished.emit(json.dumps(info))
                return
            elif self.mode == "image_prompt":
                prompt = self.llm.generate_image_prompt(**self.kwargs)
                self.finished.emit(prompt)
                return
            else:
                return

            for chunk in gen:
                self._result += chunk
                self.chunk_received.emit(chunk)
            self.finished.emit(self._result)
        except Exception as e:
            self.error.emit(str(e))


class ImageWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, image_gen: ImageGenerator, mode: str, **kwargs):
        super().__init__()
        self.image_gen = image_gen
        self.mode = mode
        self.kwargs = kwargs

    def run(self):
        try:
            if self.mode == "scene":
                path = self.image_gen.generate_scene(**self.kwargs)
            elif self.mode == "avatar":
                path = self.image_gen.generate_character_avatar(**self.kwargs)
            elif self.mode == "custom":
                path = self.image_gen.generate(**self.kwargs)
            else:
                path = self.image_gen.generate(**self.kwargs)
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


class TTSWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, tts: TTSEngine, text: str, filename: str = None):
        super().__init__()
        self.tts = tts
        self.text = text
        self.filename = filename

    def run(self):
        try:
            path = self.tts.save_to_file(self.text, self.filename)
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


class VideoWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_gen: VideoGenerator, images: list, title: str, audio_path: str = None):
        super().__init__()
        self.video_gen = video_gen
        self.images = images
        self.title = title
        self.audio_path = audio_path

    def run(self):
        try:
            path = self.video_gen.create_book_trailer(self.images, self.audio_path, self.title)
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


# ─── Character Dialog ─────────────────────────────────────────────────────────

class CharacterDialog(QDialog):
    def __init__(self, parent=None, character: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Character Editor")
        self.setMinimumWidth(560)
        self.setMinimumHeight(640)
        self.character = character or {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        inner = QWidget()
        form = QFormLayout(inner)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setVerticalSpacing(10)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        # ── Basic Info ──────────────────────────────────────────────────────
        self.name_edit = QLineEdit(self.character.get("name", ""))
        self.name_edit.setPlaceholderText("Full character name")
        form.addRow("Name *:", self.name_edit)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["Protagonist", "Antagonist", "Supporting", "Minor", "Narrator"])
        role = self.character.get("role", "Supporting")
        idx = self.role_combo.findText(role, Qt.MatchFlag.MatchContains)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)
        form.addRow("Role:", self.role_combo)

        age_gender = QHBoxLayout()
        self.age_edit = QLineEdit(str(self.character.get("age", "")))
        self.age_edit.setPlaceholderText("e.g. 28")
        self.age_edit.setFixedWidth(80)
        self.gender_edit = QLineEdit(self.character.get("gender", ""))
        self.gender_edit.setPlaceholderText("e.g. Female, Male, Non-binary…")
        age_gender.addWidget(self.age_edit)
        age_gender.addWidget(QLabel("Gender:"))
        age_gender.addWidget(self.gender_edit)
        age_gender.addStretch()
        form.addRow("Age:", age_gender)

        # ── Appearance & Personality ────────────────────────────────────────
        self.appearance_edit = QTextEdit()
        self.appearance_edit.setPlaceholderText("Physical description — hair, eyes, build, clothing style…")
        self.appearance_edit.setPlainText(self.character.get("appearance", ""))
        self.appearance_edit.setFixedHeight(80)
        form.addRow("Appearance:", self.appearance_edit)

        self.personality_edit = QTextEdit()
        self.personality_edit.setPlaceholderText("Personality, temperament, quirks, habits…")
        self.personality_edit.setPlainText(self.character.get("personality", ""))
        self.personality_edit.setFixedHeight(80)
        form.addRow("Personality:", self.personality_edit)

        self.traits_edit = QLineEdit(", ".join(self.character.get("traits", [])))
        self.traits_edit.setPlaceholderText("brave, stubborn, witty, loyal…")
        form.addRow("Key Traits:", self.traits_edit)

        # ── Backstory & Motivation ──────────────────────────────────────────
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("General description or bio…")
        self.desc_edit.setPlainText(self.character.get("description", ""))
        self.desc_edit.setFixedHeight(90)
        form.addRow("Bio / Description:", self.desc_edit)

        self.backstory_edit = QTextEdit()
        self.backstory_edit.setPlaceholderText("Character backstory — history, upbringing, key past events…")
        self.backstory_edit.setPlainText(self.character.get("backstory", ""))
        self.backstory_edit.setFixedHeight(90)
        form.addRow("Backstory:", self.backstory_edit)

        self.goals_edit = QTextEdit()
        self.goals_edit.setPlaceholderText("What does this character want? Short-term and long-term goals…")
        self.goals_edit.setPlainText(self.character.get("goals", ""))
        self.goals_edit.setFixedHeight(70)
        form.addRow("Goals:", self.goals_edit)

        self.motivation_edit = QTextEdit()
        self.motivation_edit.setPlaceholderText("Why do they pursue those goals? Inner drive, fear, love…")
        self.motivation_edit.setPlainText(self.character.get("motivation", ""))
        self.motivation_edit.setFixedHeight(70)
        form.addRow("Motivation:", self.motivation_edit)

        self.arc_edit = QLineEdit(self.character.get("character_arc", ""))
        self.arc_edit.setPlaceholderText("e.g. From coward → hero, from idealist → cynic…")
        form.addRow("Character Arc:", self.arc_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Anything else — relationships, secrets, language, habits…")
        self.notes_edit.setPlainText(self.character.get("notes", ""))
        self.notes_edit.setFixedHeight(70)
        form.addRow("Notes:", self.notes_edit)

        # ── Avatar ──────────────────────────────────────────────────────────
        self.avatar_label = QLabel("No avatar")
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setStyleSheet(
            "border: 1px solid #2d2d4e; border-radius: 8px; padding: 10px; color: #64748b;"
        )
        self.avatar_label.setFixedHeight(120)
        if self.character.get("avatar_path") and os.path.exists(self.character["avatar_path"]):
            pix = QPixmap(self.character["avatar_path"]).scaled(
                110, 110, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.avatar_label.setPixmap(pix)
        form.addRow("Avatar:", self.avatar_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_character(self) -> dict:
        c = self.character.copy()
        c["name"] = self.name_edit.text().strip()
        c["role"] = self.role_combo.currentText()
        c["age"] = self.age_edit.text().strip()
        c["gender"] = self.gender_edit.text().strip()
        c["appearance"] = self.appearance_edit.toPlainText().strip()
        c["personality"] = self.personality_edit.toPlainText().strip()
        c["traits"] = [t.strip() for t in self.traits_edit.text().split(",") if t.strip()]
        c["description"] = self.desc_edit.toPlainText().strip()
        c["backstory"] = self.backstory_edit.toPlainText().strip()
        c["goals"] = self.goals_edit.toPlainText().strip()
        c["motivation"] = self.motivation_edit.toPlainText().strip()
        c["character_arc"] = self.arc_edit.text().strip()
        c["notes"] = self.notes_edit.toPlainText().strip()
        return c


# ─── Settings Dialog ──────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    def __init__(self, parent=None, config: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        self.config = config or {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # ── OpenAI / API Keys ──────────────────────────────────────────────
        api_widget = QWidget()
        api_form = QFormLayout(api_widget)

        self.openai_key = QLineEdit(self.config.get("openai_api_key", ""))
        self.openai_key.setPlaceholderText("sk-…  (get from platform.openai.com)")
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_form.addRow("OpenAI API Key:", self.openai_key)

        show_btn = QPushButton("Show/Hide")
        show_btn.setFixedWidth(90)
        show_btn.clicked.connect(lambda: self.openai_key.setEchoMode(
            QLineEdit.EchoMode.Normal
            if self.openai_key.echoMode() == QLineEdit.EchoMode.Password
            else QLineEdit.EchoMode.Password
        ))
        api_form.addRow("", show_btn)

        key_hint = QLabel(
            "Used for: DALL-E 3 images (best quality), OpenAI TTS (human-like voices).\n"
            "Leave blank to use local Stable Diffusion / pyttsx3 instead."
        )
        key_hint.setWordWrap(True)
        key_hint.setStyleSheet("color: #64748b; font-size: 11px;")
        api_form.addRow(key_hint)

        self.use_openai_images = QCheckBox("Use DALL-E 3 for image generation (recommended)")
        self.use_openai_images.setChecked(self.config.get("use_openai_images", True))
        api_form.addRow(self.use_openai_images)

        self.openai_img_quality = QComboBox()
        self.openai_img_quality.addItems(["standard", "hd"])
        self.openai_img_quality.setCurrentText(self.config.get("openai_image_quality", "standard"))
        api_form.addRow("DALL-E 3 quality:", self.openai_img_quality)

        tabs.addTab(api_widget, "🔑 API Keys")

        # ── LM Studio ─────────────────────────────────────────────────────
        llm_widget = QWidget()
        llm_form = QFormLayout(llm_widget)
        self.lm_url = QLineEdit(self.config.get("lm_studio_url", "http://localhost:1234/v1"))
        self.lm_model = QLineEdit(self.config.get("lm_studio_model", "local-model"))
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(200, 4000)
        self.max_tokens.setValue(self.config.get("max_tokens", 1200))
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.1, 2.0)
        self.temperature.setSingleStep(0.05)
        self.temperature.setValue(self.config.get("temperature", 0.85))
        llm_form.addRow("LM Studio URL:", self.lm_url)
        llm_form.addRow("Model name:", self.lm_model)
        llm_form.addRow("Max tokens:", self.max_tokens)
        llm_form.addRow("Temperature:", self.temperature)
        tabs.addTab(llm_widget, "🤖 AI Model")

        # ── Images ────────────────────────────────────────────────────────
        img_widget = QWidget()
        img_form = QFormLayout(img_widget)

        self.image_engine = QComboBox()
        self.image_engine.addItems([
            "automatic1111 (local SD WebUI — no filter, no internet)",
            "local_sd      (diffusers + torch — no filter, no internet)",
            "pollinations  (free internet, has safety filter)",
            "openai        (DALL-E 3 — paid key, has filter)",
        ])
        engine_map = {
            "automatic1111": 0, "local_sd": 1, "pollinations": 2, "openai": 3
        }
        self.image_engine.setCurrentIndex(
            engine_map.get(self.config.get("image_engine", "automatic1111"), 0)
        )
        img_form.addRow("Image Engine:", self.image_engine)

        img_hint = QLabel(
            "AUTOMATIC1111 and local_sd run 100% on your PC — no internet, no filters.\n"
            "Best for adult/uncensored content. See SETUP_GUIDE.txt for install steps."
        )
        img_hint.setWordWrap(True)
        img_hint.setStyleSheet("color: #64748b; font-size: 11px;")
        img_form.addRow(img_hint)

        self.pollinations_model = QComboBox()
        self.pollinations_model.addItems(["flux", "turbo", "dreamshaper", "stable-diffusion"])
        self.pollinations_model.setCurrentText(self.config.get("pollinations_model", "flux"))
        img_form.addRow("Pollinations model:", self.pollinations_model)

        img_form.addRow(QLabel("─── Stable Diffusion (if using local / A1111) ───"))
        self.sd_url = QLineEdit(self.config.get("sd_api_url", "http://localhost:7860"))
        self.sd_model_path = QLineEdit(self.config.get("sd_model_path", ""))
        img_form.addRow("AUTOMATIC1111 URL:", self.sd_url)
        img_form.addRow("Local model path:", self.sd_model_path)

        self.openai_img_quality2 = QComboBox()
        self.openai_img_quality2.addItems(["standard", "hd"])
        self.openai_img_quality2.setCurrentText(self.config.get("openai_image_quality", "standard"))
        img_form.addRow("DALL-E 3 quality:", self.openai_img_quality2)

        tabs.addTab(img_widget, "🖼 Images")

        # ── TTS / Audio ────────────────────────────────────────────────────
        tts_widget = QWidget()
        tts_form = QFormLayout(tts_widget)

        self.tts_engine_sel = QComboBox()
        self.tts_engine_sel.addItems(["openai", "gtts", "pyttsx3"])
        self.tts_engine_sel.setCurrentText(self.config.get("tts_engine", "openai"))
        tts_form.addRow("TTS Engine:", self.tts_engine_sel)

        self.tts_voice_sel = QComboBox()
        self.tts_voice_sel.addItems(["nova", "shimmer", "alloy", "echo", "fable", "onyx"])
        self.tts_voice_sel.setCurrentText(self.config.get("tts_voice", "nova"))
        tts_form.addRow("OpenAI Voice:", self.tts_voice_sel)

        self.tts_speed_spin = QDoubleSpinBox()
        self.tts_speed_spin.setRange(0.25, 4.0)
        self.tts_speed_spin.setSingleStep(0.25)
        self.tts_speed_spin.setValue(float(self.config.get("tts_rate", 1.0)))
        tts_form.addRow("OpenAI Speed (0.25–4.0):", self.tts_speed_spin)

        self.pyttsx3_rate = QSpinBox()
        self.pyttsx3_rate.setRange(50, 300)
        self.pyttsx3_rate.setValue(self.config.get("tts_pyttsx3_rate", 150))
        tts_form.addRow("pyttsx3 Rate (WPM):", self.pyttsx3_rate)

        voice_hint = QLabel(
            "Voices: nova (warm female), shimmer (soft female), alloy (neutral),\n"
            "echo (male), fable (British male), onyx (deep male)"
        )
        voice_hint.setStyleSheet("color: #64748b; font-size: 11px;")
        tts_form.addRow(voice_hint)
        tabs.addTab(tts_widget, "🔊 Audio")

        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        c = self.config.copy()
        c["openai_api_key"] = self.openai_key.text().strip()
        c["use_openai_images"] = c["openai_api_key"] != ""
        c["openai_image_quality"] = self.openai_img_quality.currentText()
        c["lm_studio_url"] = self.lm_url.text().strip()
        c["lm_studio_model"] = self.lm_model.text().strip()
        c["max_tokens"] = self.max_tokens.value()
        c["temperature"] = self.temperature.value()
        engine_reverse = {0: "automatic1111", 1: "local_sd", 2: "pollinations", 3: "openai"}
        c["image_engine"] = engine_reverse.get(self.image_engine.currentIndex(), "automatic1111")
        c["pollinations_model"] = self.pollinations_model.currentText()
        c["sd_api_url"] = self.sd_url.text().strip()
        c["use_sd_api"] = c["image_engine"] == "automatic1111"
        c["sd_model_path"] = self.sd_model_path.text().strip()
        c["tts_engine"] = self.tts_engine_sel.currentText()
        c["tts_voice"] = self.tts_voice_sel.currentText()
        c["tts_rate"] = self.tts_speed_spin.value()
        c["tts_pyttsx3_rate"] = self.pyttsx3_rate.value()
        return c


# ─── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self._init_services()
        self.project = self.storage.new_project()
        self.current_chapter = None
        self.current_chapter_idx = -1
        self._worker = None
        self._img_worker = None
        self._tts_worker = None
        self._vid_worker = None
        self._speaking = False

        self.setWindowTitle("BookAI Studio")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(DARK_THEME)
        self._build_menu()
        self._build_toolbar()
        self._build_status_bar()
        self._build_ui()
        self._update_status()

        # Auto-load last project
        if self.config.get("last_project") and os.path.exists(self.config["last_project"]):
            try:
                self.project = self.storage.load_project(self.config["last_project"])
                self._refresh_all()
            except Exception:
                pass

    def _init_services(self):
        self.llm = LLMClient(self.config["lm_studio_url"], self.config["lm_studio_model"])
        self.parser = BookParser()
        # Pass full config so engines can use OpenAI key, voice, speed etc.
        self.tts = TTSEngine(config=self.config)
        self.image_gen = ImageGenerator(
            config=self.config,
            use_api=self.config.get("use_sd_api", False),
            api_url=self.config.get("sd_api_url", "http://localhost:7860"),
            model_path=self.config.get("sd_model_path", ""),
        )
        self.video_gen = VideoGenerator()
        self.storage = ProjectStorage()

    def _make_action(self, text, slot=None, shortcut=None):
        action = QAction(text, self)
        if slot:
            action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(shortcut)
        return action

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        file_menu.addAction(self._make_action("New Project", self._new_project, "Ctrl+N"))
        file_menu.addAction(self._make_action("Open Project", self._open_project, "Ctrl+O"))
        file_menu.addAction(self._make_action("Save Project", self._save_project, "Ctrl+S"))
        file_menu.addSeparator()
        file_menu.addAction(self._make_action("Import Book (PDF/EPUB/TXT)", self._import_book))
        file_menu.addSeparator()
        file_menu.addAction(self._make_action("Exit", self.close))

        edit_menu = menubar.addMenu("Edit")
        edit_menu.addAction(self._make_action("Add Chapter", self._add_chapter))
        edit_menu.addAction(self._make_action("Delete Chapter", self._delete_chapter))

        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction(self._make_action("Settings", self._open_settings))
        tools_menu.addAction(self._make_action("Check LM Studio Connection", self._check_connection))

        help_menu = menubar.addMenu("Help")
        help_menu.addAction(self._make_action("Setup Guide", self._show_setup_guide))
        help_menu.addAction(self._make_action("About", self._show_about))

    def _build_toolbar(self):
        tb = QToolBar()
        tb.setIconSize(QSize(16, 16))
        tb.setMovable(False)
        self.addToolBar(tb)

        for label, slot in [
            ("📁 New", self._new_project),
            ("📂 Open", self._open_project),
            ("💾 Save", self._save_project),
            ("|", None),
            ("📖 Import Book", self._import_book),
            ("|", None),
            ("▶ Generate Chapter", self._generate_full_chapter),
            ("✍ Continue Writing", self._continue_writing),
            ("|", None),
            ("⚙ Settings", self._open_settings),
        ]:
            if label == "|":
                tb.addSeparator()
            else:
                btn = QPushButton(label)
                btn.setStyleSheet("QPushButton { padding: 6px 12px; font-size: 12px; }")
                if slot:
                    btn.clicked.connect(slot)
                tb.addWidget(btn)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Project title
        self.project_title_label = QLabel("New Project")
        self.project_title_label.setObjectName("title")
        self.project_title_label.setStyleSheet("padding: 14px 16px; font-size: 15px; font-weight: 700; color: #e2e8f0; border-bottom: 1px solid #2d2d4e;")
        self.project_title_label.setWordWrap(True)
        sidebar_layout.addWidget(self.project_title_label)

        # Chapters section
        chap_header = QWidget()
        chap_header_layout = QHBoxLayout(chap_header)
        chap_header_layout.setContentsMargins(12, 8, 8, 4)
        chap_label = QLabel("CHAPTERS")
        chap_label.setObjectName("section")
        chap_header_layout.addWidget(chap_label)
        add_chap_btn = QPushButton("+")
        add_chap_btn.setFixedSize(22, 22)
        add_chap_btn.setStyleSheet("QPushButton { padding: 0; font-size: 14px; border-radius: 4px; }")
        add_chap_btn.clicked.connect(self._add_chapter)
        chap_header_layout.addWidget(add_chap_btn)
        sidebar_layout.addWidget(chap_header)

        self.chapter_list = QListWidget()
        # No max height — show all chapters
        self.chapter_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.chapter_list.currentRowChanged.connect(self._on_chapter_selected)
        sidebar_layout.addWidget(self.chapter_list, stretch=3)

        # Characters section
        char_header = QWidget()
        char_header_layout = QHBoxLayout(char_header)
        char_header_layout.setContentsMargins(12, 8, 8, 4)
        char_label = QLabel("CHARACTERS")
        char_label.setObjectName("section")
        char_header_layout.addWidget(char_label)
        add_char_btn = QPushButton("+")
        add_char_btn.setFixedSize(22, 22)
        add_char_btn.setStyleSheet("QPushButton { padding: 0; font-size: 14px; border-radius: 4px; }")
        add_char_btn.clicked.connect(self._add_character_manually)
        char_header_layout.addWidget(add_char_btn)
        del_char_btn = QPushButton("−")
        del_char_btn.setFixedSize(22, 22)
        del_char_btn.setStyleSheet("QPushButton { padding: 0; font-size: 14px; border-radius: 4px; color: #f87171; }")
        del_char_btn.clicked.connect(self._delete_selected_character)
        char_header_layout.addWidget(del_char_btn)
        sidebar_layout.addWidget(char_header)

        self.char_list = QListWidget()
        # No max height — show all characters
        self.char_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.char_list.itemDoubleClicked.connect(self._edit_character)
        sidebar_layout.addWidget(self.char_list, stretch=2)

        # Writing style
        style_label = QLabel("STYLE")
        style_label.setObjectName("section")
        style_label.setStyleSheet("padding: 8px 12px 4px; color: #64748b; font-size: 10px; font-weight: 600; letter-spacing: 1px;")
        sidebar_layout.addWidget(style_label)

        self.style_combo = QComboBox()
        self.style_combo.setStyleSheet("margin: 0 8px;")
        self.style_combo.addItems([
            "Dark Fantasy", "Epic Fantasy", "Sci-Fi", "Romance",
            "Mystery/Thriller", "Horror", "Historical Fiction",
            "Contemporary", "Erotica", "Adventure",
        ])
        sidebar_layout.addWidget(self.style_combo)
        main_layout.addWidget(sidebar)

        # ── Main Content ──────────────────────────────────────────────────────
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(content_splitter)

        # Center: tabs
        self.tabs = QTabWidget()
        content_splitter.addWidget(self.tabs)

        # ── Write Tab ─────────────────────────────────────────────────────────
        write_widget = QWidget()
        write_layout = QVBoxLayout(write_widget)
        write_layout.setContentsMargins(0, 0, 0, 0)

        # Chapter header
        chap_bar = QWidget()
        chap_bar.setStyleSheet("background: #16162a; border-bottom: 1px solid #2d2d4e; padding: 4px;")
        chap_bar_layout = QHBoxLayout(chap_bar)
        self.chapter_title_edit = QLineEdit("Chapter Title")
        self.chapter_title_edit.setStyleSheet("font-size: 15px; font-weight: 600; background: transparent; border: none; color: #e2e8f0;")
        self.chapter_title_edit.textChanged.connect(self._on_chapter_title_changed)
        chap_bar_layout.addWidget(self.chapter_title_edit)
        self.word_count_label = QLabel("0 words")
        self.word_count_label.setStyleSheet("color: #475569; font-size: 11px;")
        chap_bar_layout.addWidget(self.word_count_label)
        write_layout.addWidget(chap_bar)

        # ── Formatting Toolbar ────────────────────────────────────────────────
        fmt_bar = QFrame()
        fmt_bar.setStyleSheet("background: #1e1e38; border-bottom: 1px solid #2d2d4e; padding: 4px 8px;")
        fmt_row = QHBoxLayout(fmt_bar)
        fmt_row.setContentsMargins(4, 2, 4, 2)
        fmt_row.setSpacing(4)

        def _fmt_btn(label, tip, slot):
            b = QPushButton(label)
            b.setToolTip(tip)
            b.setFixedSize(30, 28)
            b.setStyleSheet("QPushButton { font-weight: 700; font-size: 13px; padding: 0; border-radius: 5px; }")
            b.clicked.connect(slot)
            return b

        fmt_row.addWidget(_fmt_btn("B", "Bold (Ctrl+B)", self._fmt_bold))
        fmt_row.addWidget(_fmt_btn("I", "Italic (Ctrl+I)", self._fmt_italic))
        fmt_row.addWidget(_fmt_btn("U", "Underline (Ctrl+U)", self._fmt_underline))

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #2d2d4e;")
        fmt_row.addWidget(sep)

        fmt_row.addWidget(QLabel("Size:"))
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["10", "11", "12", "13", "14", "16", "18", "20", "24", "28", "32"])
        self.font_size_combo.setCurrentText("13")
        self.font_size_combo.setFixedWidth(60)
        self.font_size_combo.currentTextChanged.connect(self._fmt_font_size)
        fmt_row.addWidget(self.font_size_combo)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #2d2d4e;")
        fmt_row.addWidget(sep2)

        fmt_row.addWidget(QLabel("Spacing:"))
        self.para_spacing_spin = QSpinBox()
        self.para_spacing_spin.setRange(0, 40)
        self.para_spacing_spin.setValue(12)
        self.para_spacing_spin.setFixedWidth(55)
        self.para_spacing_spin.setToolTip("Paragraph spacing (px)")
        self.para_spacing_spin.valueChanged.connect(self._fmt_para_spacing)
        fmt_row.addWidget(self.para_spacing_spin)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet("color: #2d2d4e;")
        fmt_row.addWidget(sep3)

        self.heading_combo = QComboBox()
        self.heading_combo.addItems(["Normal", "Heading 1", "Heading 2", "Heading 3"])
        self.heading_combo.setFixedWidth(110)
        self.heading_combo.currentIndexChanged.connect(self._fmt_heading)
        fmt_row.addWidget(self.heading_combo)

        sep4 = QFrame()
        sep4.setFrameShape(QFrame.Shape.VLine)
        sep4.setStyleSheet("color: #2d2d4e;")
        fmt_row.addWidget(sep4)

        clear_btn = QPushButton("Clear ×")
        clear_btn.setToolTip("Clear all formatting")
        clear_btn.setFixedHeight(28)
        clear_btn.setStyleSheet("QPushButton { font-size: 11px; padding: 0 8px; border-radius: 5px; }")
        clear_btn.clicked.connect(self._fmt_clear)
        fmt_row.addWidget(clear_btn)

        fmt_row.addStretch()
        write_layout.addWidget(fmt_bar)

        # Editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Start writing here, or use the AI tools on the right to generate content...")
        editor_font = QFont("Georgia", 13)
        self.editor.setFont(editor_font)
        self.editor.document().setDefaultStyleSheet(
            "body { line-height: 1.8; } p { margin-bottom: 12px; }"
        )
        self.editor.textChanged.connect(self._on_editor_changed)
        write_layout.addWidget(self.editor)

        # Prompt bar
        prompt_frame = QFrame()
        prompt_frame.setStyleSheet("background: #16162a; border-top: 1px solid #2d2d4e; padding: 8px;")
        prompt_layout = QHBoxLayout(prompt_frame)
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Describe what happens next... e.g. 'The hero discovers the traitor's identity'")
        self.prompt_input.returnPressed.connect(self._continue_writing)
        prompt_layout.addWidget(self.prompt_input)
        cont_btn = QPushButton("▶ Continue")
        cont_btn.setObjectName("primary")
        cont_btn.clicked.connect(self._continue_writing)
        gen_btn = QPushButton("⚡ Generate Chapter")
        gen_btn.clicked.connect(self._generate_full_chapter)
        stop_btn = QPushButton("■ Stop")
        stop_btn.clicked.connect(self._stop_generation)
        for btn in [cont_btn, gen_btn, stop_btn]:
            prompt_layout.addWidget(btn)
        write_layout.addWidget(prompt_frame)
        self.tabs.addTab(write_widget, "✍ Write")

        # ── Characters Tab ────────────────────────────────────────────────────
        char_widget = QWidget()
        char_layout = QVBoxLayout(char_widget)

        char_toolbar = QHBoxLayout()
        add_char_btn2 = QPushButton("+ Add Character")
        add_char_btn2.setObjectName("primary")
        add_char_btn2.clicked.connect(self._add_character_manually)
        gen_avatar_btn = QPushButton("🖼 Generate Avatar")
        gen_avatar_btn.clicked.connect(self._generate_avatar_for_selected)
        char_toolbar.addWidget(add_char_btn2)
        char_toolbar.addWidget(gen_avatar_btn)
        char_toolbar.addStretch()
        char_layout.addLayout(char_toolbar)

        self.char_grid = QWidget()
        self.char_grid_layout = QGridLayout(self.char_grid)
        self.char_grid_layout.setSpacing(12)
        scroll = QScrollArea()
        scroll.setWidget(self.char_grid)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        char_layout.addWidget(scroll)
        self.tabs.addTab(char_widget, "👤 Characters")

        # ── Images Tab ────────────────────────────────────────────────────────
        img_widget = QWidget()
        img_layout = QVBoxLayout(img_widget)

        img_toolbar = QHBoxLayout()
        self.img_prompt_edit = QLineEdit()
        self.img_prompt_edit.setPlaceholderText("Image prompt — or leave blank to generate from current chapter")
        gen_img_btn = QPushButton("🖼 Generate Image")
        gen_img_btn.setObjectName("primary")
        gen_img_btn.clicked.connect(self._generate_scene_image)
        self.img_style_combo = QComboBox()
        self.img_style_combo.addItems(["Cinematic", "Dark Fantasy Art", "Realistic", "Oil Painting", "Anime", "Watercolor"])
        img_toolbar.addWidget(self.img_prompt_edit)
        img_toolbar.addWidget(self.img_style_combo)
        img_toolbar.addWidget(gen_img_btn)
        img_layout.addLayout(img_toolbar)

        self.img_progress = QProgressBar()
        self.img_progress.setVisible(False)
        self.img_progress.setMaximum(0)
        img_layout.addWidget(self.img_progress)

        self.img_grid = QWidget()
        self.img_grid_layout = QGridLayout(self.img_grid)
        img_scroll = QScrollArea()
        img_scroll.setWidget(self.img_grid)
        img_scroll.setWidgetResizable(True)
        img_scroll.setStyleSheet("QScrollArea { border: none; }")
        img_layout.addWidget(img_scroll)
        self.tabs.addTab(img_widget, "🖼 Images")

        # ── Audio Tab ─────────────────────────────────────────────────────────
        audio_widget = QWidget()
        audio_layout = QVBoxLayout(audio_widget)

        # Voice selection row
        voice_row = QHBoxLayout()
        voice_row.addWidget(QLabel("Engine:"))
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.addItems(["openai", "gtts", "pyttsx3"])
        self.tts_engine_combo.setCurrentText(self.config.get("tts_engine", "openai"))
        self.tts_engine_combo.setFixedWidth(100)
        self.tts_engine_combo.currentTextChanged.connect(self._on_tts_engine_changed)
        voice_row.addWidget(self.tts_engine_combo)

        voice_row.addWidget(QLabel("Voice:"))
        self.tts_voice_combo = QComboBox()
        self.tts_voice_combo.addItems(["nova", "shimmer", "alloy", "echo", "fable", "onyx"])
        self.tts_voice_combo.setCurrentText(self.config.get("tts_voice", "nova"))
        self.tts_voice_combo.setFixedWidth(110)
        self.tts_voice_combo.currentTextChanged.connect(lambda v: self.tts.set_voice(v))
        voice_row.addWidget(self.tts_voice_combo)

        voice_row.addWidget(QLabel("Speed:"))
        self.openai_speed_spin = QDoubleSpinBox()
        self.openai_speed_spin.setRange(0.25, 4.0)
        self.openai_speed_spin.setSingleStep(0.25)
        self.openai_speed_spin.setValue(float(self.config.get("tts_rate", 1.0)))
        self.openai_speed_spin.setFixedWidth(70)
        self.openai_speed_spin.setToolTip("Speed: 0.25 = slow, 1.0 = normal, 2.0 = fast (OpenAI TTS)\nFor pyttsx3: values > 10 are treated as words-per-minute (80–300)")
        self.openai_speed_spin.valueChanged.connect(lambda v: self.tts.set_openai_speed(v))
        voice_row.addWidget(self.openai_speed_spin)

        voice_row.addStretch()
        audio_layout.addLayout(voice_row)

        audio_ctrl = QHBoxLayout()
        self.read_btn = QPushButton("▶ Read Chapter Aloud")
        self.read_btn.setObjectName("primary")
        self.read_btn.clicked.connect(self._read_aloud)
        self.stop_read_btn = QPushButton("■ Stop")
        self.stop_read_btn.clicked.connect(self._stop_reading)
        self.export_audio_btn = QPushButton("💾 Export as MP3")
        self.export_audio_btn.clicked.connect(self._export_audio)
        audio_ctrl.addWidget(self.read_btn)
        audio_ctrl.addWidget(self.stop_read_btn)
        audio_ctrl.addWidget(self.export_audio_btn)
        audio_ctrl.addStretch()
        audio_layout.addLayout(audio_ctrl)

        self.audio_progress = QProgressBar()
        self.audio_progress.setVisible(False)
        self.audio_progress.setMaximum(0)
        audio_layout.addWidget(self.audio_progress)

        self.audio_list = QListWidget()
        self.audio_list.setMaximumHeight(200)
        audio_layout.addWidget(QLabel("Exported Audio Files:"))
        audio_layout.addWidget(self.audio_list)

        audio_layout.addWidget(QLabel("Chapter Text Preview:"))
        self.audio_preview = QTextEdit()
        self.audio_preview.setReadOnly(True)
        self.audio_preview.setStyleSheet("font-size: 14px; line-height: 1.8;")
        audio_layout.addWidget(self.audio_preview)
        self.tabs.addTab(audio_widget, "🔊 Audio")

        # ── Video Tab ─────────────────────────────────────────────────────────
        video_widget = QWidget()
        video_layout = QVBoxLayout(video_widget)

        video_ctrl = QHBoxLayout()
        self.create_trailer_btn = QPushButton("🎬 Create Book Trailer")
        self.create_trailer_btn.setObjectName("primary")
        self.create_trailer_btn.clicked.connect(self._create_video)
        self.video_title_edit = QLineEdit()
        self.video_title_edit.setPlaceholderText("Video title...")
        video_ctrl.addWidget(self.video_title_edit)
        video_ctrl.addWidget(self.create_trailer_btn)
        video_layout.addLayout(video_ctrl)

        self.video_progress = QProgressBar()
        self.video_progress.setVisible(False)
        self.video_progress.setMaximum(0)
        video_layout.addWidget(self.video_progress)
        video_layout.addWidget(QLabel("Uses all generated scene images. Generate images first in the Images tab."))

        self.video_list = QListWidget()
        video_layout.addWidget(QLabel("Generated Videos:"))
        video_layout.addWidget(self.video_list)
        self.tabs.addTab(video_widget, "🎬 Video")

        # ── Right Panel: AI Suggestions ───────────────────────────────────────
        right_panel = QFrame()
        right_panel.setObjectName("sidebar")
        right_panel.setFixedWidth(260)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)

        right_title = QLabel("✦ AI Assistant")
        right_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #a78bfa; margin-bottom: 8px;")
        right_layout.addWidget(right_title)

        sugg_label = QLabel("STORY SUGGESTIONS")
        sugg_label.setObjectName("section")
        right_layout.addWidget(sugg_label)

        self.suggestion_btn = QPushButton("💡 Get Suggestions")
        self.suggestion_btn.clicked.connect(self._get_suggestions)
        right_layout.addWidget(self.suggestion_btn)

        self.suggestions_list = QListWidget()
        self.suggestions_list.setMaximumHeight(200)
        self.suggestions_list.itemDoubleClicked.connect(self._use_suggestion)
        right_layout.addWidget(self.suggestions_list)

        right_layout.addWidget(QLabel("CHAPTER SETTINGS"))
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(200, 4000)
        self.tokens_spin.setValue(self.config.get("max_tokens", 1200))
        right_layout.addWidget(QLabel("Max words per generation:"))
        right_layout.addWidget(self.tokens_spin)

        right_layout.addStretch()

        status_frame = QFrame()
        status_frame.setStyleSheet("background: #16162a; border: 1px solid #2d2d4e; border-radius: 8px; padding: 8px;")
        status_v = QVBoxLayout(status_frame)
        self.ai_status_label = QLabel("● LM Studio: Checking...")
        self.ai_status_label.setStyleSheet("font-size: 11px; color: #64748b;")
        status_v.addWidget(self.ai_status_label)
        right_layout.addWidget(status_frame)

        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([900, 260])

        # Generation progress bar at bottom of editor
        self.gen_progress = QProgressBar()
        self.gen_progress.setMaximum(0)
        self.gen_progress.setVisible(False)
        self.gen_progress.setFixedHeight(4)
        self.statusBar().addPermanentWidget(self.gen_progress, 1)

        # Check connection
        QTimer.singleShot(1000, self._check_connection_silent)

    def _build_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — Load a project or import a book to start")

    # ─── Status ───────────────────────────────────────────────────────────────

    def _update_status(self):
        title = self.project.get("title", "New Project")
        self.project_title_label.setText(title)
        self.setWindowTitle(f"BookAI Studio — {title}")

    def _check_connection_silent(self):
        connected = self.llm.is_connected()
        if connected:
            self.ai_status_label.setText("● LM Studio: Connected")
            self.ai_status_label.setStyleSheet("font-size: 11px; color: #4ade80;")
        else:
            self.ai_status_label.setText("● LM Studio: Not connected")
            self.ai_status_label.setStyleSheet("font-size: 11px; color: #f87171;")

    def _check_connection(self):
        connected = self.llm.is_connected()
        msg = "✅ LM Studio is connected and ready." if connected else "❌ Cannot connect to LM Studio.\n\nMake sure:\n1. LM Studio is running\n2. A model is loaded\n3. Local server is started (port 1234)"
        QMessageBox.information(self, "LM Studio Connection", msg)
        self._check_connection_silent()

    # ─── Project ──────────────────────────────────────────────────────────────

    def _new_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project title:")
        if ok and name.strip():
            self.project = self.storage.new_project(name.strip())
            self._refresh_all()
            self.status_bar.showMessage(f"New project: {name}")

    def _open_project(self):
        projects = self.storage.list_projects()
        if not projects:
            QMessageBox.information(self, "No Projects", "No saved projects found. Start a new project.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Open Project")
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog)
        lst = QListWidget()
        for p in projects:
            item = QListWidgetItem(f"{p['title']} ({p['chapter_count']} chapters)")
            item.setData(Qt.ItemDataRole.UserRole, p["path"])
            lst.addItem(item)
        layout.addWidget(lst)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)
        if dialog.exec() == QDialog.DialogCode.Accepted and lst.currentItem():
            path = lst.currentItem().data(Qt.ItemDataRole.UserRole)
            self.project = self.storage.load_project(path)
            self.config["last_project"] = path
            save_config(self.config)
            self._refresh_all()
            self.status_bar.showMessage(f"Opened: {self.project['title']}")

    def _save_project(self):
        path = self.storage.save_project(self.project)
        self.config["last_project"] = path
        save_config(self.config)
        self.status_bar.showMessage(f"Saved to {path}")

    def _refresh_all(self):
        self._update_status()
        self._refresh_chapter_list()
        self._refresh_char_list()
        self._refresh_char_grid()
        self._refresh_image_grid()
        style = self.project.get("style", "Dark Fantasy")
        idx = self.style_combo.findText(style)
        if idx >= 0:
            self.style_combo.setCurrentIndex(idx)
        self.video_title_edit.setText(self.project.get("title", ""))

    # ─── Import Book ──────────────────────────────────────────────────────────

    def _import_book(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Book", "",
            "Books (*.pdf *.epub *.txt *.docx);;All Files (*.*)"
        )
        if not path:
            return

        self.status_bar.showMessage("Parsing book...")
        try:
            data = self.parser.parse(path)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))
            return

        self.project["title"] = data.get("title", "Imported Book")
        self.project["source_book"] = path

        # Import chapters
        imported = 0
        for ch in data.get("chapters", []):
            if len(ch.get("content", "")) > 100:
                self.storage.add_chapter(self.project, ch["title"], ch["content"])
                imported += 1
                if imported >= 50:
                    break

        self._refresh_all()
        self.status_bar.showMessage(f"Imported {imported} chapters from {os.path.basename(path)}")

        # Auto-extract characters in background
        full_text = data.get("full_text", "")[:8000]
        if full_text and self.llm.is_connected():
            self._extract_characters_from_text(full_text)
            self._extract_info_from_text(full_text)

    def _extract_characters_from_text(self, text: str):
        self.status_bar.showMessage("Extracting characters from book...")
        self._chars_worker = LLMWorker(self.llm, "extract_chars", text=text)
        self._chars_worker.finished.connect(self._on_chars_extracted)
        self._chars_worker.finished.connect(self._chars_worker.deleteLater)
        self._chars_worker.start()

    def _on_chars_extracted(self, result: str):
        try:
            chars = json.loads(result)
            for c in chars:
                if c.get("name"):
                    self.storage.add_character(self.project, c)
            self._refresh_char_list()
            self._refresh_char_grid()
            self.status_bar.showMessage(f"Extracted {len(chars)} characters from book")
        except Exception:
            pass

    def _extract_info_from_text(self, text: str):
        self._info_worker = LLMWorker(self.llm, "extract_info", text=text)
        self._info_worker.finished.connect(self._on_info_extracted)
        self._info_worker.finished.connect(self._info_worker.deleteLater)
        self._info_worker.start()

    def _on_info_extracted(self, result: str):
        try:
            info = json.loads(result)
            for key in ["genre", "setting", "plot_summary", "tone"]:
                if info.get(key):
                    self.project[key] = info[key]
            style = info.get("writing_style", "")
            if style:
                self.project["style"] = style
        except Exception:
            pass

    # ─── Chapters ─────────────────────────────────────────────────────────────

    def _refresh_chapter_list(self):
        self.chapter_list.clear()
        for ch in self.project["chapters"]:
            item = QListWidgetItem(ch["title"])
            self.chapter_list.addItem(item)
        if self.project["chapters"]:
            self.chapter_list.setCurrentRow(0)

    def _on_chapter_selected(self, row: int):
        if row < 0 or row >= len(self.project["chapters"]):
            return
        # Save current chapter before switching
        if self.current_chapter and self.current_chapter_idx >= 0:
            html = self.editor.toHtml()
            self.project["chapters"][self.current_chapter_idx]["content"] = html
            plain = self.editor.toPlainText()
            self.project["chapters"][self.current_chapter_idx]["word_count"] = len(plain.split())

        self.current_chapter_idx = row
        self.current_chapter = self.project["chapters"][row]
        self.chapter_title_edit.setText(self.current_chapter["title"])

        content = self.current_chapter.get("content", "")
        # Load as HTML if it looks like HTML, otherwise convert plain text
        if content.strip().startswith("<"):
            self.editor.setHtml(content)
        else:
            self.editor.setHtml(self._plain_to_html(content))

        plain_text = self.editor.toPlainText()
        self.audio_preview.setPlainText(plain_text)
        wc = len(plain_text.split())
        self.word_count_label.setText(f"{wc:,} words")

    def _on_chapter_title_changed(self, text: str):
        if self.current_chapter:
            self.current_chapter["title"] = text
            row = self.current_chapter_idx
            if 0 <= row < self.chapter_list.count():
                self.chapter_list.item(row).setText(text)

    def _on_editor_changed(self):
        plain = self.editor.toPlainText()
        wc = len(plain.split())
        self.word_count_label.setText(f"{wc:,} words")
        if self.current_chapter:
            self.current_chapter["content"] = self.editor.toHtml()
            self.current_chapter["word_count"] = wc

    def _add_chapter(self):
        title, ok = QInputDialog.getText(self, "New Chapter", "Chapter title:")
        if ok and title.strip():
            ch = self.storage.add_chapter(self.project, title.strip())
            item = QListWidgetItem(ch["title"])
            self.chapter_list.addItem(item)
            self.chapter_list.setCurrentRow(self.chapter_list.count() - 1)

    def _delete_chapter(self):
        row = self.chapter_list.currentRow()
        if row < 0:
            return
        ch = self.project["chapters"][row]
        reply = QMessageBox.question(self, "Delete Chapter",
                                     f"Delete '{ch['title']}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.project["chapters"].pop(row)
            self._refresh_chapter_list()
            self.editor.clear()
            self.current_chapter = None
            self.current_chapter_idx = -1

    # ─── AI Writing ───────────────────────────────────────────────────────────

    def _get_characters(self) -> list:
        return self.project.get("characters", [])

    def _continue_writing(self):
        if not self.current_chapter:
            QMessageBox.warning(self, "No Chapter", "Please select or create a chapter first.")
            return
        if not self.llm.is_connected():
            QMessageBox.critical(self, "Not Connected", "LM Studio is not connected. Please start LM Studio and load a model.")
            return

        existing_text = self.editor.toPlainText()
        user_prompt = self.prompt_input.text().strip() or "Continue the story naturally"
        style = self.style_combo.currentText()

        self.gen_progress.setVisible(True)
        self.status_bar.showMessage("Generating...")

        self._worker = LLMWorker(self.llm, "continue",
                                  existing_text=existing_text,
                                  prompt=user_prompt,
                                  style=style,
                                  characters=self._get_characters(),
                                  max_tokens=self.tokens_spin.value())
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.finished.connect(self._on_generation_done)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.error.connect(self._on_generation_error)
        self._worker.start()
        self.prompt_input.clear()

    def _generate_full_chapter(self):
        if not self.current_chapter:
            QMessageBox.warning(self, "No Chapter", "Please select a chapter first.")
            return
        if not self.llm.is_connected():
            QMessageBox.critical(self, "Not Connected", "LM Studio is not connected.")
            return

        title = self.chapter_title_edit.text()
        summary = self.prompt_input.text().strip() or f"Write chapter: {title}"
        style = self.style_combo.currentText()

        prev = ""
        idx = self.current_chapter_idx
        if idx > 0:
            prev = self.project["chapters"][idx - 1].get("content", "")

        self.editor.clear()
        self.gen_progress.setVisible(True)
        self.status_bar.showMessage("Generating chapter...")

        self._worker = LLMWorker(self.llm, "generate_chapter",
                                  title=title,
                                  summary=summary,
                                  previous_chapter=prev,
                                  style=style,
                                  characters=self._get_characters(),
                                  max_tokens=self.tokens_spin.value())
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.finished.connect(self._on_generation_done)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.error.connect(self._on_generation_error)
        self._worker.start()
        self.prompt_input.clear()

    def _on_chunk(self, text: str):
        cursor = self.editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()

    def _on_generation_done(self, text: str):
        self.gen_progress.setVisible(False)
        self.status_bar.showMessage(f"Done — {len(text.split())} words generated")
        if self.current_chapter:
            self.current_chapter["content"] = self.editor.toHtml()

    def _on_generation_error(self, error: str):
        self.gen_progress.setVisible(False)
        self.status_bar.showMessage("Generation failed")
        QMessageBox.critical(self, "Generation Error", error)

    def _stop_generation(self):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self.gen_progress.setVisible(False)
            self.status_bar.showMessage("Stopped")

    def _get_suggestions(self):
        text = self.editor.toPlainText()
        if not text.strip():
            QMessageBox.information(self, "No Text", "Write some text first to get suggestions.")
            return
        if not self.llm.is_connected():
            QMessageBox.critical(self, "Not Connected", "LM Studio is not connected.")
            return

        self.suggestion_btn.setText("Loading...")
        self.suggestion_btn.setEnabled(False)
        self._suggestions_worker = LLMWorker(self.llm, "suggestions",
                                              text=text, style=self.style_combo.currentText())
        self._suggestions_worker.finished.connect(self._on_suggestions_done)
        self._suggestions_worker.finished.connect(self._suggestions_worker.deleteLater)
        self._suggestions_worker.error.connect(lambda e: (
            self.suggestion_btn.setText("💡 Get Suggestions"),
            self.suggestion_btn.setEnabled(True)
        ))
        self._suggestions_worker.start()

    def _on_suggestions_done(self, result: str):
        self.suggestion_btn.setText("💡 Get Suggestions")
        self.suggestion_btn.setEnabled(True)
        try:
            suggestions = json.loads(result)
            self.suggestions_list.clear()
            for s in suggestions:
                self.suggestions_list.addItem(str(s))
        except Exception:
            pass

    def _use_suggestion(self, item: QListWidgetItem):
        self.prompt_input.setText(item.text())
        self.tabs.setCurrentIndex(0)

    # ─── Characters ───────────────────────────────────────────────────────────

    def _refresh_char_list(self):
        self.char_list.clear()
        for c in self.project["characters"]:
            self.char_list.addItem(c.get("name", "Unknown"))

    def _refresh_char_grid(self):
        # Clear grid
        while self.char_grid_layout.count():
            item = self.char_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        chars = self.project.get("characters", [])
        for i, char in enumerate(chars):
            card = self._make_char_card(char)
            row, col = divmod(i, 3)
            self.char_grid_layout.addWidget(card, row, col)

    def _make_char_card(self, char: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("QFrame#card { background: #16162a; border: 1px solid #2d2d4e; border-radius: 10px; padding: 12px; } QFrame#card:hover { border-color: #4f46e5; }")
        layout = QVBoxLayout(card)

        # Avatar
        avatar_label = QLabel()
        avatar_label.setFixedSize(100, 100)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_path = char.get("avatar_path", "")
        if avatar_path and os.path.exists(avatar_path):
            pix = QPixmap(avatar_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation)
            avatar_label.setPixmap(pix)
        else:
            avatar_label.setText("👤")
            avatar_label.setStyleSheet("font-size: 40px; background: #1e1e38; border-radius: 50px; border: 1px solid #2d2d4e;")
        layout.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)

        name = QLabel(char.get("name", "Unknown"))
        name.setStyleSheet("color: #e2e8f0; font-weight: 700; font-size: 14px;")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name)

        role = QLabel(char.get("role", ""))
        role.setStyleSheet("color: #a78bfa; font-size: 11px;")
        role.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(role)

        desc = char.get("description", "")[:80]
        if desc:
            desc_label = QLabel(desc + "..." if len(char.get("description", "")) > 80 else desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #64748b; font-size: 11px;")
            layout.addWidget(desc_label)

        btn_row = QHBoxLayout()
        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        avatar_btn = QPushButton("🖼 Avatar")
        avatar_btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        char_ref = char
        edit_btn.clicked.connect(lambda: self._edit_character_by_ref(char_ref))
        avatar_btn.clicked.connect(lambda: self._generate_avatar(char_ref))
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(avatar_btn)
        layout.addLayout(btn_row)
        return card

    def _add_character_manually(self):
        dialog = CharacterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            char = dialog.get_character()
            if char.get("name"):
                self.storage.add_character(self.project, char)
                self._refresh_char_list()
                self._refresh_char_grid()

    def _edit_character(self, item: QListWidgetItem):
        idx = self.char_list.row(item)
        if 0 <= idx < len(self.project["characters"]):
            self._edit_character_by_ref(self.project["characters"][idx])

    def _edit_character_by_ref(self, char: dict):
        dialog = CharacterDialog(self, char)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated = dialog.get_character()
            char.update(updated)
            self._refresh_char_list()
            self._refresh_char_grid()

    def _generate_avatar_for_selected(self):
        row = self.char_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Character", "Select a character first.")
            return
        self._generate_avatar(self.project["characters"][row])

    def _on_avatar_done(self, char: dict, path: str):
        char["avatar_path"] = path
        self.project["images"].append(path)
        self._refresh_char_grid()
        self._refresh_image_grid()
        self.status_bar.showMessage(f"Avatar saved: {path}")

    # ─── Images ───────────────────────────────────────────────────────────────

    def _do_generate_image_with_prompt(self, prompt: str):
        style = self.img_style_combo.currentText()
        self.img_progress.setVisible(True)
        self.status_bar.showMessage("Generating image...")
        self._img_worker = ImageWorker(self.image_gen, "scene",
                                        scene_prompt=prompt, style=style.lower())
        self._img_worker.finished.connect(self._on_image_done)
        self._img_worker.error.connect(self._on_image_error)
        self._img_worker.start()

    def _on_image_done(self, path: str):
        self.img_progress.setVisible(False)
        if path not in self.project["images"]:
            self.project["images"].append(path)
        self._refresh_image_grid()
        self.status_bar.showMessage(f"Image saved: {os.path.basename(path)}")

    def _on_image_error(self, error: str):
        self.img_progress.setVisible(False)
        self.status_bar.showMessage("Image generation failed")
        QMessageBox.critical(self, "Image Error", error)

    def _refresh_image_grid(self):
        while self.img_grid_layout.count():
            item = self.img_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        images = [p for p in self.project.get("images", []) if os.path.exists(p)]
        for i, img_path in enumerate(images):
            card = self._make_image_card(img_path)
            row, col = divmod(i, 3)
            self.img_grid_layout.addWidget(card, row, col)

    def _make_image_card(self, img_path: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(220)
        layout = QVBoxLayout(card)
        img_label = QLabel()
        pix = QPixmap(img_path).scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
        img_label.setPixmap(pix)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(img_label)

        fname = QLabel(os.path.basename(img_path))
        fname.setStyleSheet("color: #64748b; font-size: 10px;")
        fname.setWordWrap(True)
        layout.addWidget(fname)

        open_btn = QPushButton("📂 Open")
        open_btn.clicked.connect(lambda: os.startfile(img_path) if os.name == "nt" else os.system(f"xdg-open '{img_path}'"))
        layout.addWidget(open_btn)
        return card

    # ─── Audio ────────────────────────────────────────────────────────────────

    def _read_aloud(self):
        text = self.editor.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "No Text", "The current chapter is empty.")
            return

        def speak_thread():
            self._speaking = True
            self.tts.speak(text)
            self._speaking = False

        t = threading.Thread(target=speak_thread, daemon=True)
        t.start()
        self.status_bar.showMessage("Reading aloud...")

    def _stop_reading(self):
        self.tts.stop()
        self._speaking = False
        self.status_bar.showMessage("Reading stopped")

    def _export_audio(self):
        text = self.editor.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "No Text", "The current chapter is empty.")
            return

        chap_title = self.chapter_title_edit.text().strip() or "chapter"
        fname = "".join(c for c in chap_title if c.isalnum() or c in " _-").strip().replace(" ", "_") + ".mp3"

        self.audio_progress.setVisible(True)
        self.status_bar.showMessage("Exporting audio...")
        self._tts_worker = TTSWorker(self.tts, text, fname)
        self._tts_worker.finished.connect(self._on_audio_exported)
        self._tts_worker.error.connect(self._on_audio_error)
        self._tts_worker.start()

    def _on_audio_exported(self, path: str):
        self.audio_progress.setVisible(False)
        if path not in self.project["audio_files"]:
            self.project["audio_files"].append(path)
        self.audio_list.addItem(os.path.basename(path))
        self.status_bar.showMessage(f"Audio exported: {os.path.basename(path)}")
        QMessageBox.information(self, "Audio Exported", f"Saved to:\n{path}")

    def _on_audio_error(self, error: str):
        self.audio_progress.setVisible(False)
        QMessageBox.critical(self, "Audio Error", error)

    # ─── Video ────────────────────────────────────────────────────────────────

    def _create_video(self):
        if not self.video_gen.is_available():
            QMessageBox.warning(self, "moviepy Not Installed",
                                "Install moviepy to create videos:\npip install moviepy")
            return

        images = [p for p in self.project.get("images", []) if os.path.exists(p)]
        if not images:
            QMessageBox.warning(self, "No Images",
                                "Generate some scene images first in the Images tab.")
            return

        title = self.video_title_edit.text().strip() or self.project.get("title", "Book Trailer")
        audio_files = [p for p in self.project.get("audio_files", []) if os.path.exists(p)]
        audio = audio_files[0] if audio_files else None

        self.video_progress.setVisible(True)
        self.status_bar.showMessage("Creating video...")
        self._vid_worker = VideoWorker(self.video_gen, images, title, audio)
        self._vid_worker.finished.connect(self._on_video_done)
        self._vid_worker.error.connect(self._on_video_error)
        self._vid_worker.start()

    def _on_video_done(self, path: str):
        self.video_progress.setVisible(False)
        if path not in self.project["videos"]:
            self.project["videos"].append(path)
        self.video_list.addItem(os.path.basename(path))
        self.status_bar.showMessage(f"Video created: {os.path.basename(path)}")
        QMessageBox.information(self, "Video Created", f"Saved to:\n{path}")

    def _on_video_error(self, error: str):
        self.video_progress.setVisible(False)
        QMessageBox.critical(self, "Video Error", error)

    # ─── Settings ─────────────────────────────────────────────────────────────

    def _open_settings(self):
        dialog = SettingsDialog(self, self.config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config = dialog.get_config()
            save_config(self.config)
            self._init_services()
            self._check_connection_silent()
            self.status_bar.showMessage("Settings saved")

    # ─── Help ─────────────────────────────────────────────────────────────────

    def _show_setup_guide(self):
        msg = """BookAI Studio v1.1 — Setup Guide

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICK START (OpenAI — easiest)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Get an API key from platform.openai.com
2. Open Settings → API Keys → paste your key
3. Enable "Use DALL-E 3 for images"
4. Select TTS Engine: openai and pick a voice
   (nova, shimmer, alloy, echo, fable, onyx)
5. Start writing! Images and audio will use OpenAI.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FULLY OFFLINE SETUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI Writing (LM Studio):
  • Download lmstudio.ai, load a model
  • Go to Local Server → Start Server (port 1234)

Images (Stable Diffusion):
  Option A: pip install diffusers torch
  Option B: Install AUTOMATIC1111 WebUI, enable API
  → Set SD URL in Settings → Images (SD)

Audio (offline TTS):
  pip install gTTS pyttsx3
  → Set TTS Engine to gtts or pyttsx3 in Audio tab

Video:
  pip install moviepy

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WRITING TIPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• File → New Project or Import Book (PDF/EPUB/TXT)
• Use the formatting toolbar: Bold/Italic/Size/Spacing
• Double-click a character to edit full profile
• The + button in the sidebar adds chapters/characters"""
        QMessageBox.information(self, "Setup Guide", msg)

    def _show_about(self):
        QMessageBox.about(self, "About BookAI Studio",
                          f"BookAI Studio v1.0\n\nOffline AI-powered book writing, image generation, and video creation.\n\nRuns 100% offline on your GPU.")

    # ─── Formatting ───────────────────────────────────────────────────────────

    @staticmethod
    def _plain_to_html(text: str) -> str:
        """Convert plain text with newlines to basic HTML paragraphs."""
        if not text:
            return ""
        paragraphs = text.split("\n\n")
        parts = []
        for p in paragraphs:
            p = p.strip()
            if p:
                lines = p.replace("\n", "<br>")
                parts.append(f"<p>{lines}</p>")
        return "".join(parts) or f"<p>{text}</p>"

    def _fmt_bold(self):
        fmt = QTextCharFormat()
        cursor = self.editor.textCursor()
        current = cursor.charFormat()
        new_weight = (
            QFont.Weight.Normal
            if current.fontWeight() == QFont.Weight.Bold
            else QFont.Weight.Bold
        )
        fmt.setFontWeight(new_weight)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def _fmt_italic(self):
        fmt = QTextCharFormat()
        cursor = self.editor.textCursor()
        fmt.setFontItalic(not cursor.charFormat().fontItalic())
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def _fmt_underline(self):
        fmt = QTextCharFormat()
        cursor = self.editor.textCursor()
        fmt.setFontUnderline(not cursor.charFormat().fontUnderline())
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def _fmt_font_size(self, size_str: str):
        try:
            size = int(size_str)
            fmt = QTextCharFormat()
            fmt.setFontPointSize(size)
            cursor = self.editor.textCursor()
            if cursor.hasSelection():
                cursor.mergeCharFormat(fmt)
            self.editor.mergeCurrentCharFormat(fmt)
        except ValueError:
            pass

    def _fmt_para_spacing(self, px: int):
        cursor = self.editor.textCursor()
        block_fmt = QTextBlockFormat()
        block_fmt.setBottomMargin(float(px))
        # ProportionalHeight = 1, value 180 means 1.8× line height
        block_fmt.setLineHeight(180.0, 1)
        # Apply to all paragraphs if no selection; else apply to selection
        if not cursor.hasSelection():
            c = QTextCursor(self.editor.document())
            c.select(QTextCursor.SelectionType.Document)
            c.mergeBlockFormat(block_fmt)
        else:
            cursor.mergeBlockFormat(block_fmt)

    def _fmt_heading(self, index: int):
        sizes = [13, 20, 17, 15]  # Normal, H1, H2, H3
        weights = [
            QFont.Weight.Normal, QFont.Weight.Bold,
            QFont.Weight.Bold, QFont.Weight.Bold,
        ]
        size = sizes[index] if index < len(sizes) else 13
        weight = weights[index] if index < len(weights) else QFont.Weight.Normal

        char_fmt = QTextCharFormat()
        char_fmt.setFontPointSize(size)
        char_fmt.setFontWeight(weight)

        block_fmt = QTextBlockFormat()
        block_fmt.setTopMargin(8 if index > 0 else 0)
        block_fmt.setBottomMargin(6 if index > 0 else 12)

        cursor = self.editor.textCursor()
        cursor.mergeBlockFormat(block_fmt)
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.mergeCharFormat(char_fmt)
        self.editor.mergeCurrentCharFormat(char_fmt)

    def _fmt_clear(self):
        cursor = self.editor.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontPointSize(13)
        fmt.setFontWeight(QFont.Weight.Normal)
        fmt.setFontItalic(False)
        fmt.setFontUnderline(False)
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(fmt)
        block_fmt = QTextBlockFormat()
        block_fmt.setBottomMargin(12)
        cursor.mergeBlockFormat(block_fmt)

    # ─── Characters (new methods) ──────────────────────────────────────────────

    def _delete_selected_character(self):
        row = self.char_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Select a character to delete.")
            return
        char = self.project["characters"][row]
        reply = QMessageBox.question(
            self, "Delete Character",
            f"Delete '{char.get('name', 'Unknown')}'?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.project["characters"].pop(row)
            self._refresh_char_list()
            self._refresh_char_grid()

    # ─── Audio (new methods) ──────────────────────────────────────────────────

    def _on_tts_engine_changed(self, engine: str):
        self.tts.set_engine(engine)
        # Show/hide OpenAI-specific controls
        is_openai = engine == "openai"
        self.tts_voice_combo.setEnabled(is_openai)
        self.openai_speed_spin.setEnabled(True)

    # ─── Image gen – make available via OpenAI too ────────────────────────────

    def _generate_avatar(self, char: dict):
        name = char.get("name", "character")
        desc = char.get("appearance", char.get("description", ""))
        self.status_bar.showMessage(f"Generating avatar for {name}...")
        self._img_worker = ImageWorker(self.image_gen, "avatar",
                                       character_name=name, description=desc)
        self._img_worker.finished.connect(lambda path: self._on_avatar_done(char, path))
        self._img_worker.error.connect(self._on_image_error)
        self._img_worker.start()

    def _generate_scene_image(self):
        user_prompt = self.img_prompt_edit.text().strip()
        style = self.img_style_combo.currentText()

        if not user_prompt and self.current_chapter:
            if self.llm.is_connected():
                chapter_text = self.editor.toPlainText()
                self.status_bar.showMessage("Generating image prompt from chapter...")
                self._imgprompt_worker = LLMWorker(
                    self.llm, "image_prompt",
                    chapter_text=chapter_text,
                    additional_prompt="",
                    style=style.lower()
                )
                self._imgprompt_worker.finished.connect(self._do_generate_image_with_prompt)
                self._imgprompt_worker.finished.connect(self._imgprompt_worker.deleteLater)
                self._imgprompt_worker.start()
                return
            else:
                user_prompt = f"{self.current_chapter.get('title', 'scene')}, {style}"

        self._do_generate_image_with_prompt(user_prompt or f"Dramatic fantasy scene, {style} style")

    # ─── Close ────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self.current_chapter and self.current_chapter_idx >= 0:
            self.project["chapters"][self.current_chapter_idx]["content"] = self.editor.toHtml()
        try:
            self._save_project()
        except Exception:
            pass
        event.accept()
