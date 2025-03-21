# Aeris_Voice_Assistant

An interactive AI-powered voice assistant that supports multiple characters and languages. It allows users to interact through **speech** or **text**, generating AI responses in real-time.

## 🚀 Features

- 🎤 **Voice Recognition** - Convert speech to text using `SpeechRecognition`.  
- 🗣️ **Text-to-Speech (TTS)** - AI-generated responses using Google Gemini API.  
- 🔄 **Multi-Language Support** - Speak and receive responses in different languages.  
- 🏆 **Character-Based Voices** - Choose from multiple AI-generated character voices.  
- 🌐 **Web Interface** - User-friendly web UI built with **Flask** & **JavaScript**.  
- 🔐 **User Authentication** - Secure login & signup with JWT-based authentication.  
- 📡 **Real-time Communication** - Support for WebSockets via `Flask-SocketIO` (if enabled).  
- 🌍 **Cross-Origin Support** - `flask-cors` allows secure API interactions.  

---

## 📂 Project Structure

```
📦 AI-Voice-Assistant
├── 📁 static
│   ├── 📂 css
│   │   ├── styles.css
│   │   ├── auth.css
│   ├── 📂 js
│   │   ├── app.js
│   │   ├── auth.js
├── 📁 templates
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── reset_password.html
├── app.py        # Main Flask application
├── assistant.py  # AI assistant logic
├── authentication.py  # User authentication system
├── gladia_api.py  # API integration for audio processing
├── system.py  # Core system functions
├── tts.py  # Text-to-Speech implementation
├── requirements.txt  # Project dependencies
└── README.md  # Project documentation
```

---

## 🛠️ Installation

### 1️⃣ Clone the repository
```sh
git clone https://github.com/your-username/AI-Voice-Assistant.git
cd AI-Voice-Assistant
```

### 2️⃣ Create a virtual environment & activate it
```sh
python -m venv venv
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate  # On Windows
```

### 3️⃣ Install dependencies
```sh
pip install -r requirements.txt
```

### 4️⃣ Set up environment variables
Create a `.env` file in the project root and add:
```ini
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
```

### 5️⃣ Run the Flask application
```sh
flask run
```
The app will be available at `http://127.0.0.1:5000/`.

---

## 🔗 API Endpoints

| Endpoint         | Method | Description |
|-----------------|--------|-------------|
| `/`             | GET    | Home page |
| `/login`        | POST   | User login |
| `/signup`       | POST   | User signup |
| `/reset_password` | POST | Handles password reset |
| `/process_audio`| POST   | Processes recorded voice input |
| `/process_text` | POST   | Processes text input and generates AI response |

---

## 📸 Screenshots

🚀 *Add screenshots of your app UI here!*

---

## 📜 License

This project is licensed under the **MIT License**.

---

## 🏗️ Future Enhancements

- [ ] 🎧 Enhance real-time voice streaming  
- [ ] 🌍 Expand language models  
- [ ] 📊 Add analytics for user interactions  
- [ ] 📱 Create a mobile-friendly UI  

---

## 🤝 Contributing

Pull requests are welcome! For major changes, open an issue first to discuss the proposal.

```sh
git checkout -b feature-branch
git commit -m "Added new feature"
git push origin feature-branch
```

---

## 🛠️ Tech Stack

- **Backend**: Flask, Google Gemini API, Flask-SocketIO, Flask-Login  
- **Frontend**: HTML, CSS, Bootstrap, JavaScript  
- **Audio Processing**: SpeechRecognition, Pydub, Librosa  

---

## 📞 Contact

👨‍💻 Created by **Your Name**  
📧 Email: `your.email@example.com`  
🔗 GitHub: [your-username](https://github.com/your-username)

---

🚀 **Ready to go? Clone, Install, and Run!** 🎙️✨
