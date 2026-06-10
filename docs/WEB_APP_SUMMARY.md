# Web Application - Complete Implementation

## Overview

A full-stack local web application that provides a user-friendly interface for Trackman report generation. Designed for non-technical users who need to generate reports without using command-line tools.

## Architecture

### Backend (Flask)
- **File**: `web_app/app.py`
- **Framework**: Flask (Python web framework)
- **Port**: 5000 (localhost only)
- **Security**: Local-only, not accessible from network

### Frontend (HTML/CSS/JavaScript)
- **File**: `web_app/templates/index.html`
- **Design**: Modern, responsive, gradient-based UI
- **Features**: Drag-and-drop, real-time progress, tabbed interface

## Features Implemented

### ✅ File Upload
- Drag-and-drop CSV file upload
- Click-to-browse file selection
- File validation (CSV only, 50MB max)
- Visual feedback during upload

### ✅ Automatic Metadata Extraction
- Pitcher name extracted from CSV data automatically
- Date extracted from filename automatically
- Opponent and game info can be auto-filled from path

### ✅ Report Generation
- Background job processing (non-blocking)
- Real-time progress updates
- Status polling for completion
- Error handling and user feedback

### ✅ Report Management
- View all generated reports
- Download reports directly from browser
- Report list with creation dates
- Automatic refresh capability

### ✅ User Experience
- Clean, modern interface
- No technical knowledge required
- Clear instructions and feedback
- Responsive design

## File Structure

```
web_app/
├── app.py                 # Flask backend server
├── templates/
│   └── index.html        # Frontend interface
└── README.md             # Web app documentation

START_WEB_APP.bat         # Windows launcher
START_WEB_APP.ps1         # PowerShell launcher
```

## How to Use

### For End Users

1. **Start the application:**
   - Double-click `START_WEB_APP.bat`
   - Or run: `python web_app\app.py`

2. **Open browser:**
   - Go to: `http://localhost:5000`

3. **Generate report:**
   - Drag CSV file onto the page
   - Click "Generate Report"
   - Wait for completion
   - Download from "View Reports" tab

### For Developers

The application uses:
- Flask for routing and API endpoints
- Background threading for report generation
- In-memory job queue for status tracking
- Pandas for CSV processing
- Existing report generation pipeline

## API Endpoints

- `GET /` - Main page
- `POST /upload` - Upload CSV and start report generation
- `GET /status/<job_id>` - Check job status
- `GET /reports` - List all generated reports
- `GET /download/<filename>` - Download a report

## Technical Details

### Job Processing
- Jobs are processed in background threads
- Status tracked in-memory dictionary
- Progress updates via polling
- Non-blocking UI during generation

### File Handling
- Uploaded files stored in `uploads/` directory
- Generated reports in `BaseballData/` directory
- Secure filename handling
- File size limits enforced

### Error Handling
- Graceful error messages
- User-friendly feedback
- Server-side logging
- Client-side error display

## Security Considerations

- **Local-only**: Runs on 127.0.0.1 (localhost)
- **No network access**: Not accessible from other computers
- **File validation**: Only CSV files accepted
- **Size limits**: 50MB maximum file size
- **Secure filenames**: Werkzeug secure_filename used

## Comparison: Web vs Command Line

### Web Interface Advantages
- ✅ No technical knowledge required
- ✅ Visual feedback and progress
- ✅ Drag-and-drop file upload
- ✅ Easy report management
- ✅ User-friendly error messages

### Command Line Advantages
- ✅ Faster for batch processing
- ✅ Scriptable/automated
- ✅ More control over options
- ✅ Better for technical users

## Future Enhancements (Optional)

- Batch file upload
- Report preview before download
- Email report delivery
- Report templates/customization
- User authentication (if needed)
- Database for report history
- Advanced filtering/search

## Dependencies

- Flask >= 3.0.0
- All existing dependencies (pandas, matplotlib, etc.)

## Testing

To test the application:
1. Start the server
2. Upload a test CSV file
3. Verify report generation
4. Check report download
5. Test error handling with invalid files

## Support

For issues:
- Check server console for errors
- Verify file format (must be CSV)
- Ensure dependencies are installed
- Review `web_app/README.md` for details

