import os
import json
import time
from config import PROJECTS_DIR


class ProjectStorage:

    def new_project(self, title: str = "Untitled") -> dict:
        return {
            "id": str(int(time.time())),
            "title": title,
            "created": time.time(),
            "modified": time.time(),
            "genre": "",
            "style": "Dark Fantasy",
            "setting": "",
            "plot_summary": "",
            "tone": "",
            "series_info": {"book_number": 1, "series_name": ""},
            "characters": [],
            "chapters": [],
            "images": [],
            "videos": [],
            "audio_files": [],
            "source_book": "",
        }

    def save_project(self, project: dict) -> str:
        project["modified"] = time.time()
        title_safe = "".join(c for c in project["title"] if c.isalnum() or c in " _-").strip()
        title_safe = title_safe.replace(" ", "_") or "project"
        filename = f"{title_safe}_{project['id']}.json"
        path = os.path.join(PROJECTS_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(project, f, indent=2, ensure_ascii=False)
        return path

    def load_project(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_projects(self) -> list:
        projects = []
        for fname in os.listdir(PROJECTS_DIR):
            if fname.endswith(".json"):
                path = os.path.join(PROJECTS_DIR, fname)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    projects.append({
                        "path": path,
                        "title": data.get("title", "Untitled"),
                        "modified": data.get("modified", 0),
                        "chapter_count": len(data.get("chapters", [])),
                    })
                except Exception:
                    pass
        return sorted(projects, key=lambda x: x["modified"], reverse=True)

    def delete_project(self, path: str):
        if os.path.exists(path):
            os.remove(path)

    def add_chapter(self, project: dict, title: str, content: str = "") -> dict:
        chapter = {
            "id": str(int(time.time())),
            "title": title,
            "content": content,
            "word_count": len(content.split()),
            "created": time.time(),
            "modified": time.time(),
        }
        project["chapters"].append(chapter)
        return chapter

    def update_chapter(self, project: dict, chapter_id: str, content: str):
        for ch in project["chapters"]:
            if ch["id"] == chapter_id:
                ch["content"] = content
                ch["word_count"] = len(content.split())
                ch["modified"] = time.time()
                return
        raise ValueError(f"Chapter {chapter_id} not found")

    def add_character(self, project: dict, character: dict) -> dict:
        if "id" not in character:
            character["id"] = str(int(time.time()))
        project["characters"].append(character)
        return character

    def update_character(self, project: dict, char_id: str, updates: dict):
        for c in project["characters"]:
            if c.get("id") == char_id:
                c.update(updates)
                return
