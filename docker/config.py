import os

class Config:
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*') 