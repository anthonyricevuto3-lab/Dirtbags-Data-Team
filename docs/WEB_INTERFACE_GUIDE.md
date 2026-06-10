# Web Interface User Guide

## For Non-Technical Users

This guide is for staff members who want to generate Trackman reports without using command-line tools.

## Getting Started

### Step 1: Start the Web Application

**Option A - Double-Click (Easiest):**
- Find the file `START_WEB_APP.bat` on your computer
- Double-click it
- A window will open showing the server is starting

**Option B - From Command Prompt:**
- Open Command Prompt or PowerShell
- Navigate to the project folder
- Type: `python web_app\app.py`
- Press Enter

### Step 2: Open Your Web Browser

Once the server is running, you'll see a message like:
```
Open your browser to: http://localhost:5000
```

1. Open any web browser (Chrome, Firefox, Edge, Safari)
2. Type in the address bar: `http://localhost:5000`
3. Press Enter

### Step 3: Generate a Report

1. **Select a File**
   - You'll see a large box that says "Click to select a file or drag and drop"
   - **Option 1**: Click the box and browse for your Trackman CSV file
   - **Option 2**: Drag your CSV file from Windows Explorer and drop it on the box

2. **Fill in Information (Optional)**
   - **Pitcher Name**: Leave blank - it will be found automatically from the file
   - **Opponent**: Type the opponent name (defaults to "Practice")
   - **Game/Session**: Type the game number or session (e.g., "Game1" or "Session4")
   - **Date**: Leave blank - it will be found automatically from the filename

3. **Generate Report**
   - Click the blue "Generate Report" button
   - Watch the progress bar - it will show the report is being created
   - When complete, you'll see a success message

4. **Download Report**
   - Click the "View Reports" tab at the top
   - Find your report in the list
   - Click the "Download" button to save it to your computer

## Tips

- **File Format**: Only CSV files from Trackman will work
- **File Size**: Files up to 50MB are supported
- **Auto-Detection**: The system automatically finds:
  - Pitcher name from the CSV file
  - Date from the filename
  - So you can leave most fields blank!

## Troubleshooting

### "Can't connect to server"
- Make sure you started the web application first (Step 1)
- Check that the server window is still open
- Try refreshing your browser

### "File upload failed"
- Make sure the file is a CSV file (ends in .csv)
- Check that the file isn't too large (under 50MB)
- Try a different file to see if the problem is with that specific file

### "Report generation error"
- Check the server window for error messages
- Make sure the CSV file is a valid Trackman export
- Try a different CSV file

### "Port already in use"
- Another program might be using port 5000
- Close other applications
- Or contact the technical team to change the port

## What Happens Behind the Scenes

1. You upload a CSV file
2. The system reads the file and finds the pitcher name automatically
3. It cleans and organizes the data
4. It creates all the charts and tables
5. It generates a PDF report
6. The report is saved and ready to download

**You don't need to understand any of this - just upload and click!**

## Security

- This web application only runs on your computer
- It's not accessible from the internet
- All files stay on your machine
- No data is sent anywhere

## Need Help?

If you encounter issues:
1. Check the server window for error messages
2. Try refreshing the browser page
3. Restart the web application
4. Contact the technical team if problems persist

