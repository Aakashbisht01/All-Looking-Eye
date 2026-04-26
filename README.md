All Looking EyeAI-Powered Anomaly Detection SystemWelcome to All Looking Eye. This is a real-time violence and anomaly detection system built using LSTM deep learning models and pose estimation. The goal of this project is to analyze human body movements across various video sources to detect abnormal or violent behavior and immediately notify administrators.Core FeaturesPose-Based Analysis: Instead of basic object tracking, the system uses an LSTM model to analyze the sequence of body movements to accurately flag violent behavior.Flexible Input Sources: You can run detection on pre-recorded video uploads, a local webcam, or connect directly to live CCTV streams (RTSP/HTTP/HLS).Real-Time Processing: The system provides live visual feedback, drawing a skeleton overlay and displaying confidence scores directly on the feed.Automated Alert System: When an anomaly is detected, the backend automatically clips a 5-second video of the incident and sends it out via email notification.Persistent Logging: All detection events are logged into a MongoDB database so you can review the history later.Web Interface: Everything is controlled through a responsive, browser-based dashboard.Tech StackComponentTechnologyBackendFlask, Python 3.10+ML/DL EngineTensorFlow/Keras, MediaPipe, OpenCVDatabaseMongoDBFrontendHTML5, CSS3, JavaScriptAlertingSMTP (Gmail compatible)Getting StartedTo get this running on your local machine, you will need Python 3.10+, an instance of MongoDB (either local or Atlas), and an SMTP email account to handle the outgoing alerts.1. Clone the RepositoryBashgit clone https://github.com/aakashbisht01/all-looking-eye.git
cd all-looking-eye
2. Set Up the EnvironmentIt is highly recommended to use a virtual environment to manage dependencies.Bashpython -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
3. Install DependenciesBashpip install -r requirements.txt
4. Add the ML ModelsThe trained model weights are too large to be hosted directly in this repository. You will need to place the following files into the root directory of the project:final_model_normalized.keras (Primary model)best_model_81acc.keras (Backup model)5. Configure Environment VariablesCreate a file named .env in the root directory and configure your specific details:Code snippet# Database configuration
MONGODB_URI=mongodb://localhost:27017/all_looking_eye

# Email alert configuration (Gmail example)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Application Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
6. Boot the ServerBashcd backend
python app.py
Once the server is running, you can access the dashboard by navigating to http://localhost:5000 in your browser.Project ArchitecturePlaintextAll-Looking-Eye/
├── backend/
│   ├── app.py              # Main Flask application entry point
│   ├── config.py           # Core configuration settings
│   ├── models/             # Database schemas
│   ├── routes/             # API endpoint definitions
│   └── services/           # ML detectors and email dispatchers
├── frontend/
│   ├── dashboard.html      # Main web interface
│   ├── css/                
│   └── js/                 
├── outputs/                # Directory for processed video results
├── uploads/                # Temporary directory for incoming files
├── requirements.txt        
└── .env                    
How the Detection Pipeline WorksFrame Capture: The backend pulls raw video frames from your selected input source.Pose Estimation: We use MediaPipe to extract 33 distinct body landmarks from each person in the frame.Sequence Analysis: The system collects these landmarks over a 150-frame sequence and feeds them into the LSTM model to understand the motion over time.Scoring: The model outputs a confidence score between 0 and 1 indicating the likelihood of anomalous behavior.Action: If the score exceeds the configured threshold, the system triggers the alert protocol and saves the relevant footage.Configuration OptionsYou can tune the system's sensitivity and behavior by adjusting these variables in backend/config.py:SettingDefaultDescriptionMODEL_PATHfinal_model_normalized.kerasTarget path for the active modelSEQUENCE_LENGTH150Number of frames required for one predictionANOMALY_THRESHOLD0.5The confidence score required to trigger an alertCLIP_DURATION5Length (in seconds) of the video clip attached to alertsNote on Email SetupIf you are using Gmail for the SMTP server, you cannot use your standard account password. You will need to enable 2-Factor Authentication on your Google account and generate a specific "App Password" to place in your .env file.LicenseThis project is licensed under the MIT License. See the LICENSE file for more information.
