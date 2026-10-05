# 🔥 SLAYIN - AI-Powered Personal Fashion Stylist

> Slay every outfit with AI-driven fashion intelligence

## 💡 Problem Statement

In today's world, people have endless clothing options but struggle to decide which outfits suit their body type, skin tone, occasion, and personal style. Lack of fashion knowledge and personalized guidance leads to poor outfit choices, impacting confidence and appearance.

## ✨ Solution

**SLAYIN** is an AI-powered personal fashion assistant that analyzes your fashion sense, body features, and preferences to recommend outfits — just like having a personal stylist in your pocket.

## 🎯 Features

- **Clothing Upload & Analysis**: Computer-vision tagging of category, colour, pattern and style
- **Digital Wardrobe**: Organise your closet with searchable clothing embeddings
- **Personalized Recommendations**: Occasion-aware outfit suggestions with colour matching
- **Style Learning**: Preferences and feedback improve recommendations over time
- **AI Stylist Chat**: Conversational styling assistant grounded in your wardrobe
- **Wardrobe Intelligence**: Usage insights, versatility and gap analysis
- **Outfit History** and **AI-generated outfit visuals**

> **Future scope:** body-type detection, skin-tone analysis, virtual try-on and AR.

## 🚀 Tech Stack

- **Backend**: Python 3.13, FastAPI
- **AI/ML**: PyTorch (CPU), OpenCLIP, rembg, OpenCV, scikit-learn
- **LLM / Image generation**: Google Gemini
- **Frontend**: React + Vite
- **Database**: SQLite (MVP) → PostgreSQL, via SQLAlchemy + Alembic
- **Dataset**: DeepFashion2 (non-commercial research licence)
- **Deployment**: Docker

## 📦 Installation (Windows / PowerShell)

```powershell
# Virtual environment
python -m venv venv
venv\Scripts\activate

# Backend dependencies
pip install -r requirements.txt

# Environment variables (then add your GEMINI_API_KEY)
copy .env.example .env

# Run the API  ->  http://127.0.0.1:8000/docs
python -m src.main

# Run the frontend (new terminal)  ->  http://localhost:5173
cd frontend
npm.cmd install
npm.cmd run dev
```
