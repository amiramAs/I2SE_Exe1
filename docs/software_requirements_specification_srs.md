# Software Requirements Specification (SRS)
## 3D to 2D Projection and Rendering Application

### 1. Introduction
* **Purpose:** The system is a desktop application developed in Python that extracts 2D image slices from a 3D voxel space (`.nrrd` file) based on spatial coordinates provided in an external file. 
* **Scope:** The product features a Graphical User Interface (GUI) for data loading and frame navigation, a high-performance geometric projection engine, and an automated video export module. 

### 2. Functional Requirements
* **Data Ingestion:** The GUI shall include two primary buttons. One button for loading a 3D matrix file in `.nrrd` format (up to $500^3$ bits), and another for loading a `.csv` file containing the target coordinates (e.g., `Ex0.csv - Sheet1.csv`).
* **Projection Engine:** The algorithm shall accept either 3 points (defining an isosceles triangle plane) or 4 points (defining an isosceles trapezoid plane) from the `.csv` file. For each valid record, it will normalize the direction vectors and sample the relevant pixels to output a 2D matrix frame.
* **Out-of-Bounds Handling:** The system shall gracefully handle target coordinates that fall outside the boundaries of the original 3D matrix (e.g., negative coordinates like -50 or coordinates exceeding the volume size). Instead of throwing errors, the system will output a background value of `0` for these specific pixels.
* **Interactive Navigation:** Upon completion of the frame generation, the GUI will display the 2D images and allow the user to smoothly navigate forward and backward through the sequence using the keyboard arrow keys.
* **Video Export:** The system shall aggregate the processed 2D frames and export them as a continuous video file using the external `ffmpeg` command-line tool.

### 3. Non-Functional Requirements
* **Performance & Throughput:** The core rendering algorithm shall process the 2D matrices at a minimum rate of 100 Frames Per Second (100 FPS), ensuring an inference time of no more than 10 milliseconds per frame. (Note: This time limit applies strictly to the frame generation and excludes the `ffmpeg` video export phase).
* **Memory Architecture:** To meet the strict performance requirements, the 3D `.nrrd` volume shall be stored in memory as a contiguous 1D array. This layout is required to maximize CPU cache hits and minimize memory access latency during the inner pixel-sampling loops.
* **UI State & Blocking:** The processing pipeline will run synchronously. Upon initiating the rendering process, the GUI will temporarily freeze user interactions and display a clear "Please wait" message to the user. The UI will return to a responsive state only after the processing is fully complete.
* **I/O Efficiency:** The video generation via `ffmpeg` shall be executed by streaming the raw pixel data directly from the application's memory to the `ffmpeg` standard input (stdin pipeline), strictly avoiding the creation of temporary image files on the hard drive.
* **Reliability:** The system shall implement safety mechanisms for mathematical edge cases (e.g., preventing division by zero when calculating vectors for overlapping points). Bad records in the `.csv` will be skipped or logged, ensuring the application continues processing without crashing.