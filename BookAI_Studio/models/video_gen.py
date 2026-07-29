"""
Video Generator for BookAI Studio.

Supports both moviepy v1 (uses moviepy.editor) and moviepy v2 (direct import).
Falls back to a PIL-only still-image slideshow if moviepy is missing.
"""

import os
import time

try:
    from config import VIDEO_DIR
except ImportError:
    VIDEO_DIR = os.path.join(os.path.expanduser("~"), "BookAI_Exports", "videos")


def _import_moviepy():
    """Return (ImageClip, AudioFileClip, concatenate_videoclips, TextClip,
              CompositeVideoClip) handling both moviepy v1 and v2 APIs."""
    try:
        # moviepy v2 dropped the .editor sub-module
        from moviepy import (
            ImageClip, AudioFileClip, concatenate_videoclips,
            CompositeVideoClip,
        )
        try:
            from moviepy import TextClip
        except ImportError:
            TextClip = None
        return ImageClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
    except ImportError:
        pass
    try:
        from moviepy.editor import (
            ImageClip, AudioFileClip, concatenate_videoclips,
            CompositeVideoClip,
        )
        try:
            from moviepy.editor import TextClip
        except ImportError:
            TextClip = None
        return ImageClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
    except ImportError:
        return None, None, None, None, None


class VideoGenerator:

    def create_book_trailer(self, images: list, audio_path: str = None,
                            title: str = "Book Trailer", duration_per_image: float = 3.0,
                            output_name: str = None) -> str:

        ImageClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip = _import_moviepy()

        if ImageClip is None:
            # Fallback: create a simple GIF-style video using PIL and imageio
            return self._create_simple_slideshow(images, title, output_name)

        if not images:
            raise ValueError("No images provided")

        valid = [p for p in images if os.path.exists(p)]
        if not valid:
            raise ValueError("No valid image files found")

        clips = []
        for img_path in valid:
            try:
                clip = ImageClip(img_path, duration=duration_per_image)
                # resize — API changed between v1 and v2
                try:
                    clip = clip.resized((1280, 720))          # v2
                except AttributeError:
                    clip = clip.resize((1280, 720))           # v1
                # fade — API changed between v1 and v2
                try:
                    clip = clip.with_effects(["fadein:0.5", "fadeout:0.5"])
                except Exception:
                    try:
                        clip = clip.fadein(0.5).fadeout(0.5)  # v1
                    except Exception:
                        pass
                clips.append(clip)
            except Exception as e:
                print(f"Skipping image {img_path}: {e}")
                continue

        if not clips:
            raise ValueError("Could not load any images for video")

        video = concatenate_videoclips(clips, method="compose")

        # Title text overlay
        if TextClip is not None:
            try:
                txt = TextClip(
                    title, fontsize=60, color="white",
                    stroke_color="black", stroke_width=2,
                )
                # set_position / set_duration API varies
                try:
                    txt = txt.with_position("center").with_duration(min(3.0, video.duration))
                    video = CompositeVideoClip([video, txt.with_start(0)])
                except AttributeError:
                    txt = txt.set_position("center").set_duration(min(3.0, video.duration))
                    video = CompositeVideoClip([video, txt.set_start(0)])
            except Exception:
                # TextClip needs ImageMagick; skip silently
                pass

        # Audio
        if audio_path and os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                if audio.duration > video.duration:
                    try:
                        audio = audio.subclipped(0, video.duration)   # v2
                    except AttributeError:
                        audio = audio.subclip(0, video.duration)      # v1
                try:
                    video = video.with_audio(audio)    # v2
                except AttributeError:
                    video = video.set_audio(audio)     # v1
            except Exception as e:
                print(f"Audio overlay skipped: {e}")

        output_name = output_name or f"trailer_{int(time.time())}.mp4"
        if not output_name.endswith(".mp4"):
            output_name += ".mp4"
        output_path = os.path.join(VIDEO_DIR, output_name)

        video.write_videofile(
            output_path, fps=24, codec="libx264",
            audio_codec="aac", logger=None,
        )
        video.close()
        return output_path

    def create_slideshow_with_narration(self, images: list, texts: list,
                                        output_name: str = None) -> str:
        import tempfile
        ImageClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip = _import_moviepy()

        if ImageClip is None:
            return self._create_simple_slideshow(images, "Slideshow", output_name)

        valid_pairs = [(img, txt) for img, txt in zip(images, texts) if os.path.exists(img)]
        if not valid_pairs:
            raise ValueError("No valid images found")

        clips = []
        temp_audio_files = []

        for img_path, text in valid_pairs:
            audio_duration = 4.0
            audio_clip = None
            try:
                from gtts import gTTS
                tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                tmp.close()
                gTTS(text=text[:300], lang="en", slow=False).save(tmp.name)
                temp_audio_files.append(tmp.name)
                audio_clip = AudioFileClip(tmp.name)
                audio_duration = max(audio_clip.duration + 0.5, 3.0)
            except Exception:
                pass

            try:
                img_clip = ImageClip(img_path, duration=audio_duration)
                try:
                    img_clip = img_clip.resized((1280, 720))
                except AttributeError:
                    img_clip = img_clip.resize((1280, 720))

                if audio_clip:
                    try:
                        img_clip = img_clip.with_audio(audio_clip)
                    except AttributeError:
                        img_clip = img_clip.set_audio(audio_clip)

                try:
                    img_clip = img_clip.fadein(0.3).fadeout(0.3)
                except Exception:
                    pass
                clips.append(img_clip)
            except Exception as e:
                print(f"Skipping {img_path}: {e}")

        if not clips:
            raise ValueError("No valid clips created")

        final = concatenate_videoclips(clips, method="compose")
        output_name = output_name or f"slideshow_{int(time.time())}.mp4"
        if not output_name.endswith(".mp4"):
            output_name += ".mp4"
        output_path = os.path.join(VIDEO_DIR, output_name)
        final.write_videofile(output_path, fps=24, codec="libx264",
                              audio_codec="aac", logger=None)
        final.close()

        for f in temp_audio_files:
            try:
                os.remove(f)
            except Exception:
                pass

        return output_path

    def _create_simple_slideshow(self, images: list, title: str, output_name: str = None) -> str:
        """PIL + imageio fallback when moviepy is not available."""
        try:
            import imageio.v3 as iio
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np
        except ImportError:
            raise ImportError(
                "moviepy is not installed. To create videos run:\n"
                "  pip install moviepy\n\n"
                "For a basic slideshow without moviepy:\n"
                "  pip install imageio imageio-ffmpeg"
            )

        output_name = output_name or f"trailer_{int(time.time())}.mp4"
        if not output_name.endswith(".mp4"):
            output_name += ".mp4"
        output_path = os.path.join(VIDEO_DIR, output_name)

        fps = 24
        hold_frames = fps * 3  # 3 seconds per image

        valid = [p for p in images if os.path.exists(p)]
        if not valid:
            raise ValueError("No valid images")

        frames = []
        for img_path in valid:
            img = Image.open(img_path).convert("RGB").resize((1280, 720), Image.LANCZOS)
            arr = np.array(img)
            for _ in range(hold_frames):
                frames.append(arr)

        with iio.imopen(output_path, "w", plugin="pyav") as writer:
            writer.init_video_stream("libx264", fps=fps)
            for frame in frames:
                writer.write_frame(frame)

        return output_path

    def is_available(self) -> bool:
        ImageClip, *_ = _import_moviepy()
        if ImageClip is not None:
            return True
        try:
            import imageio  # noqa
            from PIL import Image  # noqa
            return True
        except ImportError:
            return False
