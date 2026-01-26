# Ezquela - Face Recognition Attendance System

A comprehensive web-based attendance management system that uses facial recognition technology to automate student attendance tracking in educational institutions.

## 🌟 Features

### For Administrators
- **Complete Institution Management**
  - Manage courses, departments, and academic programs
  - Add and manage staff members
  - Register and oversee students
  - Create and update subject assignments
  - Generate and manage class timetables

### For Teachers/Staff
- **Smart Attendance System**
  - Take attendance using real-time face recognition
  - Manual attendance adjustment capabilities
  - View class-wise student lists with attendance percentages
  - Monitor students with attendance shortage alerts
  - Manage student leave requests (approve/reject)

### For Students
- **Self-Service Portal**
  - View personal profile and attendance records
  - Train facial recognition model with photo uploads
  - Apply for leave with status tracking
  - View assigned subjects and faculty details
  - Track attendance percentage by subject

### Core Capabilities
- **AI-Powered Face Recognition** using OpenCV LBPH algorithm
- **Role-Based Access Control** (Admin, Teacher, Student)
- **Real-Time Attendance Tracking** with live camera feed
- **Automated Timetable Generation**
- **Leave Management System**
- **Comprehensive Reporting & Analytics**

## 🛠️ Technology Stack

### Backend
- **Flask** - Python web framework
- **PyMySQL** - MySQL database connector with connection pooling
- **OpenCV** - Computer vision and face recognition
- **Pillow** - Image processing

### Frontend
- **Bootstrap 5** - Responsive UI framework
- **Font Awesome** - Icon library
- **jQuery** - DOM manipulation and AJAX

### Database
- **MySQL 8.0** - Relational database management

### Deployment
- **Docker** & **Docker Compose** - Containerization
- **Gunicorn-ready** architecture

## 📋 Prerequisites

- Docker Desktop (or Docker + Docker Compose)
- 4GB RAM minimum
- Webcam/Camera for face recognition features

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone [https://github.com/ShaijoGeorge/ezquela.git](https://github.com/ShaijoGeorge/Ezquela-Attendance.git)
cd ezquela
```

### 2. Start the Application
```bash
docker-compose up --build
```

This will:
- Build the Flask application container
- Set up MySQL database with sample data
- Start both services
- Make the application available at `http://localhost:5000`

### 3. Access the System
Open your browser and navigate to:
```
http://localhost:5000
```

## 🔐 Default Login Credentials

### Administrator
```
Username: admin
Password: admin123
```

### Sample Teacher
```
Username: staff01
Password: staff123
```

### Sample Student
```
Username: student01
Password: student123
```

> **⚠️ Security Note:** Change these credentials immediately after first login.

## 📁 Project Structure
```
ezquela/
├── static/
│   ├── photos/
│   │   ├── studentphoto/    # Student profile images
│   │   └── staffphoto/      # Staff profile images
│   ├── dataset/             # Face training datasets (s{id}/)
│   └── test/                # Temporary face detection images
├── templates/
│   ├── admin/               # Admin dashboard templates
│   ├── staff/               # Teacher portal templates
│   └── student/             # Student portal templates
├── webcode.py               # Main Flask application
├── facemaster.py            # Face recognition module
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
├── compose.yaml            # Docker Compose setup
└── attendance_face.dump    # Database initialization SQL
```

## 🎯 Key Workflows

### Taking Attendance (Teacher)
1. Login as Teacher
2. Navigate to "Take Attendance"
3. Select Subject, Division, and Hour
4. Click "Launch Camera"
5. System automatically detects and marks students present
6. Manually adjust any incorrect entries using toggle switches
7. Click "End Class" to finalize

### Training Face Model (Student)
1. Login as Student
2. Go to "Train Face Model"
3. Upload 10-20 clear photos of your face
   - Different angles recommended
   - Good lighting conditions
4. System processes and trains the AI model
5. You're ready for attendance recognition!

### Managing Departments (Admin)
1. Login as Administrator
2. Navigate to "Departments"
3. Select a Course
4. Add/Edit/Delete departments
5. Assign to appropriate courses

## ⚙️ Configuration

### Environment Variables
Edit `compose.yaml` to customize:
```yaml
environment:
  - DB_HOST=ezquela-db
  - DB_USER=root
  - DB_PASSWORD=root          # Change in production!
  - DB_NAME=attendance_face
```

### Database Connection Pooling
The system uses connection pooling for optimal performance:
- **Max Connections:** 10
- **Min Cached:** 2
- **Max Cached:** 5

Adjust in `webcode.py` if needed:
```python
pool = PooledDB(
    maxconnections=10,
    mincached=2,
    maxcached=5,
    # ...
)
```

## 📊 Database Schema Highlights

### Key Tables
- **login** - User authentication (admin/teacher/student)
- **courses** - Academic programs (B.Tech, M.Tech, etc.)
- **department** - Academic departments linked to courses
- **teacher** - Staff information
- **student** - Student records
- **subject** - Course subjects with staff assignments
- **attendence** - Attendance records (date, hour, status)
- **timetable** - Class schedules
- **leave** - Leave requests and approvals

## 🧪 Testing

### Manual Testing Checklist
- [ ] Admin can create courses and departments
- [ ] Admin can register staff and students
- [ ] Teacher can take attendance via camera
- [ ] Student face is correctly recognized
- [ ] Leave requests flow (apply → approve/reject)
- [ ] Timetable generation works correctly
- [ ] Attendance reports show accurate percentages
- [ ] Password change functionality works
- [ ] Profile editing updates database

**Built with ❤️ for modern educational institutions**

*Making attendance tracking smarter, faster, and more efficient.*
