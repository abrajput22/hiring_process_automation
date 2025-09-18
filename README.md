# AI-Powered Hiring Process Management System

A comprehensive, automated hiring platform that streamlines the entire recruitment process from application to final selection using AI-powered resume screening and automated workflows.

## 🚀 Features

### Core Functionality
- **AI Resume Screening**: Automated resume evaluation using Gemini AI with job description matching
- **Multi-Stage Assessment**: Resume screening → Online Assessment → HR Scoring → Final Selection
- **Automated Workflows**: Scheduled processes with deadline-based triggers
- **Email Notifications**: Automated candidate communication at each stage
- **Real-time Dashboard**: HR and candidate portals with live status updates

### User Roles
- **HR Portal**: Process management, candidate scoring, workflow monitoring
- **Candidate Portal**: Application submission, assessment taking, status tracking
- **Admin Features**: Process creation, scheduling, and analytics

### Automation Features
- **Smart Scheduling**: APScheduler-based deadline management
- **LangGraph Workflows**: Complex multi-step hiring processes
- **Email Automation**: Template-based notifications for all stages
- **Score Calculation**: Weighted scoring system for final selection

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **Python 3.8+**: Core programming language
- **MongoDB**: NoSQL database for flexible data storage
- **Motor**: Async MongoDB driver for Python
- **Pydantic**: Data validation and settings management

### AI & Automation
- **Google Gemini AI**: Resume screening and job matching
- **LangGraph**: Workflow orchestration and state management
- **APScheduler**: Background job scheduling and automation
- **LangChain**: AI model integration and prompt management

### Frontend
- **HTML5/CSS3**: Modern web standards
- **JavaScript (ES6+)**: Interactive user interfaces
- **Tailwind CSS**: Utility-first CSS framework
- **Responsive Design**: Mobile-friendly interfaces

### Email & Communication
- **Gmail SMTP**: Free email service integration
- **Template Engine**: Dynamic email content generation
- **Multi-stage Notifications**: Automated candidate communication

### Authentication & Security
- **JWT Tokens**: Secure authentication system
- **Role-based Access**: HR and candidate permission management
- **Session Management**: Secure user sessions

### Deployment & DevOps
- **Render**: Cloud deployment platform
- **Environment Variables**: Secure configuration management
- **CORS**: Cross-origin resource sharing
- **Static File Serving**: Efficient asset delivery

## 📋 System Architecture

### Workflow Pipeline
1. **Application Stage**: Candidates submit resumes
2. **AI Screening**: Gemini AI evaluates resume-job fit
3. **Online Assessment**: Python MCQ tests for shortlisted candidates
4. **HR Scoring**: Technical and HR evaluation
5. **Final Selection**: Weighted scoring and automated notifications

### Database Schema
- **Candidates**: User profiles and authentication
- **Applications**: Resume submissions per process
- **Processes**: HR-created hiring workflows
- **Assessments**: Online test questions and results

### API Architecture
- **RESTful APIs**: Clean, resource-based endpoints
- **Async Operations**: Non-blocking database operations
- **Error Handling**: Comprehensive exception management
- **Data Validation**: Pydantic model validation

## 📂 Project Structure
hiring_process_automation/
├── app/                # FastAPI application
│   ├── routes/         # API routes
│   ├── models/         # Pydantic models
│   ├── services/       # Business logic
│   └── utils/          # Helper functions
├── tests/              # Unit and integration tests
├── requirements.txt    # Python dependencies
├── render.yaml         # Deployment configuration
└── README.md           # Documentation



## 🔧 Installation & Setup

### Prerequisites
- Python 3.8+
- MongoDB instance
- Gmail account with App Password
- Gemini AI API key

### Environment Variables
```bash
MONGODB_URI=mongodb://localhost:27017/hiring_process
GEMINI_API_KEY=your_gemini_api_key
GMAIL_USERNAME=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
PORT=8000
```

### Local Development
```bash
# Clone repository
git clone <repository-url>
cd hiring-process

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Run application
python app.py
```

### Deployment (Render)
1. Connect GitHub repository to Render
2. Set environment variables in Render dashboard
3. Deploy using `render.yaml` configuration

## 📊 Key Metrics & Performance

### Automation Benefits
- **90% Time Reduction**: Automated resume screening
- **Real-time Processing**: Instant candidate status updates
- **Scalable Architecture**: Handle multiple concurrent processes
- **Email Automation**: 100% automated candidate communication

### Scoring System
- **Resume Match**: AI-powered job description alignment
- **Assessment Score**: Technical competency evaluation
- **HR Evaluation**: Soft skills and cultural fit
- **Final Score**: Weighted combination (40% OA + 30% Tech + 30% HR)

## 🎯 Use Cases

### For HR Teams
- Create and manage multiple hiring processes
- Monitor candidate progress in real-time
- Automated screening saves manual review time
- Data-driven selection with scoring metrics

### For Candidates
- Simple application process with resume upload
- Real-time status tracking
- Automated email notifications
- Fair, AI-powered evaluation

### For Organizations
- Standardized hiring process
- Reduced time-to-hire
- Improved candidate experience
- Scalable recruitment solution

## 🔮 Future Enhancements

- **Video Interview Integration**: Automated scheduling and recording
- **Advanced Analytics**: Hiring metrics and insights dashboard
- **Multi-language Support**: Internationalization features
- **Integration APIs**: Connect with existing HR systems
- **Mobile App**: Native mobile applications for candidates

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 Support

For support and questions, please open an issue in the GitHub repository or contact the development team.

---

**Built with ❤️ using modern AI and web technologies**
