"""
Desktop Graphical User Interface (GUI) for the 3D to 2D Volumetric Reslicing Engine.
Built using Tkinter and Pillow (No OpenCV required).
"""
from __future__ import annotations
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


class ReslicerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("3D to 2D Volumetric Reslicer")
        self.root.geometry("760x540")
        self.root.minsize(580, 440)

        self.volume: VolumeData | None = None
        self.nrrd_path: str = ""
        self.csv_path: str = ""
        self.frames: list[np.ndarray] = []
        self.current_frame_idx: int = 0
        self.photo_image: ImageTk.PhotoImage | None = None

        self._setup_ui()
        self._bind_keys()

    def _setup_ui(self):
        # Top Control Frame
        ctrl_frame = ttk.LabelFrame(self.root, text=" Data Ingestion & Controls ", padding=8)
        ctrl_frame.pack(side=tk.TOP, fill=tk.X, padx=12, pady=6)

        # Buttons
        self.btn_nrrd = ttk.Button(ctrl_frame, text="Load 3D NRRD Volume", command=self._load_nrrd)
        self.btn_nrrd.grid(row=0, column=0, padx=5, pady=3)

        self.lbl_nrrd = ttk.Label(ctrl_frame, text="No volume loaded", foreground="gray")
        self.lbl_nrrd.grid(row=0, column=1, sticky=tk.W, padx=10)

        self.btn_csv = ttk.Button(ctrl_frame, text="Load CSV Coordinates", command=self._load_csv)
        self.btn_csv.grid(row=1, column=0, padx=5, pady=3)

        self.lbl_csv = ttk.Label(ctrl_frame, text="No CSV loaded", foreground="gray")
        self.lbl_csv.grid(row=1, column=1, sticky=tk.W, padx=10)

        # Action Buttons
        act_frame = ttk.Frame(ctrl_frame)
        act_frame.grid(row=2, column=0, columnspan=2, pady=6, sticky=tk.W)

        self.btn_render = ttk.Button(act_frame, text="Render 2D Slices", command=self._render_slices, state=tk.DISABLED)
        self.btn_render.pack(side=tk.LEFT, padx=5)

        self.btn_export = ttk.Button(act_frame, text="Export MP4 Video", command=self._export_video, state=tk.DISABLED)
        self.btn_export.pack(side=tk.LEFT, padx=5)

        self.lbl_status = ttk.Label(act_frame, text="Ready", foreground="black", font=("Arial", 9, "italic"))
        self.lbl_status.pack(side=tk.LEFT, padx=(15, 5))

        self.lbl_fps = ttk.Label(act_frame, text="", foreground="#0055aa", font=("Arial", 9, "bold"))
        self.lbl_fps.pack(side=tk.LEFT, padx=5)

        # Navigation & Display Frame
        disp_frame = ttk.LabelFrame(self.root, text=" 2D Sliced Frame Viewer ", padding=8)
        disp_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=4)

        # Info Header
        self.lbl_info = ttk.Label(disp_frame, text="Use Left / Right Arrow keys to navigate frames", font=("Arial", 9))
        self.lbl_info.pack(side=tk.TOP, pady=2)

        # Canvas for displaying image
        self.canvas = tk.Canvas(disp_frame, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=4)
        self.canvas.bind("<Configure>", lambda e: self._show_current_frame())

        # Bottom Frame Navigation Bar
        nav_frame = ttk.Frame(self.root, padding=6)
        nav_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.btn_prev = ttk.Button(nav_frame, text="◄ Previous (Left)", command=self._prev_frame, state=tk.DISABLED)
        self.btn_prev.pack(side=tk.LEFT, padx=10)

        self.lbl_counter = ttk.Label(nav_frame, text="Frame: 0 / 0", font=("Arial", 10, "bold"))
        self.lbl_counter.pack(side=tk.LEFT, expand=True)

        self.btn_next = ttk.Button(nav_frame, text="Next (Right) ►", command=self._next_frame, state=tk.DISABLED)
        self.btn_next.pack(side=tk.RIGHT, padx=10)

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

        self.lbl_status.config(text="Loading 3D volume, please wait...", foreground="blue")
        self.root.update_idletasks()

        try:
            self.volume = VolumeData.from_file(file_path)
            self.nrrd_path = file_path
            fname = os.path.basename(file_path)
            self.lbl_nrrd.config(text=f"{fname} ({self.volume.shape[0]}x{self.volume.shape[1]}x{self.volume.shape[2]})", foreground="green")
            self.lbl_status.config(text="Volume loaded successfully.", foreground="black")
            self._check_ready_to_render()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load NRRD file:\n{e}")
            self.lbl_status.config(text="Error loading volume.", foreground="red")

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
        self.lbl_csv.config(text=fname, foreground="green")
        self._check_ready_to_render()

    def _check_ready_to_render(self):
        if self.volume is not None and self.csv_path:
            self.btn_render.config(state=tk.NORMAL)

    def _render_slices(self):
        if not self.volume or not self.csv_path:
            return

        # Synchronous UI freeze with "Please wait" status (SRS Section 3)
        self.lbl_status.config(text="Please wait... Processing 2D frames", foreground="red")
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
            self.lbl_status.config(text=f"Rendered {len(self.frames)} frames successfully.", foreground="green")
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
            self.lbl_status.config(text="Error rendering slices.", foreground="red")
        finally:
            self.btn_render.config(state=tk.NORMAL)
            self.btn_nrrd.config(state=tk.NORMAL)
            self.btn_csv.config(state=tk.NORMAL)
            self.root.config(cursor="")

    def _show_current_frame(self):
        if not self.frames:
            return

        frame = self.frames[self.current_frame_idx]
        self.lbl_counter.config(text=f"Frame: {self.current_frame_idx + 1} / {len(self.frames)}  [{frame.shape[1]}x{frame.shape[0]}]")

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
        canv_w = self.canvas.winfo_width()
        canv_h = self.canvas.winfo_height()

        if canv_w > 50 and canv_h > 50:
            img_w, img_h = pil_img.size
            scale = min((canv_w - 20) / img_w, (canv_h - 20) / img_h)
            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.NEAREST)

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

        self.lbl_status.config(text="Exporting video via ffmpeg, please wait...", foreground="blue")
        self.root.config(cursor="wait")
        self.root.update()

        try:
            export_frames_to_mp4(self.frames, save_path, fps=10)
            messagebox.showinfo("Success", f"Video exported successfully to:\n{save_path}")
            self.lbl_status.config(text="Video exported successfully.", foreground="green")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export video:\n{e}")
            self.lbl_status.config(text="Export failed.", foreground="red")
        finally:
            self.root.config(cursor="")


def main():
    root = tk.Tk()
    app = ReslicerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
