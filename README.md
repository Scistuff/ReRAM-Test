# Keithley SMU Control & ReRAM Tester 🔬

A professional, Python-based GUI application for controlling Keithley Source Measure Units (SMUs) for advanced electronic device characterization. This tool is especially useful for testing memristors and ReRAM devices.

 
<img width="2454" height="1631" alt="image" src="https://github.com/user-attachments/assets/d5ed55f4-6737-4158-9945-4aabecfc6c96" />



##  Key Features

- **Intuitive GUI:** Built with Tkinter for a user-friendly experience.
- **Broad Instrument Support:** Connects to Keithley SMUs via VISA and automatically detects 2400 vs. 2600 series instruments.
- **Standard Characterization:**
  - I-V Sweeps (Voltage and Current)
  - DC Bias Application
  - 2-Wire and 4-Wire Resistance Measurement
- **Advanced Memristor/ReRAM Testing Suite:**
  - **IV Loop Testing:** Perform repeated triangular voltage sweeps to observe resistive switching hysteresis.
  - **Retention Testing:** Program the device to SET/RESET states and monitor resistance over time.
  - **Endurance Testing:** Cycle the device between SET and RESET states for thousands of cycles to test its durability.
- **Data Handling:**
  - Live data display in a table.
  - Export all measurement data to a `.csv` file with metadata.
  - Built-in plotting for quick data visualization.

##  Prerequisites

Before running the application, you need to have the following installed:

1.  **Python 3.x**
2.  A **VISA Backend Library** installed on your system. This is required for `pyvisa` to communicate with the hardware. The most common is [NI-VISA](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html).
3.  The required Python packages.

##  Installation & Usage

1.  **Download single file code**

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    ```bash
    python SMU_APP.py
    ```

4.  **Using the App:**
    - Enter the VISA address of your Keithley SMU (e.g., `GPIB0::24::INSTR`).
    - Click "Connect".
    - Navigate to the desired measurement tab.
    - Set your parameters and click the "Start" button for the test.
    - View live results in the "Data Table" tab.
    - Export your data using the "Export CSV" button.
