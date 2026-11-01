"""
Desktop Graphical User Interface (GUI) for the 3D to 2D Volumetric Reslicing Engine.
Built using Tkinter and Pillow (No OpenCV required).
"""
from __future__ import annotations
import ctypes
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
from PIL import Image, ImageTk

from src.volume_io import VolumeData
from src.csv_parser import parse_csv_file
from src.reslicer import reslice_plane
from src.error_renderer import make_error_frame
from src.video_streamer import export_frames_to_mp4


# Enable native High-DPI rendering on Windows (fixes blurry text and controls on laptops)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# Neutral Carbon & Graphite Palette (Black / Gray)
BG_MAIN = "#141414"        # Carbon black background
BG_CARD = "#1f1f1f"        # Elevated dark gray card surface
BG_CANVAS = "#0a0a0a"      # Pure near-black viewport
BORDER_COL = "#333333"     # Neutral dark gray border
TEXT_PRIMARY = "#f2f2f2"   # Crisp off-white text
TEXT_HEADER = "#cccccc"    # Clean neutral gray section header
TEXT_MUTED = "#8c8c8c"     # Muted gray secondary text
ACCENT_OK = "#4ade80"      # Subtle green status text
ACCENT_FPS = "#e5e5e5"     # Clean bright silver for FPS counter
ACCENT_WARN = "#fbbf24"    # Amber warning/wait text
ACCENT_ERR = "#f87171"     # Soft red error text
BTN_BG = "#2b2b2b"         # Standard button neutral gray
BTN_HOVER = "#3b3b3b"
BTN_ACTION_BG = "#383838"  # Emphasized neutral gray for action buttons
BTN_ACTION_HOVER = "#4a4a4a"
BTN_ACTION_BORDER = "#525252"
BTN_DISABLED = "#1a1a1a"


class ReslicerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("3D to 2D Volumetric Reslicer")

        # Adapt window size proportionally to physical screen resolution (High-DPI friendly)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(max(760, int(screen_w * 0.50)), 1050)
        win_h = min(max(540, int(screen_h * 0.68)), 780)
        pos_x = max(20, (screen_w - win_w) // 2)
        pos_y = max(20, (screen_h - win_h) // 2 - 20)
        self.root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.root.minsize(640, 460)
        self.root.configure(bg=BG_MAIN)

        self.volume: VolumeData | None = None
        self.nrrd_path: str = ""
        self.csv_path: str = ""
        self.frames: list[np.ndarray] = []
        self.current_frame_idx: int = 0
        self.photo_image: ImageTk.PhotoImage | None = None

        self._configure_styles()
        self._setup_ui()
        self._bind_keys()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # Frame & LabelFrame styles
        style.configure("Main.TFrame", background=BG_MAIN)
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure(
            "Card.TLabelframe",
            background=BG_CARD,
            foreground=TEXT_HEADER,
            bordercolor=BORDER_COL,
            lightcolor=BORDER_COL,
            darkcolor=BORDER_COL,
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=BG_CARD,
            foreground=TEXT_HEADER,
            font=("Segoe UI", 9, "bold"),
        )

        # Label styles
        style.configure(
            "Card.TLabel",
            background=BG_CARD,
            foreground=TEXT_PRIMARY,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Muted.TLabel",
            background=BG_CARD,
            foreground=TEXT_MUTED,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Nav.TLabel",
            background=BG_MAIN,
            foreground=TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold"),
        )

        # Secondary Button (File loaders & navigation)
        style.configure(
            "Secondary.TButton",
            background=BTN_BG,
            foreground=TEXT_PRIMARY,
            bordercolor=BORDER_COL,
            lightcolor=BTN_BG,
            darkcolor=BTN_BG,
            focuscolor="none",
            font=("Segoe UI", 9),
            padding=(12, 5),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", BTN_HOVER), ("disabled", BTN_DISABLED)],
            foreground=[("disabled", "#525252")],
            bordercolor=[("disabled", "#262626")],
        )

        # Action Button (Render & Export - clean monochrome graphite)
        style.configure(
            "Action.TButton",
            background=BTN_ACTION_BG,
            foreground="#ffffff",
            bordercolor=BTN_ACTION_BORDER,
            lightcolor=BTN_ACTION_BG,
            darkcolor=BTN_ACTION_BG,
            focuscolor="none",
            font=("Segoe UI", 9, "bold"),
            padding=(14, 5),
        )
        style.map(
            "Action.TButton",
            background=[("active", BTN_ACTION_HOVER), ("disabled", BTN_DISABLED)],
            foreground=[("disabled", "#525252")],
            bordercolor=[("disabled", "#262626")],
        )

    def _setup_ui(self):
        # Top Control Frame
        ctrl_frame = ttk.LabelFrame(
            self.root,
            text="  DATA INGESTION & CONTROLS  ",
            style="Card.TLabelframe",
            padding=(12, 8),
        )
        ctrl_frame.pack(side=tk.TOP, fill=tk.X, padx=14, pady=(10, 6))

        # File Load Buttons
        self.btn_nrrd = ttk.Button(
            ctrl_frame,
            text="Load 3D NRRD Volume",
            style="Secondary.TButton",
            command=self._load_nrrd,
            width=22,
        )
        self.btn_nrrd.grid(row=0, column=0, padx=(2, 8), pady=3, sticky=tk.W)

        self.lbl_nrrd = ttk.Label(ctrl_frame, text="No volume loaded", style="Muted.TLabel")
        self.lbl_nrrd.grid(row=0, column=1, sticky=tk.W, padx=6)

        self.btn_csv = ttk.Button(
            ctrl_frame,
            text="Load CSV Coordinates",
            style="Secondary.TButton",
            command=self._load_csv,
            width=22,
        )
        self.btn_csv.grid(row=1, column=0, padx=(2, 8), pady=3, sticky=tk.W)

        self.lbl_csv = ttk.Label(ctrl_frame, text="No CSV loaded", style="Muted.TLabel")
        self.lbl_csv.grid(row=1, column=1, sticky=tk.W, padx=6)

        # Action Buttons Row
        act_frame = ttk.Frame(ctrl_frame, style="Card.TFrame")
        act_frame.grid(row=2, column=0, columnspan=2, pady=(8, 2), sticky=tk.W)

        self.btn_render = ttk.Button(
            act_frame,
            text="Render 2D Slices",
            style="Action.TButton",
            command=self._render_slices,
            state=tk.DISABLED,
        )
        self.btn_render.pack(side=tk.LEFT, padx=(2, 8))

        self.btn_export = ttk.Button(
            act_frame,
            text="Export MP4 Video",
            style="Action.TButton",
            command=self._export_video,
            state=tk.DISABLED,
        )
        self.btn_export.pack(side=tk.LEFT, padx=(0, 12))

        self.lbl_status = ttk.Label(
            act_frame,
            text="Ready",
            style="Muted.TLabel",
            font=("Segoe UI", 9),
        )
        self.lbl_status.pack(side=tk.LEFT, padx=(6, 4))

        self.lbl_fps = ttk.Label(
            act_frame,
            text="",
            style="Card.TLabel",
            foreground=ACCENT_FPS,
            font=("Segoe UI", 9, "bold"),
        )
        self.lbl_fps.pack(side=tk.LEFT, padx=4)

        # Navigation & Display Frame
        disp_frame = ttk.LabelFrame(
            self.root,
            text="  2D SLICED FRAME VIEWPORT  ",
            style="Card.TLabelframe",
            padding=(10, 6),
        )
        disp_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=14, pady=4)

        # Info Header
        self.lbl_info = ttk.Label(
            disp_frame,
            text="Use Left / Right Arrow keys to navigate frames",
            style="Muted.TLabel",
            font=("Segoe UI", 9),
        )
        self.lbl_info.pack(side=tk.TOP, pady=(0, 4))

        # Canvas for displaying image
        self.canvas = tk.Canvas(
            disp_frame,
            bg=BG_CANVAS,
            highlightthickness=1,
            highlightbackground=BORDER_COL,
        )
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=2)
        self.canvas.bind("<Configure>", lambda e: self._show_current_frame())

        # Bottom Frame Navigation Bar
        nav_frame = ttk.Frame(self.root, style="Main.TFrame", padding=(14, 8))
        nav_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.btn_prev = ttk.Button(
            nav_frame,
            text="◄  Previous",
            style="Secondary.TButton",
            command=self._prev_frame,
            state=tk.DISABLED,
        )
        self.btn_prev.pack(side=tk.LEFT)

        self.lbl_counter = ttk.Label(
            nav_frame,
            text="Frame: 0 / 0",
            style="Nav.TLabel",
        )
        self.lbl_counter.pack(side=tk.LEFT, expand=True)

        self.btn_next = ttk.Button(
            nav_frame,
            text="Next  ►",
            style="Secondary.TButton",
            command=self._next_frame,
            state=tk.DISABLED,
        )
        self.btn_next.pack(side=tk.RIGHT)

    def _bind_keys(self):
        self.root.bind("<Left>", lambda e: self._prev_frame())
        self.root.bind("<Right>", lambda e: self._next_frame())

    def _load_nrrd(self):
        file_path = filedialog.askopenfilename(
            title="Select 3D NRRD Volume",
            filetypes=[("NRRD Volume", "*.nrrd"), ("All Files", "*.*")],
            initialdir="data",
        )
        if not file_path:
            return

        self.lbl_status.config(text="Loading 3D volume, please wait...", foreground=TEXT_PRIMARY)
        self.root.update_idletasks()

        try:
            self.volume = VolumeData.from_file(file_path)
            self.nrrd_path = file_path
            fname = os.path.basename(file_path)
            self.lbl_nrrd.config(
                text=f"{fname}  ({self.volume.shape[0]}×{self.volume.shape[1]}×{self.volume.shape[2]})",
                foreground=ACCENT_OK,
                font=("Segoe UI", 9, "bold"),
            )
            self.lbl_status.config(text="Volume loaded.", foreground=TEXT_MUTED)
            self._check_ready_to_render()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load NRRD file:\n{e}")
            self.lbl_status.config(text="Error loading volume.", foreground=ACCENT_ERR)

    def _load_csv(self):
        file_path = filedialog.askopenfilename(
            title="Select Trajectory Coordinates CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialdir="data",
        )
        if not file_path:
            return

        self.csv_path = file_path
        fname = os.path.basename(file_path)
        self.lbl_csv.config(
            text=fname,
            foreground=ACCENT_OK,
            font=("Segoe UI", 9, "bold"),
        )
        self._check_ready_to_render()

    def _check_ready_to_render(self):
        if self.volume is not None and self.csv_path:
            self.btn_render.config(state=tk.NORMAL)

    def _render_slices(self):
        if not self.volume or not self.csv_path:
            return

        # Synchronous UI freeze with "Please wait" status (SRS Section 3)
        self.lbl_status.config(text="Please wait... Processing 2D frames", foreground=ACCENT_WARN)
        self.lbl_fps.config(text="")
        self.btn_render.config(state=tk.DISABLED)
        self.btn_nrrd.config(state=tk.DISABLED)
        self.btn_csv.config(state=tk.DISABLED)
        self.root.config(cursor="wait")
        self.root.update()

        try:
            records = parse_csv_file(self.csv_path)
            rendered_frames: list[np.ndarray] = []
            last_dims = (500, 500)

            t_start = time.perf_counter()
            for rec in records:
                if rec.is_error:
                    f = make_error_frame(rec.error_message or "ERROR", last_dims)
                else:
                    f = reslice_plane(self.volume, rec.points, last_frame_dims=last_dims)
                    if not (f.shape == (500, 500) and np.any(f > 0)):
                        last_dims = f.shape
                rendered_frames.append(f)
            elapsed = time.perf_counter() - t_start
            render_fps = len(rendered_frames) / elapsed if elapsed > 0 else 0.0

            self.frames = rendered_frames
            self.current_frame_idx = 0
            self.lbl_status.config(
                text=f"Rendered {len(self.frames)} frames successfully.",
                foreground=ACCENT_OK,
            )
            self.lbl_fps.config(text=f"|  {render_fps:.1f} FPS")

            if self.frames:
                self.btn_export.config(state=tk.NORMAL)
                self.btn_prev.config(state=tk.NORMAL)
                self.btn_next.config(state=tk.NORMAL)
                self._show_current_frame()
            else:
                messagebox.showwarning("Warning", "No frames found in CSV file.")

        except Exception as e:
            messagebox.showerror("Rendering Error", f"An error occurred during rendering:\n{e}")
            self.lbl_status.config(text="Error rendering slices.", foreground=ACCENT_ERR)
        finally:
            self.btn_render.config(state=tk.NORMAL)
            self.btn_nrrd.config(state=tk.NORMAL)
            self.btn_csv.config(state=tk.NORMAL)
            self.root.config(cursor="")

    def _show_current_frame(self):
        canv_w = self.canvas.winfo_width()
        canv_h = self.canvas.winfo_height()

        if not self.frames:
            self.canvas.delete("all")
            if canv_w > 50 and canv_h > 50:
                self.canvas.create_text(
                    canv_w // 2,
                    canv_h // 2,
                    text="Load a 3D Volume (.nrrd) and Trajectory (.csv) to preview slices",
                    fill="#555555",
                    font=("Segoe UI", 10),
                )
            return

        frame = self.frames[self.current_frame_idx]
        self.lbl_counter.config(
            text=f"Frame: {self.current_frame_idx + 1} / {len(self.frames)}   •   {frame.shape[1]}×{frame.shape[0]} px"
        )

        # Convert to 8-bit image for PIL
        if frame.dtype != np.uint8:
            if frame.max() > 0:
                f8 = (frame / frame.max() * 255).astype(np.uint8)
            else:
                f8 = frame.astype(np.uint8)
        else:
            f8 = frame

        pil_img = Image.fromarray(f8)

        # Scale image to fit canvas while preserving aspect ratio
        if canv_w > 50 and canv_h > 50:
            img_w, img_h = pil_img.size
            scale = min((canv_w - 16) / img_w, (canv_h - 16) / img_h)
            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))
            resample_mode = Image.Resampling.LANCZOS if scale < 1.0 else Image.Resampling.NEAREST
            pil_img = pil_img.resize((new_w, new_h), resample_mode)

        self.photo_image = ImageTk.PhotoImage(pil_img)
        self.canvas.delete("all")
        cx = canv_w // 2
        cy = canv_h // 2
        self.canvas.create_image(cx, cy, image=self.photo_image, anchor=tk.CENTER)

    def _prev_frame(self):
        if self.frames and self.current_frame_idx > 0:
            self.current_frame_idx -= 1
            self._show_current_frame()

    def _next_frame(self):
        if self.frames and self.current_frame_idx < len(self.frames) - 1:
            self.current_frame_idx += 1
            self._show_current_frame()

    def _export_video(self):
        if not self.frames:
            return

        save_path = filedialog.asksaveasfilename(
            title="Export Video File",
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4"), ("All Files", "*.*")],
            initialfile="flight_trajectory.mp4",
        )
        if not save_path:
            return

        self.lbl_status.config(text="Exporting video via ffmpeg, please wait...", foreground=TEXT_PRIMARY)
        self.root.config(cursor="wait")
        self.root.update()

        try:
            export_frames_to_mp4(self.frames, save_path, fps=10)
            messagebox.showinfo("Success", f"Video exported successfully to:\n{save_path}")
            self.lbl_status.config(text="Video exported successfully.", foreground=ACCENT_OK)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export video:\n{e}")
            self.lbl_status.config(text="Export failed.", foreground=ACCENT_ERR)
        finally:
            self.root.config(cursor="")


def main():
    root = tk.Tk()
    app = ReslicerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
