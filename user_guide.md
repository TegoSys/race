# Race Agent User Guide

Welcome to the Race Agent analytics platform. This guide provides instructions on how to use the system to upload, process, and visualize race telemetry data.

## 🚀 Getting Started

### Backend Setup
1. Navigate to the `backend` directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   .\venv\Scripts\activate    # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. **Database Setup (Docker)**:
   - The system uses Docker Compose to manage the PostgreSQL database.
   - From the **project root**, start the database container:
     ```bash
     docker-compose up -d
     ```
   - If you need to customize the database credentials, you can modify the `docker-compose.yml` file or use a `.env` file in the `backend` directory.
   - **Note**: The database schema is automatically checked and initialized on API startup.
5. Start the API server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Navigate to the `frontend` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

---

## 🛠 Feature Guide

### 1. Uploading Data
- Go to the **Upload** page.
- Select a CSV file from your local system.
- The system supports both standard CSVs and **MoTeC CSV** formats.
- Once uploaded, the file is stored in the backend storage directory and registered in the database.

### 2. Data Processing
- After uploading, you can trigger the processing pipeline.
- The system extracts:
    - **Metadata**: Race info, driver, and car details.
    - **Channel Statistics**: Min, max, average, and standard deviation for all numeric channels.
    - **Correlations**: Automatically detects and calculates correlations between key channels (e.g., Throttle vs. Manifold Pressure).

### 3. Data Visualization & Analysis
The **Analysis** page allows you to deeply explore your telemetry data using a high-performance visualization engine.

#### How to use the Analysis Dashboard:
1. **Select a File**: Use the dropdown to choose a previously uploaded data file.
2. **Choose Channels**: Select one or more columns (channels) from the list to visualize.
3. **Adjust Downsampling**: 
    - Telemetry files can be massive. Use the **Downsample Factor** slider to control how many rows are loaded.
    - *Example*: A factor of `10` loads every 10th row, significantly improving performance while maintaining the trend of the data.
4. **Analyze Visualizations**:
    - **Time Series Plot**: View how selected channels change over the course of the race.
    - **Distribution Histograms**: See the frequency distribution of values for each selected channel (30-bin histogram).
    - **Data Table**: Scroll through the raw (downsampled) values for precision inspection.
5. **Review File Summary**:
    - Switch to the **File Summary** tab to view aggregated insights.
    - **Metadata Grid**: Quickly view key race and file details.
    - **Channel Statistics**: 
      - Use the **Search** box to find specific channels.
      - **Favorites**: Click the star icon next to a channel to mark it as a favorite. Enable **Favorites Only** to filter the table to your most important channels.
    - **Correlation Insights**: View a visual ranking of the strongest relationships between channels, color-coded by strength.
6. **Save Your Work**:
    - Click **Save Plots as Image** to export the current dashboard view as a PNG file for reports or sharing.

---

## 🎨 Design Philosophy
The interface follows the **"Apple Liquid Glass"** aesthetic:
- **Translucency**: Use of `backdrop-blur` and semi-transparent backgrounds.
- **Frosted Glass**: Panels are designed to look like frosted glass over a deep slate background.
- **PWA Ready**: The app is configured as a Progressive Web App for a native-like experience on desktop and mobile.

## 📈 Data Format Support
- **Standard CSV**: Assumes the header is on the first line.
- **MoTeC CSV**: Automatically handles the multi-line MoTeC header (metadata in lines 1-12, columns on line 15, units on line 16, and data starting at line 19).
