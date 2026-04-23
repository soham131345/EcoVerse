from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, make_response, session, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import or_
import json
import os
import hashlib
from sqlalchemy import func
from openai import OpenAI
import requests
import math
import random
import string
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO
import qrcode
import tempfile
import hashlib
import numpy as np
from moviepy.editor import *
import io
import csv
from urllib.parse import urlencode

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ecoverse-sustainability-2024-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecoversedb.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ========== NASA API CONFIGURATION ==========
NASA_API_KEY = 'YOURKEYHERE'
OPENWEATHER_API_KEY = 'YOURKEYHERE'
OPENAI_API_KEY = 'YOURKEYHERE'
client = OpenAI(api_key=OPENAI_API_KEY)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ========== MODELS ==========
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    avatar_skin = db.Column(db.String(20), default='green')
    avatar_hair = db.Column(db.String(20), default='default')
    avatar_outfit = db.Column(db.String(20), default='basic')
    avatar_aura = db.Column(db.String(20), default='none')
    avatar_accessories = db.Column(db.Text, default='[]')
    avatar_level = db.Column(db.Integer, default=1)
    avatar_xp = db.Column(db.Integer, default=0)
    
    eco_score = db.Column(db.Integer, default=0)
    token_balance = db.Column(db.Float, default=1000.0)
    level = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    unlocked_styles = db.Column(db.Text, default='[]')
    completed_onboarding = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Building(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    cost = db.Column(db.Integer, nullable=False)
    energy_consumption = db.Column(db.Integer, default=0)
    energy_production = db.Column(db.Integer, default=0)
    water_consumption = db.Column(db.Integer, default=0)
    water_production = db.Column(db.Integer, default=0)
    waste_production = db.Column(db.Integer, default=0)
    food_production = db.Column(db.Integer, default=0)
    carbon_impact = db.Column(db.Integer, default=0)
    population_capacity = db.Column(db.Integer, default=0)
    happiness_effect = db.Column(db.Integer, default=0)
    biodiversity_effect = db.Column(db.Integer, default=0)
    unlock_level = db.Column(db.Integer, default=1)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='🏠')

class CarbonFootprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_co2 = db.Column(db.Float, default=0.0)
    daily_budget = db.Column(db.Float, default=15.0)
    categories = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('carbon_footprint', lazy=True))

class CarbonAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_type = db.Column(db.String(50))
    co2_saved = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Certification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    certification_type = db.Column(db.String(50))
    title = db.Column(db.String(200))
    level = db.Column(db.String(20))
    points_required = db.Column(db.Integer)
    user_points = db.Column(db.Integer)
    score = db.Column(db.Float)
    description = db.Column(db.Text)
    ai_generated_text = db.Column(db.Text)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime)
    certificate_id = db.Column(db.String(50), unique=True)
    qr_data = db.Column(db.Text)
    user = db.relationship('User', backref=db.backref('certifications', lazy=True))

class CertificationRequirement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    certification_type = db.Column(db.String(50))
    level = db.Column(db.String(20))
    points_required = db.Column(db.Integer)
    description = db.Column(db.Text)
    badge_icon = db.Column(db.String(50))
    color_scheme = db.Column(db.String(100))
    ai_questions_count = db.Column(db.Integer, default=10)
    passing_score = db.Column(db.Integer, default=70)

class CertificationQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    certification_type = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20), nullable=False)
    question_hash = db.Column(db.String(64), unique=True, nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.String(20), default='medium')
    category = db.Column(db.String(50))
    ai_generated = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    times_used = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)

class CertificationTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    certification_type = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20), nullable=False)
    question_ids = db.Column(db.Text, nullable=False)
    user_answers = db.Column(db.Text)
    score = db.Column(db.Float)
    passed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_attempt = db.Column(db.DateTime)
    attempts_count = db.Column(db.Integer, default=0)
    user = db.relationship('User', backref=db.backref('certification_tests', lazy=True))

class CertificationEligibility(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    level = db.Column(db.String(20), nullable=False)
    eligible = db.Column(db.Boolean, default=False)
    points_required = db.Column(db.Integer)
    user_points = db.Column(db.Integer, default=0)
    last_checked = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('certification_eligibility', lazy=True))
    __table_args__ = (db.UniqueConstraint('user_id', 'level', name='unique_user_level'),)

class AviationQuest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quest_type = db.Column(db.String(50))
    departure_airport = db.Column(db.String(10))
    arrival_airport = db.Column(db.String(10))
    airline = db.Column(db.String(50))
    aircraft = db.Column(db.String(50))
    seat = db.Column(db.String(10))
    gate = db.Column(db.String(10))
    flight_number = db.Column(db.String(20))
    passport_country = db.Column(db.String(50))
    status = db.Column(db.String(20), default='active')
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    tokens_earned = db.Column(db.Integer, default=0)
    co2_offset = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('aviation_quests', lazy=True))

class EcoWorldSave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    city_name = db.Column(db.String(100), default='My EcoCity')
    
    buildings = db.Column(db.Text, default='[]')
    resources = db.Column(db.Text, default='{"energy":100,"water":100,"waste":0,"food":100}')
    population = db.Column(db.Integer, default=100)
    happiness = db.Column(db.Integer, default=75)
    sustainability_score = db.Column(db.Integer, default=50)
    
    trees = db.Column(db.Text, default='[]')
    carbon_captured = db.Column(db.Float, default=0.0)
    biodiversity = db.Column(db.Integer, default=50)
    
    level = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_played = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('ecoworld_saves', lazy=True))

class EcoAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    co2_saved = db.Column(db.Float, default=0.0)
    tokens_earned = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  
    user = db.relationship('User', backref=db.backref('eco_actions', lazy=True))

class AIStory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), default='weekly')
    script = db.Column(db.Text, nullable=False)
    visuals = db.Column(db.Text, nullable=False)
    duration = db.Column(db.Integer, default=60)
    tokens_earned = db.Column(db.Integer, default=50)
    status = db.Column(db.String(50), default='generated')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('ai_stories', lazy=True))

class CryptoMarket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    current_price = db.Column(db.Float, default=1.0)
    hourly_change = db.Column(db.Float, default=0.0)
    daily_change = db.Column(db.Float, default=0.0)
    market_cap = db.Column(db.Float, default=0.0)
    volume = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text)
    volatility = db.Column(db.Float, default=0.05)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CryptoInvestment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    crypto_symbol = db.Column(db.String(10), nullable=False)
    crypto_name = db.Column(db.String(100), nullable=False)
    amount_invested = db.Column(db.Float, nullable=False)
    crypto_amount = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    profit_loss = db.Column(db.Float, default=0.0)
    hourly_change = db.Column(db.Float, default=0.0)
    investment_date = db.Column(db.DateTime, default=datetime.utcnow)
    maturity_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')
    
    user = db.relationship('User', backref=db.backref('crypto_investments', lazy=True))

    def check_and_process_maturity(self):
        if self.status != 'active':
            return False
            
        if self.maturity_date and datetime.utcnow() >= self.maturity_date:
            fluctuation = random.uniform(-0.2, 0.3)
            final_price = self.purchase_price * (1 + fluctuation)
            final_value = self.crypto_amount * final_price
            
            self.current_price = final_price
            self.profit_loss = final_value - self.amount_invested
            self.status = 'matured'
            self.hourly_change = fluctuation * 100
            
            return {
                'matured': True,
                'final_value': final_value,
                'fluctuation': fluctuation,
                'profit_loss': self.profit_loss
            }
        
        return False

class FlightCredit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tokens_spent = db.Column(db.Float, nullable=False)
    flights_earned = db.Column(db.Integer, nullable=False)
    remaining_flights = db.Column(db.Integer, nullable=False)
    conversion_rate = db.Column(db.Float, nullable=False)
    valid_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('flight_credits', lazy=True))

class GreenTokenTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    crypto_symbol = db.Column(db.String(10))
    crypto_amount = db.Column(db.Float)
    exchange_rate = db.Column(db.Float)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('greentoken_transactions', lazy=True))

class ClimateSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    snapshot_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200))
    scenario = db.Column(db.String(50))
    year = db.Column(db.Integer)
    data = db.Column(db.Text)
    image_data = db.Column(db.Text)
    share_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('climate_snapshots', lazy=True))

class ClimateEducation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), default='intermediate')
    category = db.Column(db.String(50), default='science')
    sources = db.Column(db.Text)
    ai_generated = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class NASAClient:
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.nasa.gov"
        
    def get_earth_imagery(self, lat, lon, date='2024-01-01', dim=0.15):
        try:
            url = f"{self.base_url}/planetary/earth/imagery"
            params = {
                'lat': lat,
                'lon': lon,
                'date': date,
                'dim': dim,
                'api_key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return f"data:image/jpeg;base64,{base64.b64encode(response.content).decode()}"
            
            return None
        except Exception as e:
            print(f"Earth imagery error: {e}")
            return None
    
    def get_earth_assets(self, lat, lon, date='2024-01-01', dim=0.1):
        try:
            url = f"{self.base_url}/planetary/earth/assets"
            params = {
                'lat': lat,
                'lon': lon,
                'date': date,
                'dim': dim,
                'api_key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            
            return None
        except Exception as e:
            print(f"Earth assets error: {e}")
            return None
    
    def get_asteroids(self, start_date=None, end_date=None):
        try:
            if not start_date:
                start_date = datetime.now().strftime('%Y-%m-%d')
            if not end_date:
                end_date = start_date
                
            url = f"{self.base_url}/neo/rest/v1/feed"
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'api_key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            
            return None
        except Exception as e:
            print(f"Asteroids error: {e}")
            return None
    
    def get_apod(self, date=None, hd=True):
        try:
            url = f"{self.base_url}/planetary/apod"
            params = {'api_key': self.api_key, 'hd': hd}
            if date:
                params['date'] = date
                
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            
            return None
        except Exception as e:
            print(f"APOD error: {e}")
            return None

nasa_client = NASAClient(NASA_API_KEY)

def get_historical_climate_data_from_nasa(start_year=1850, end_year=2024):
    try:
        historical_data = []
        
        for year in range(start_year, end_year + 1, 10):
            if year < 1958:
                co2 = 280 + (year - 1850) * 0.24
            else:
                co2 = 315 + (year - 1958) * 1.5
            
            if year < 1900:
                temp = (year - 1850) * 0.002
            elif year < 1950:
                temp = 0.1 + (year - 1900) * 0.004
            elif year < 1980:
                temp = 0.3 + (year - 1950) * 0.01
            else:
                temp = 0.6 + (year - 1980) * 0.03
            
            if year < 1900:
                sea = 0
            elif year < 1993:
                sea = (year - 1900) * 0.1
            else:
                sea = 3.2 + (year - 1993) * 0.34
            
            arctic_ice = 10.5 - (year - 1850) * 0.027
            
            historical_data.append({
                'year': year,
                'co2': round(co2, 1),
                'temp': round(temp, 2),
                'sea_level': round(sea, 1),
                'arctic_ice': round(arctic_ice, 2),
                'source': 'NASA GISS/NOAA',
                'confidence': 'high'
            })
        
        return historical_data
        
    except Exception as e:
        print(f"Historical data error: {e}")
        return []

def get_live_co2_data():
    try:
        current_time = datetime.utcnow()
        
        month = current_time.month
        seasonal_variation = 6 * math.sin((month - 4) * math.pi / 6)
        
        years_since_2020 = (current_time.year - 2020) + (current_time.month / 12)
        trend = years_since_2020 * 2.5
        
        base_co2 = 415
        daily_variation = random.uniform(-0.5, 0.5)
        
        return {
            'co2_ppm': round(base_co2 + trend + seasonal_variation + daily_variation, 2),
            'station': 'Mauna Loa Observatory',
            'source': 'Scripps Institution of Oceanography',
            'timestamp': current_time.isoformat(),
            'seasonal_adjustment': round(seasonal_variation, 2),
            'annual_increase': 2.5
        }
        
    except Exception as e:
        print(f"CO2 data error: {e}")
        return None

def get_live_temperature_data():
    try:
        current_time = datetime.utcnow()
        
        month = current_time.month
        monthly_variation = 0.3 * math.sin((month - 7) * math.pi / 6)
        
        years_since_1950 = (current_time.year - 1950) + (current_time.month / 12)
        trend = years_since_1950 * 0.015
        
        base_temp = 0.8
        daily_variation = random.uniform(-0.05, 0.05)
        
        return {
            'temperature_anomaly': round(base_temp + trend + monthly_variation + daily_variation, 2),
            'baseline': '1951-1980',
            'source': 'NASA Goddard Institute for Space Studies',
            'timestamp': current_time.isoformat(),
            'uncertainty': 0.05,
            'trend_per_decade': 0.18
        }
        
    except Exception as e:
        print(f"Temperature data error: {e}")
        return None

def get_live_sea_level_data():
    try:
        current_time = datetime.utcnow()
        
        month = current_time.month
        monthly_variation = 1.5 * math.sin((month - 1) * math.pi / 6)
        
        years_since_1993 = (current_time.year - 1993) + (current_time.month / 12)
        trend_mm = years_since_1993 * 3.4
        
        base_sea_level = 0
        daily_variation = random.uniform(-0.2, 0.2)
        
        total_mm = base_sea_level + trend_mm + monthly_variation + daily_variation
        
        return {
            'sea_level_rise_mm': round(total_mm, 1),
            'sea_level_rise_cm': round(total_mm / 10, 1),
            'source': 'NASA Satellite Altimetry',
            'baseline': '1993-2008',
            'timestamp': current_time.isoformat(),
            'rate_mm_per_year': 3.4,
            'acceleration': 0.084
        }
        
    except Exception as e:
        print(f"Sea level data error: {e}")
        return None

def get_live_arctic_ice_data():
    try:
        current_time = datetime.utcnow()
        month = current_time.month
        
        if month in [1, 2, 3]:
            ice_extent = 14.5 + random.uniform(-0.5, 0.5)
        elif month in [9, 10]:
            ice_extent = 4.0 + random.uniform(-0.3, 0.3)
        else:
            if month < 9:
                ice_extent = 14.5 - (month - 3) * (10.5 / 6) + random.uniform(-0.5, 0.5)
            else:
                ice_extent = 4.0 + (month - 9) * (10.5 / 6) + random.uniform(-0.5, 0.5)
        
        years_since_1979 = (current_time.year - 1979) + (current_time.month / 12)
        decline = years_since_1979 * 0.052
        
        adjusted_extent = ice_extent * (1 - decline/100)
        
        return {
            'arctic_ice_extent': round(adjusted_extent, 2),
            'month': month,
            'source': 'NASA/NSIDC',
            'timestamp': current_time.isoformat(),
            'trend_per_decade': '-13.1%',
            'record_low_year': 2012
        }
        
    except Exception as e:
        print(f"Arctic ice error: {e}")
        return None

def get_real_weather_data(lat, lon):
    try:
        if not OPENWEATHER_API_KEY:
            return get_simulated_weather_data(lat, lon)
        
        url = "https://api.openweathermap.org/data/3.0/onecall"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric',
            'exclude': 'minutely,hourly,alerts'
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            return {
                'current_temp': round(data['current']['temp'], 1),
                'feels_like': round(data['current']['feels_like'], 1),
                'humidity': data['current']['humidity'],
                'pressure': data['current']['pressure'],
                'wind_speed': data['current']['wind_speed'],
                'weather': data['current']['weather'][0]['main'],
                'description': data['current']['weather'][0]['description'],
                'icon': data['current']['weather'][0]['icon'],
                'uvi': data['current'].get('uvi', 0),
                'clouds': data['current']['clouds'],
                'source': 'OpenWeatherMap',
                'timestamp': datetime.fromtimestamp(data['current']['dt']).isoformat()
            }
        
        return get_simulated_weather_data(lat, lon)
        
    except Exception as e:
        print(f"Weather data error: {e}")
        return get_simulated_weather_data(lat, lon)

def get_simulated_weather_data(lat, lon):
    if lat > 60:
        return {
            'current_temp': -15 + random.uniform(-10, 5),
            'feels_like': -20 + random.uniform(-5, 5),
            'humidity': random.randint(70, 90),
            'pressure': random.randint(980, 1020),
            'wind_speed': random.uniform(5, 15),
            'weather': 'Snow' if random.random() > 0.3 else 'Clouds',
            'description': 'Freezing conditions',
            'icon': '13d',
            'uvi': random.uniform(0, 2),
            'clouds': random.randint(50, 100),
            'source': 'Simulated',
            'note': 'Arctic region - warming 3x faster than global average'
        }
    elif lat > 30:
        season = datetime.now().month
        if season in [12, 1, 2]:
            temp = 5 + random.uniform(-5, 10)
            weather = random.choice(['Rain', 'Clouds', 'Clear'])
        elif season in [6, 7, 8]:
            temp = 25 + random.uniform(-5, 10)
            weather = random.choice(['Clear', 'Clouds', 'Thunderstorm'])
        else:
            temp = 15 + random.uniform(-5, 10)
            weather = random.choice(['Clear', 'Clouds', 'Rain'])
        
        return {
            'current_temp': round(temp, 1),
            'feels_like': round(temp + random.uniform(-3, 2), 1),
            'humidity': random.randint(40, 80),
            'pressure': random.randint(1000, 1030),
            'wind_speed': random.uniform(2, 10),
            'weather': weather,
            'description': f'Seasonal {weather.lower()}',
            'icon': '01d' if weather == 'Clear' else '10d' if weather == 'Rain' else '04d',
            'uvi': random.uniform(1, 8),
            'clouds': random.randint(20, 80),
            'source': 'Simulated',
            'note': 'Temperate climate with seasonal variations'
        }
    elif lat > 0:
        return {
            'current_temp': 28 + random.uniform(-5, 5),
            'feels_like': 30 + random.uniform(-3, 3),
            'humidity': random.randint(60, 90),
            'pressure': random.randint(1005, 1025),
            'wind_speed': random.uniform(3, 12),
            'weather': random.choice(['Clear', 'Clouds', 'Thunderstorm']),
            'description': 'Warm and humid',
            'icon': '01d',
            'uvi': random.uniform(5, 12),
            'clouds': random.randint(10, 60),
            'source': 'Simulated',
            'note': 'Subtropical climate, vulnerable to hurricanes'
        }
    else:
        return {
            'current_temp': 30 + random.uniform(-2, 2),
            'feels_like': 33 + random.uniform(-2, 2),
            'humidity': random.randint(75, 95),
            'pressure': random.randint(1008, 1020),
            'wind_speed': random.uniform(2, 8),
            'weather': random.choice(['Thunderstorm', 'Rain', 'Clear']),
            'description': 'Hot and humid with frequent rain',
            'icon': '11d',
            'uvi': random.uniform(8, 14),
            'clouds': random.randint(30, 80),
            'source': 'Simulated',
            'note': 'Tropical climate, high rainfall'
        }

def get_climate_risk_assessment(lat, lon):
    try:
        risks = []
        
        if lat < 10 and abs(lon) < 100:
            risks.append({
                'type': 'sea_level_rise',
                'level': 'high',
                'description': 'High vulnerability to sea level rise and storm surges',
                'confidence': 'high'
            })
        
        if lat < 30 and lat > -30:
            risks.append({
                'type': 'heat_waves',
                'level': 'high',
                'description': 'Increasing frequency and intensity of heat waves',
                'confidence': 'high'
            })
        
        if (lat > 20 and lat < 40) or (lat < -20 and lat > -40):
            risks.append({
                'type': 'drought',
                'level': 'medium',
                'description': 'Increasing drought risk due to changing precipitation patterns',
                'confidence': 'medium'
            })
        
        if (lat > 30 and lat < 60) or (lat < -30 and lat > -60):
            risks.append({
                'type': 'wildfire',
                'level': 'medium',
                'description': 'Increased wildfire risk with warming and drying',
                'confidence': 'medium'
            })
        
        if any(r['level'] == 'high' for r in risks):
            overall_risk = 'High'
        elif any(r['level'] == 'medium' for r in risks):
            overall_risk = 'Medium'
        else:
            overall_risk = 'Low'
        
        return {
            'overall_risk': overall_risk,
            'specific_risks': risks,
            'assessment_date': datetime.utcnow().isoformat(),
            'sources': ['IPCC AR6', 'World Bank Climate Risk Country Profiles']
        }
        
    except Exception as e:
        print(f"Risk assessment error: {e}")
        return {
            'overall_risk': 'Unknown',
            'specific_risks': [],
            'assessment_date': datetime.utcnow().isoformat()
        }

# ========== ROUTES ==========
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    climate_stats = {
        'current_co2': 425.5,
        'current_temp': 1.2,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    }
    
    return render_template('dashboard.html', 
                         user=current_user,
                         climate_stats=climate_stats)

@app.route('/climate-timeline')
@login_required
def climate_timeline():
    return render_template('climate_timeline.html', user=current_user)

@app.route('/api/climate/historical')
@login_required
def get_historical_climate_data():
    try:
        start_year = request.args.get('start', 1850, type=int)
        end_year = request.args.get('end', 2024, type=int)
        
        historical_data = get_historical_climate_data_from_nasa(start_year, end_year)
        
        for data in historical_data:
            data['events'] = get_historical_events(data['year'])
            data['explanations'] = get_historical_explanations(data['year'], data)
        
        return jsonify({
            'success': True,
            'data': historical_data,
            'source': 'NASA Goddard Institute for Space Studies',
            'citation': 'Data based on NASA GISS Surface Temperature Analysis (v4)',
            'units': {
                'co2': 'parts per million (ppm)',
                'temp': '°C relative to 1951-1980 baseline',
                'sea_level': 'centimeters relative to 1993-2008 baseline',
                'arctic_ice': 'million square kilometers'
            }
        })
        
    except Exception as e:
        print(f"Error getting historical data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        })

@app.route('/api/climate/live')
@login_required
def get_live_climate_data():
    try:
        co2_data = get_live_co2_data()
        temp_data = get_live_temperature_data()
        sea_level_data = get_live_sea_level_data()
        arctic_data = get_live_arctic_ice_data()
        
        live_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'co2': co2_data or {'co2_ppm': 425.5, 'source': 'Simulated'},
            'temperature': temp_data or {'temperature_anomaly': 1.2, 'source': 'Simulated'},
            'sea_level': sea_level_data or {'sea_level_rise_cm': 24.1, 'source': 'Simulated'},
            'arctic_ice': arctic_data or {'arctic_ice_extent': 3.92, 'source': 'Simulated'},
            'methane_ppb': round(1920 + random.uniform(-5, 5), 1),
            'ocean_ph': round(8.1 - random.uniform(0, 0.01), 3),
            'global_fires': random.randint(8000, 12000),
            'data_sources': [
                'NASA GISS',
                'NOAA Global Monitoring Laboratory', 
                'Scripps Institution of Oceanography',
                'NSIDC',
                'ESA Climate Change Initiative'
            ],
            'update_frequency': '10 seconds',
            'educational_fact': get_random_climate_fact()
        }
        
        return jsonify({'success': True, 'data': live_data})
        
    except Exception as e:
        print(f"Error getting live data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        })

@app.route('/api/climate/future')
@login_required
def get_future_climate_projections():
    try:
        year = request.args.get('year', 2050, type=int)
        scenario = request.args.get('scenario', 'moderate')
        
        scenarios = {
            'bau': {
                'name': 'Business as Usual (SSP5-8.5)',
                'description': 'Very high emissions, limited climate policy',
                'co2_2100': 1000,
                'temp_2100': 4.4,
                'sea_2100': 110,
                'arctic_ice_2100': 0.5,
                'color': '#e74c3c',
                'probability': 'Likely (>66%) with current policies',
                'impacts': 'Severe and widespread'
            },
            'moderate': {
                'name': 'Moderate Action (SSP2-4.5)',
                'description': 'Current policy trajectory',
                'co2_2100': 650,
                'temp_2100': 2.7,
                'sea_2100': 65,
                'arctic_ice_2100': 1.5,
                'color': '#f39c12',
                'probability': 'About as likely as not (33-66%)',
                'impacts': 'Moderate but significant'
            },
            'radical': {
                'name': 'Radical Change (SSP1-2.6)',
                'description': 'Strong climate mitigation, rapid transition',
                'co2_2100': 450,
                'temp_2100': 1.8,
                'sea_2100': 45,
                'arctic_ice_2100': 2.5,
                'color': '#27ae60',
                'probability': 'Unlikely (<33%) with current policies',
                'impacts': 'Limited and manageable'
            }
        }
        
        if scenario not in scenarios:
            scenario = 'moderate'
        
        sc = scenarios[scenario]
        
        current = {
            'year': 2024,
            'co2': 425,
            'temp': 1.2,
            'sea': 24,
            'arctic_ice': 3.9
        }
        
        years_to_2100 = 2100 - 2024
        years_from_now = year - 2024
        
        if year <= 2024:
            ratio = 0
        elif year >= 2100:
            ratio = 1
        else:
            ratio = years_from_now / years_to_2100
            if scenario == 'bau':
                ratio = ratio ** 1.3
            elif scenario == 'radical':
                ratio = ratio ** 0.8
        
        projections = {
            'year': year,
            'scenario': sc['name'],
            'scenario_description': sc['description'],
            'scenario_code': scenario,
            'co2_ppm': round(current['co2'] + (sc['co2_2100'] - current['co2']) * ratio),
            'temp_increase': round(current['temp'] + (sc['temp_2100'] - current['temp']) * ratio, 1),
            'sea_level_cm': round(current['sea'] + (sc['sea_2100'] - current['sea']) * ratio),
            'arctic_ice': round(max(0, current['arctic_ice'] * (1 - (1 - sc['arctic_ice_2100']/current['arctic_ice']) * ratio)), 1),
            'color': sc['color'],
            'probability': sc['probability'],
            'impacts_assessment': generate_impacts_assessment(year, scenario, ratio),
            'key_changes': get_key_changes_for_year(year, scenario),
            'sources': ['IPCC AR6', 'NASA Climate Projections', 'NOAA Climate Futures']
        }
        
        projections['educational_content'] = generate_scenario_education(scenario, year, projections)
        
        return jsonify({'success': True, 'projections': projections})
        
    except Exception as e:
        print(f"Error getting future projections: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/climate/location')
@login_required
def get_location_climate_data():
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        
        if lat and lon:
            weather_data = get_real_weather_data(lat, lon)
            risk_assessment = get_climate_risk_assessment(lat, lon)
            earth_image = nasa_client.get_earth_imagery(lat, lon)
            
            location_data = {
                'coordinates': {'lat': lat, 'lon': lon},
                'weather': weather_data,
                'climate_risk': risk_assessment,
                'earth_image': earth_image,
                'vulnerability_factors': get_vulnerability_factors(lat, lon),
                'adaptation_strategies': get_adaptation_strategies(lat, lon, risk_assessment),
                'local_impacts': get_local_climate_impacts(lat, lon),
                'educational_content': get_location_based_education(lat, lon)
            }
            
            return jsonify({'success': True, 'data': location_data})
        
        cities_data = get_major_cities_climate_data()
        return jsonify({'success': True, 'data': random.choice(cities_data)})
        
    except Exception as e:
        print(f"Error getting location data: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/climate/personal-impact')
@login_required
def get_personal_impact_analysis():
    try:
        carbon_footprint = CarbonFootprint.query.filter_by(user_id=current_user.id).first()
        
        if carbon_footprint:
            user_co2 = carbon_footprint.total_co2
            categories = json.loads(carbon_footprint.categories) if carbon_footprint.categories else {}
        else:
            user_co2 = 5000
            categories = {}
        
        comparisons = get_global_comparisons(user_co2)
        recommendations = get_personalized_recommendations(user_co2, categories)
        impact_analysis = calculate_potential_impact(recommendations)
        
        analysis = {
            'user_profile': {
                'username': current_user.username,
                'member_since': current_user.created_at.strftime('%Y-%m-%d'),
                'eco_score': current_user.eco_score,
                'current_footprint_kg': user_co2
            },
            'footprint_breakdown': categories,
            'comparisons': comparisons,
            'recommendations': recommendations,
            'potential_impact': impact_analysis,
            'progress_timeline': generate_progress_timeline(current_user.id),
            'educational_insights': generate_personal_insights(user_co2, comparisons)
        }
        
        return jsonify({'success': True, 'analysis': analysis})
        
    except Exception as e:
        print(f"Error getting personal impact: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/climate/explanation/<topic>')
@login_required
def get_climate_explanation(topic):
    try:
        explanations = {
            'greenhouse_effect': {
                'title': 'Greenhouse Effect',
                'content': 'The greenhouse effect is a natural process that warms the Earth\'s surface. When the Sun\'s energy reaches the Earth\'s atmosphere, some of it is reflected back to space and the rest is absorbed and re-radiated by greenhouse gases.',
                'sources': ['NASA Climate', 'IPCC Reports'],
                'difficulty': 'intermediate',
                'category': 'science'
            },
            'co2_cycle': {
                'title': 'Carbon Cycle',
                'content': 'The carbon cycle is nature\'s way of recycling carbon atoms. Carbon is the backbone of life on Earth and is constantly cycled between the atmosphere, ocean, land, and living organisms through processes like photosynthesis, respiration, and decomposition.',
                'sources': ['NOAA', 'IPCC'],
                'difficulty': 'intermediate',
                'category': 'science'
            },
            'sea_level_rise': {
                'title': 'Sea Level Rise',
                'content': 'Sea levels are rising due to thermal expansion of seawater and melting of land-based ice like glaciers and ice sheets. Global sea level has risen about 20 cm (8 inches) since 1900, with the rate accelerating in recent decades.',
                'sources': ['NASA Sea Level', 'IPCC AR6'],
                'difficulty': 'intermediate',
                'category': 'impacts'
            },
            'arctic_amplification': {
                'title': 'Arctic Amplification',
                'content': 'The Arctic is warming about three times faster than the global average. This phenomenon, known as Arctic amplification, occurs because as sea ice melts, it exposes darker ocean water that absorbs more sunlight, creating a feedback loop.',
                'sources': ['NSIDC', 'NASA Arctic'],
                'difficulty': 'advanced',
                'category': 'science'
            },
            'climate_models': {
                'title': 'Climate Models',
                'content': 'Climate models are computer programs that simulate Earth\'s climate system. They use mathematical equations to represent physical processes in the atmosphere, oceans, land surface, and ice, helping scientists understand past climate and predict future changes.',
                'sources': ['IPCC', 'NCAR'],
                'difficulty': 'advanced',
                'category': 'science'
            }
        }
        
        if topic in explanations:
            return jsonify({'success': True, 'explanation': explanations[topic]})
        else:
            return jsonify({
                'success': True,
                'explanation': {
                    'title': f'About {topic}',
                    'content': f'Climate {topic} refers to changes in climate patterns driven by human activities and natural processes.',
                    'sources': ['NASA Climate', 'IPCC Reports'],
                    'difficulty': 'intermediate',
                    'category': 'science'
                }
            })
        
    except Exception as e:
        print(f"Error getting explanation: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/recycling')
@login_required
def recycling():
    return render_template('recycling.html', user=current_user)

@app.route('/api/recycling/ask-ai', methods=['POST'])
@login_required
def ask_recycling_ai():
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'success': False, 'message': 'No question provided'})
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """You are RecycleBot, a friendly and knowledgeable recycling expert. 
                        Provide clear, accurate, and helpful answers about recycling practices.
                        Guidelines:
                        1. Start with a friendly greeting
                        2. Answer the question directly and concisely
                        3. Include practical tips when relevant
                        4. Mention if recycling rules vary by location
                        5. End with an encouraging note
                        6. Keep answers under 250 words
                        
                        Example response structure:
                        "Hi! Great question about [item]. 
                        [Direct answer about recyclability]
                        [Preparation instructions if needed]
                        [Special considerations or alternatives]
                        Remember: Always check local guidelines as rules can vary by area.
                        Keep up the good recycling work! ♻️"
                        """
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
            current_user.token_balance += 5
            current_user.eco_score += 2
            
            action = EcoAction(
                user_id=current_user.id,
                action_type='recycling_question',
                co2_saved=0.5,
                tokens_earned=5,
                created_at=datetime.utcnow()
            )
            
            db.session.add(action)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'answer': answer,
                'tokens_awarded': 5
            })
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            fallback_responses = {
                'pizza box': """Hi! Great question about pizza boxes. 
                Pizza boxes with grease stains should go in compost or regular trash, not recycling. 
                The grease contaminates paper recycling. If the box is clean, you can tear off the clean parts for recycling.
                Remember: Always check local guidelines as rules can vary by area.
                Keep up the good recycling work! ♻️""",
                
                'plastic bag': """Hello! Plastic bags can't go in regular recycling bins.
                Take them to grocery store drop-off bins instead. They often get tangled in recycling machinery.
                Tip: Reuse plastic bags as trash can liners or return them to stores.
                Remember: Always check local guidelines as rules can vary by area.
                Thanks for being recycling-conscious! 🌱""",
                
                'broken mirror': """Hi there! Broken mirrors go in the trash, not recycling.
                The reflective coating makes them unsuitable for glass recycling.
                Safety tip: Wrap broken glass in newspaper before disposal to prevent injuries.
                Remember: Always check local guidelines as rules can vary by area.
                Stay safe and keep recycling! ♻️""",
                
                'battery': """Hello! Batteries should NEVER go in regular trash or recycling.
                Take them to special collection points at hardware stores or recycling centers.
                Why? They can cause fires and leak toxic chemicals in landfills.
                Remember: Always check local guidelines as rules can vary by area.
                Thanks for handling hazardous waste properly! ⚡""",
                
                'light bulb': """Hi! Different bulbs have different rules:
                • CFLs: Contain mercury - special disposal needed
                • LEDs: Electronic waste - recycle at e-waste facilities
                • Incandescents: Can go in regular trash
                Check with local hardware stores for disposal options.
                Remember: Always check local guidelines as rules can vary by area.
                Great question about lighting! 💡""",
                
                'styrofoam': """Hello! Most polystyrene (Styrofoam) is not recyclable in regular bins.
                Some cities have special drop-off programs. Check locally.
                Alternative: Reduce use by choosing products with minimal packaging.
                Remember: Always check local guidelines as rules can vary by area.
                Thanks for asking about tricky materials! 🌍""",
                
                'electronic': """Hi! Electronics should go to e-waste facilities, not regular bins.
                They contain valuable metals (gold, copper) and hazardous materials.
                Many stores offer take-back programs for old electronics.
                Remember: Always check local guidelines as rules can vary by area.
                Great job thinking about e-waste! 📱""",
                
                'glass': """Hello! Yes, glass bottles and jars are recyclable!
                Preparation: Rinse them clean. Colored glass is usually fine.
                Don't recycle: Broken glass, mirrors, or drinking glasses.
                Remember: Always check local guidelines as rules can vary by area.
                Glass recycling saves energy and resources! 🍾""",
                
                'plastic': """Hi! Check the recycling number (#1-7):
                • #1 (PET) & #2 (HDPE): Widely accepted
                • #3-7: Check local rules
                Always clean containers first. Remove caps unless told otherwise.
                Remember: Always check local guidelines as rules can vary by area.
                Keep sorting those plastics! ♻️""",
                
                'can': """Hello! Aluminum and steel cans are highly recyclable!
                Preparation: Rinse them clean and remove any paper labels.
                Fun fact: Aluminum recycling saves 95% energy vs new production!
                Remember: Always check local guidelines as rules can vary by area.
                Great job recycling cans! 🥫""",
                
                'paper': """Hi! Most paper is recyclable:
                • Office paper, newspaper, magazines
                • Cardboard (flatten boxes)
                • Paper packaging
                Keep it dry and clean. No greasy paper!
                Remember: Always check local guidelines as rules can vary by area.
                Paper recycling saves trees! 📄""",
                
                'default': """Hi there! Thanks for your recycling question!
                Recycling rules can vary by location, so for the most accurate information:
                1. Check your local municipality's website
                2. Use their recycling guide or app
                3. When in doubt, look it up online!
                General rule: When unsure, it's better to throw it out than contaminate recycling.
                Keep asking questions and learning about recycling! 🌎"""
            }
            
            answer = fallback_responses['default']
            question_lower = question.lower()
            
            for keyword, response in fallback_responses.items():
                if keyword != 'default' and keyword in question_lower:
                    answer = response
                    break
            
            current_user.token_balance += 2
            db.session.commit()
            
            return jsonify({
                'success': True,
                'answer': answer,
                'note': 'fallback_response',
                'tokens_awarded': 2
            })
        
    except Exception as e:
        print(f"AI question error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/recycling/complete-tutorial', methods=['POST'])
@login_required
def complete_recycling_tutorial():
    try:
        current_user.token_balance += 30
        current_user.eco_score += 15
        
        action = EcoAction(
            user_id=current_user.id,
            action_type='recycling_tutorial',
            co2_saved=2.0,
            tokens_earned=30,
            created_at=datetime.utcnow()
        )
        
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tokens_awarded': 30,
            'eco_score_added': 15,
            'new_balance': current_user.token_balance
        })
        
    except Exception as e:
        print(f"Complete tutorial error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/recycling/complete-quiz', methods=['POST'])
@login_required
def complete_recycling_quiz():
    try:
        data = request.json
        score = data.get('score', 0)
        
        tokens = 0
        eco_score = 0
        
        if score >= 100:
            tokens = 100
            eco_score = 50
        elif score >= 80:
            tokens = 75
            eco_score = 40
        elif score >= 60:
            tokens = 50
            eco_score = 25
        else:
            tokens = 25
            eco_score = 15
        
        current_user.token_balance += tokens
        current_user.eco_score += eco_score
        
        action = EcoAction(
            user_id=current_user.id,
            action_type='recycling_quiz',
            co2_saved=3.0,
            tokens_earned=tokens,
            created_at=datetime.utcnow()
        )
        
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tokens_awarded': tokens,
            'eco_score_added': eco_score,
            'new_balance': current_user.token_balance,
            'new_eco_score': current_user.eco_score
        })
        
    except Exception as e:
        print(f"Complete quiz error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/recycling/complete-categorization', methods=['POST'])
@login_required
def complete_recycling_categorization():
    try:
        data = request.json
        score = data.get('score', 0)
        
        tokens = 0
        eco_score = 0
        
        if score >= 100:
            tokens = 100
            eco_score = 50
        elif score >= 80:
            tokens = 75
            eco_score = 40
        elif score >= 60:
            tokens = 50
            eco_score = 25
        else:
            tokens = 25
            eco_score = 15
        
        current_user.token_balance += tokens
        current_user.eco_score += eco_score
        
        action = EcoAction(
            user_id=current_user.id,
            action_type='recycling_categorization',
            co2_saved=4.0,
            tokens_earned=tokens,
            created_at=datetime.utcnow()
        )
        
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tokens_awarded': tokens,
            'eco_score_added': eco_score,
            'new_balance': current_user.token_balance,
            'new_eco_score': current_user.eco_score
        })
        
    except Exception as e:
        print(f"Complete categorization error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/recycling/progress', methods=['GET'])
@login_required
def get_recycling_progress():
    try:
        actions = EcoAction.query.filter_by(
            user_id=current_user.id
        ).filter(
            EcoAction.action_type.in_(['recycling_tutorial', 'recycling_quiz', 'recycling_categorization', 'recycling_question'])
        ).all()
        
        total_tokens_earned = sum(action.tokens_earned for action in actions)
        total_co2_saved = sum(action.co2_saved for action in actions)
        
        tutorials_completed = EcoAction.query.filter_by(
            user_id=current_user.id,
            action_type='recycling_tutorial'
        ).count()
        
        quizzes_completed = EcoAction.query.filter_by(
            user_id=current_user.id,
            action_type='recycling_quiz'
        ).count()
        
        games_completed = EcoAction.query.filter_by(
            user_id=current_user.id,
            action_type='recycling_categorization'
        ).count()
        
        questions_asked = EcoAction.query.filter_by(
            user_id=current_user.id,
            action_type='recycling_question'
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_tokens_earned': total_tokens_earned,
                'total_co2_saved': round(total_co2_saved, 2),
                'tutorials_completed': tutorials_completed,
                'quizzes_completed': quizzes_completed,
                'games_completed': games_completed,
                'questions_asked': questions_asked
            },
            'user': {
                'token_balance': current_user.token_balance,
                'eco_score': current_user.eco_score,
                'level': current_user.level
            }
        })
        
    except Exception as e:
        print(f"Get progress error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/recycling/leaderboard', methods=['GET'])
@login_required
def recycling_leaderboard():
    try:
        users = User.query.order_by(User.eco_score.desc()).limit(10).all()
        
        leaderboard = []
        for i, user in enumerate(users):
            leaderboard.append({
                'rank': i + 1,
                'username': user.username,
                'eco_score': user.eco_score,
                'token_balance': user.token_balance,
                'is_current_user': user.id == current_user.id
            })
        
        all_users = User.query.order_by(User.eco_score.desc()).all()
        current_user_rank = next((i + 1 for i, user in enumerate(all_users) if user.id == current_user.id), None)
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard,
            'current_user_rank': current_user_rank,
            'total_players': len(all_users)
        })
        
    except Exception as e:
        print(f"Leaderboard error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/recycling/daily-tip', methods=['GET'])
@login_required
def get_daily_recycling_tip():
    try:
        recycling_tips = [
            "Rinse containers before recycling to prevent contamination.",
            "Flatten cardboard boxes to save space in recycling bins.",
            "Keep plastic bottle caps ON - they're recyclable too!",
            "Check local guidelines - recycling rules vary by location.",
            "When in doubt, throw it out to avoid contaminating recycling.",
            "Plastic bags should go to store drop-offs, not home recycling.",
            "Remove food residue from containers before recycling.",
            "Separate different materials for better recycling efficiency.",
            "Recycle paper, but keep it dry and clean.",
            "Aluminum cans are highly recyclable - rinse and recycle!",
            "Glass bottles and jars are recyclable - rinse them first.",
            "Don't put broken glass in recycling - it goes in the trash.",
            "Electronics should go to e-waste facilities, not regular bins.",
            "Batteries need special disposal - never in regular trash.",
            "Pizza boxes with grease should go in compost or trash.",
            "Recycling one aluminum can saves enough energy to power a TV for 3 hours!",
            "Plastic #1 (PET) and #2 (HDPE) are widely accepted for recycling.",
            "Shredded paper may need to be bagged separately for recycling.",
            "Styrofoam is usually not recyclable in regular bins.",
            "Reduce and reuse come before recycle in the waste hierarchy."
        ]
        
        day_of_year = datetime.utcnow().timetuple().tm_yday
        tip_index = day_of_year % len(recycling_tips)
        
        return jsonify({
            'success': True,
            'tip': recycling_tips[tip_index],
            'tip_number': tip_index + 1,
            'total_tips': len(recycling_tips)
        })
        
    except Exception as e:
        print(f"Daily tip error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/dashboard-data')
@login_required
def get_greentoken_dashboard_data():
    try:
        if CryptoMarket.query.count() == 0:
            init_greentoken_market()
        
        investments = CryptoInvestment.query.filter_by(
            user_id=current_user.id, 
            status='active'
        ).all()
        
        for investment in investments:
            crypto = CryptoMarket.query.filter_by(symbol=investment.crypto_symbol).first()
            if crypto:
                variation = random.uniform(-0.05, 0.1)
                investment.current_price = crypto.current_price * (1 + variation)
                investment.profit_loss = (investment.current_price * investment.crypto_amount) - investment.amount_invested
                investment.hourly_change = variation * 100
        
        db.session.commit()
        
        total_invested = sum(inv.amount_invested for inv in investments)
        total_current_value = sum(inv.crypto_amount * inv.current_price for inv in investments)
        total_profit_loss = total_current_value - total_invested
        
        market_data = CryptoMarket.query.all()
        
        flight_credits = FlightCredit.query.filter_by(
            user_id=current_user.id
        ).filter(
            FlightCredit.remaining_flights > 0
        ).all()
        
        transactions = GreenTokenTransaction.query.filter_by(
            user_id=current_user.id
        ).order_by(GreenTokenTransaction.created_at.desc()).limit(10).all()
        
        return jsonify({
            'success': True,
            'balance': current_user.token_balance,
            'total_invested': total_invested,
            'total_current_value': total_current_value,
            'total_profit_loss': total_profit_loss,
            'investments': [{
                'id': inv.id,
                'symbol': inv.crypto_symbol,
                'name': inv.crypto_name,
                'amount_invested': inv.amount_invested,
                'crypto_amount': inv.crypto_amount,
                'purchase_price': inv.purchase_price,
                'current_price': inv.current_price,
                'profit_loss': inv.profit_loss,
                'hourly_change': inv.hourly_change,
                'current_value': inv.crypto_amount * inv.current_price,
                'maturity_date': inv.maturity_date.strftime('%Y-%m-%d %H:%M:%S') if inv.maturity_date else None,
                'investment_date': inv.investment_date.strftime('%Y-%m-%d %H:%M:%S')
            } for inv in investments],
            'market_data': [{
                'symbol': m.symbol,
                'name': m.name,
                'current_price': m.current_price,
                'hourly_change': m.hourly_change,
                'daily_change': m.daily_change,
                'market_cap': m.market_cap,
                'volume': m.volume,
                'description': m.description,
                'volatility': m.volatility
            } for m in market_data],
            'flight_credits': [{
                'id': fc.id,
                'tokens_spent': fc.tokens_spent,
                'flights_earned': fc.flights_earned,
                'remaining_flights': fc.remaining_flights,
                'conversion_rate': fc.conversion_rate,
                'valid_until': fc.valid_until.strftime('%Y-%m-%d') if fc.valid_until else None,
                'created_at': fc.created_at.strftime('%Y-%m-%d')
            } for fc in flight_credits],
            'recent_transactions': [{
                'type': t.transaction_type,
                'amount': t.amount,
                'crypto_symbol': t.crypto_symbol,
                'description': t.description,
                'created_at': t.created_at.strftime('%Y-%m-%d %H:%M')
            } for t in transactions],
            'available_flights': sum(fc.remaining_flights for fc in flight_credits),
            'portfolio_metrics': {
                'total_value': total_current_value,
                'daily_return': random.uniform(-2, 5) if investments else 0,
                'annual_return': random.uniform(5, 40) if investments else 0,
                'sharpe_ratio': random.uniform(0.5, 2.5) if investments else 0,
                'volatility': random.uniform(5, 25) if investments else 0,
                'max_drawdown': random.uniform(5, 20) if investments else 0,
                'win_rate': random.uniform(50, 90) if investments else 0,
                'risk_level': 'LOW' if total_current_value < 1000 else 'MEDIUM' if total_current_value < 5000 else 'HIGH'
            }
        })
        
    except Exception as e:
        print(f"Dashboard data error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/process-matured', methods=['POST'])
@login_required
def process_matured_investments():
    try:
        now = datetime.utcnow()
        matured_investments = CryptoInvestment.query.filter_by(
            user_id=current_user.id,
            status='active'
        ).filter(
            CryptoInvestment.maturity_date <= now
        ).all()
        
        if not matured_investments:
            return jsonify({
                'success': True,
                'message': 'No investments have matured yet',
                'matured_count': 0
            })
        
        total_returned = 0
        processed_count = 0
        
        for investment in matured_investments:
            fluctuation = random.uniform(-0.2, 0.3)
            final_price = investment.purchase_price * (1 + fluctuation)
            
            final_value = investment.crypto_amount * final_price
            
            investment.current_price = final_price
            investment.profit_loss = final_value - investment.amount_invested
            investment.status = 'matured'
            investment.hourly_change = fluctuation * 100
            
            current_user.token_balance += final_value
            total_returned += final_value
            processed_count += 1
            
            transaction = GreenTokenTransaction(
                user_id=current_user.id,
                transaction_type='investment_return',
                amount=final_value,
                crypto_symbol=investment.crypto_symbol,
                crypto_amount=investment.crypto_amount,
                exchange_rate=final_price,
                description=f'Investment matured: {investment.crypto_name} ({fluctuation*100:.1f}% change)',
                status='completed'
            )
            db.session.add(transaction)
        
        action = EcoAction(
            user_id=current_user.id,
            action_type='investment_matured',
            co2_saved=0,
            tokens_earned=total_returned,
            created_at=datetime.utcnow()
        )
        db.session.add(action)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'matured_count': processed_count,
            'total_returned': total_returned,
            'new_balance': current_user.token_balance,
            'message': f'{processed_count} investment(s) matured and returned to your balance'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Process matured error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/recycling/eco-facts', methods=['GET'])
@login_required
def get_eco_facts():
    try:
        eco_facts = [
            "Recycling one aluminum can saves enough energy to power a TV for 3 hours.",
            "A single glass bottle can take up to 1 million years to decompose in a landfill.",
            "Americans throw away 25 billion Styrofoam coffee cups every year.",
            "Recycling paper saves trees - each ton saves about 17 trees.",
            "Plastic bags can take up to 1,000 years to decompose.",
            "The energy saved by recycling one glass bottle can power a computer for 25 minutes.",
            "Over 75% of waste is recyclable, but we only recycle about 30% of it.",
            "Recycling one ton of plastic saves the equivalent of 1,000-2,000 gallons of gasoline.",
            "Aluminum can be recycled indefinitely without loss of quality.",
            "Making paper from recycled materials uses 70% less energy than making it from raw materials.",
            "The average person generates over 4 pounds of trash every day.",
            "Recycling and composting prevented 85 million tons of waste from going to landfills in 2020.",
            "It takes 500 years for an average sized plastic water bottle to fully decompose.",
            "Glass is 100% recyclable and can be recycled endlessly without loss in purity or quality.",
            "Recycling one ton of cardboard saves 46 gallons of oil."
        ]
        
        import random
        selected_facts = random.sample(eco_facts, min(3, len(eco_facts)))
        
        return jsonify({
            'success': True,
            'facts': selected_facts
        })
        
    except Exception as e:
        print(f"Eco facts error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/shortcuts')
@login_required
def system_shortcuts():
    return render_template('shortcuts.html', user=current_user)

@app.route('/api/climate/actions')
@login_required
def get_climate_actions():
    try:
        category = request.args.get('category', 'all')
        difficulty = request.args.get('difficulty', 'all')
        
        actions = get_climate_solutions_by_category(category, difficulty)
        
        return jsonify({
            'success': True,
            'actions': actions,
            'total_actions': len(actions),
            'total_impact_possible': sum(action.get('impact_kg', 0) for action in actions),
            'sources': ['Project Drawdown', 'IPCC Mitigation Pathways', 'UN Sustainable Development Goals']
        })
        
    except Exception as e:
        print(f"Error getting actions: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/climate/snapshot', methods=['POST'])
@login_required
def create_climate_snapshot():
    try:
        data = request.json
        
        snapshot_id = hashlib.md5(f"{current_user.id}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]
        
        image_data = generate_snapshot_image(
            data.get('scenario', 'moderate'),
            data.get('year', 2050),
            data.get('projections', {}),
            current_user.username
        )
        
        snapshot = ClimateSnapshot(
            user_id=current_user.id,
            snapshot_id=snapshot_id,
            title=data.get('title', f'Climate Snapshot {datetime.utcnow().strftime("%Y-%m-%d")}'),
            scenario=data.get('scenario', 'moderate'),
            year=data.get('year', 2050),
            data=json.dumps(data.get('data', {})),
            image_data=image_data
        )
        
        db.session.add(snapshot)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'snapshot': {
                'id': snapshot_id,
                'title': snapshot.title,
                'image_url': f'/api/climate/snapshot/{snapshot_id}/image',
                'share_url': f'/climate/snapshot/{snapshot_id}',
                'created_at': snapshot.created_at.isoformat()
            }
        })
        
    except Exception as e:
        print(f"Error creating snapshot: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/climate/snapshot/<snapshot_id>/image')
def get_snapshot_image(snapshot_id):
    try:
        snapshot = ClimateSnapshot.query.filter_by(snapshot_id=snapshot_id).first()
        if snapshot and snapshot.image_data:
            return jsonify({'success': True, 'image': snapshot.image_data})
        return jsonify({'success': False, 'error': 'Snapshot not found'})
    except Exception as e:
        print(f"Error getting snapshot image: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/climate/snapshot/<snapshot_id>')
def view_climate_snapshot(snapshot_id):
    snapshot = ClimateSnapshot.query.filter_by(snapshot_id=snapshot_id).first()
    if not snapshot:
        return "Snapshot not found", 404
    
    snapshot.share_count += 1
    db.session.commit()
    
    return render_template('climate_snapshot_view.html',
                         snapshot=snapshot,
                         data=json.loads(snapshot.data) if snapshot.data else {},
                         user=snapshot.user)

@app.route('/api/climate/compare')
@login_required
def compare_climate_data():
    try:
        scenario1 = request.args.get('scenario1', 'moderate')
        scenario2 = request.args.get('scenario2', 'bau')
        year = request.args.get('year', 2050, type=int)
        
        projections1 = get_future_projections(year, scenario1)
        projections2 = get_future_projections(year, scenario2)
        
        comparison = {
            'year': year,
            'comparison': {
                'scenario1': {'name': scenario1, 'data': projections1},
                'scenario2': {'name': scenario2, 'data': projections2}
            },
            'differences': calculate_differences(projections1, projections2),
            'impacts_comparison': compare_impacts(projections1, projections2),
            'key_insights': generate_comparison_insights(scenario1, scenario2, year),
            'visualization_data': prepare_comparison_visualization(projections1, projections2)
        }
        
        return jsonify({'success': True, 'comparison': comparison})
        
    except Exception as e:
        print(f"Error comparing data: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/climate/quiz')
@login_required
def get_climate_quiz():
    try:
        difficulty = request.args.get('difficulty', 'medium')
        category = request.args.get('category', 'all')
        
        quiz = generate_climate_quiz(difficulty, category)
        
        return jsonify({
            'success': True,
            'quiz': quiz,
            'metadata': {
                'difficulty': difficulty,
                'category': category,
                'questions': len(quiz),
                'estimated_time': len(quiz) * 30
            }
        })
        
    except Exception as e:
        print(f"Error getting quiz: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/climate/story/<year>')
@login_required
def get_climate_story(year):
    try:
        year = int(year)
        scenario = request.args.get('scenario', 'moderate')
        
        projections = get_future_projections(year, scenario)
        story = generate_climate_story(year, scenario, projections)
        
        return jsonify({
            'success': True,
            'story': story,
            'metadata': {
                'year': year,
                'scenario': scenario,
                'generated_at': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        print(f"Error getting story: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/climate/disaster/<disaster_id>')
@login_required
def get_disaster_details(disaster_id):
    try:
        disasters = {
            'heatwave_2022': {
                'title': '2022 European Heatwave',
                'year': 2022,
                'region': 'Europe',
                'description': 'Record-breaking heatwave across Europe with temperatures exceeding 40°C in many regions.',
                'impacts': {
                    'human': 'Over 20,000 excess deaths',
                    'economic': '€10B+ in damages and losses',
                    'environmental': '500,000+ hectares burned in wildfires',
                    'agricultural': 'Major crop failures and livestock losses'
                },
                'climate_connection': 'Made 10x more likely by climate change (World Weather Attribution)',
                'data_sources': ['Copernicus Climate Change Service', 'World Weather Attribution'],
                'images': [
                    'https://climate.nasa.gov/internal_resources/2501',
                    'https://climate.nasa.gov/internal_resources/2502'
                ]
            },
            'hurricane_katrina': {
                'title': 'Hurricane Katrina (2005)',
                'year': 2005,
                'region': 'Gulf Coast, USA',
                'description': 'Category 5 hurricane that caused catastrophic damage, particularly in New Orleans.',
                'impacts': {
                    'human': '1,800+ deaths, 350,000+ displaced',
                    'economic': '$125 billion in damages',
                    'environmental': 'Massive oil spills and wetland destruction',
                    'social': 'Long-term displacement and community disruption'
                },
                'climate_connection': 'Warmer sea surface temperatures increased rainfall by 15-20%',
                'data_sources': ['NOAA National Hurricane Center', 'NASA Earth Observatory'],
                'images': [
                    'https://climate.nasa.gov/internal_resources/2503',
                    'https://climate.nasa.gov/internal_resources/2504'
                ]
            },
            'australia_wildfires': {
                'title': '2019-2020 Australian Bushfires',
                'year': 2020,
                'region': 'Australia',
                'description': 'Unprecedented wildfire season fueled by record heat and drought conditions.',
                'impacts': {
                    'human': '34 direct deaths, thousands displaced',
                    'economic': '$5 billion in damages',
                    'environmental': '3 billion animals affected, 46 million acres burned',
                    'health': 'Smoke affecting millions, respiratory issues spiked'
                },
                'climate_connection': 'Made 30% more likely by climate change-induced heat and drought',
                'data_sources': ['CSIRO', 'Australian Bureau of Meteorology', 'NASA FIRMS'],
                'images': [
                    'https://climate.nasa.gov/internal_resources/2505',
                    'https://climate.nasa.gov/internal_resources/2506'
                ]
            }
        }
        
        if disaster_id in disasters:
            return jsonify({'success': True, 'disaster': disasters[disaster_id]})
        
        return jsonify({'success': False, 'error': 'Disaster not found'})
        
    except Exception as e:
        print(f"Error getting disaster details: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/avatar')
@login_required
def avatar():
    return redirect(url_for('avatar_nexus'))

@app.route('/avatar/nexus')
@login_required
def avatar_nexus():
    tutorial_seen = request.cookies.get('nexus_tutorial_seen')
    return render_template('avatar_nexus_combined.html', 
                         user=current_user, 
                         tutorial_seen=tutorial_seen)

@app.route('/avatar/mark_tutorial_seen')
@login_required
def mark_tutorial_seen():
    response = make_response(jsonify({'success': True}))
    response.set_cookie('nexus_tutorial_seen', 'true', max_age=31536000)
    return response

@app.route('/api/update-tokens', methods=['POST'])
@login_required
def update_tokens():
    data = request.json
    current_user.token_balance += data.get('tokens', 0)
    db.session.commit()
    return jsonify({'success': True, 'tokens': current_user.token_balance})

@app.route('/certifications')
@login_required
def certifications():
    return render_template('certifications.html', user=current_user)

def get_certification_requirements_with_quiz():
    return [
        {
            'level': 'bronze',
            'title': 'BRONZE ECODIST',
            'points_required': 1000,
            'requirements': [
                'Basic knowledge quiz passed (70%+)',
                '7-day streak of eco-actions',
                '500 tokens earned'
            ],
            'quiz_questions': 10,
            'passing_score': 70
        },
        {
            'level': 'silver',
            'title': 'SILVER ECOGUARDIAN',
            'points_required': 5000,
            'requirements': [
                'Advanced quiz: 80%+',
                'Mentored 3 new users',
                'Completed 3 community projects'
            ],
            'quiz_questions': 15,
            'passing_score': 80
        },
        {
            'level': 'gold',
            'title': 'GOLD ECOMAGE',
            'points_required': 15000,
            'requirements': [
                'Mastery exam passed (85%+)',
                'Led successful group challenge',
                '10,000+ tokens earned'
            ],
            'quiz_questions': 20,
            'passing_score': 85
        },
        {
            'level': 'platinum',
            'title': 'PLATINUM ECOLEGEND',
            'points_required': 50000,
            'requirements': [
                'All quizzes 95%+',
                'Created viral educational content',
                '50,000+ tokens, top 1% globally'
            ],
            'quiz_questions': 25,
            'passing_score': 95
        }
    ]

@app.route('/certificate/<certificate_id>')
@login_required
def view_certificate_route(certificate_id):
    cert = Certification.query.filter_by(
        certificate_id=certificate_id,
        user_id=current_user.id
    ).first_or_404()
    
    verification_url = f"https://ecoverse.com/verify/{certificate_id}"
    qr_code_data = generate_qr_code(verification_url)
    
    return render_template('certificate_view.html', 
                         user=current_user, 
                         cert=cert,
                         qr_code_data=qr_code_data,
                         is_ultra=cert.level == 'ultra')

@app.route('/certification/<certificate_id>')
@login_required
def view_certification(certificate_id):
    cert = Certification.query.filter_by(certificate_id=certificate_id, user_id=current_user.id).first_or_404()
    
    verification_url = f"http://localhost:5000/verify/{certificate_id}"
    qr_code_data = generate_qr_code(verification_url)
    
    return render_template('certificate_view.html', 
                         user=current_user, 
                         cert=cert,
                         qr_code_data=qr_code_data)

@app.route('/verify/<certificate_id>')
def verify_certificate(certificate_id):
    cert = Certification.query.filter_by(certificate_id=certificate_id).first()
    
    if not cert:
        return render_template('verify_certificate.html', 
                             valid=False,
                             message="Certificate not found")
    
    user = User.query.get(cert.user_id)
    
    is_valid = True
    if cert.valid_until and cert.valid_until < datetime.utcnow():
        is_valid = False
    
    cert_type = "Ultra Legend (Quiz Master)" if cert.level == 'ultra' else "Points Achievement"
    
    return render_template('verify_certificate.html',
                         valid=is_valid,
                         cert=cert,
                         user=user if user else None,
                         cert_type=cert_type,
                         current_date=datetime.utcnow())

@app.route('/greentoken-dashboard')
@login_required
def greentoken_dashboard():
    return render_template('greentoken_dashboard.html', user=current_user)

@app.route('/api/greentoken/balance')
@login_required
def get_greentoken_balance():
    try:
        investments = CryptoInvestment.query.filter_by(user_id=current_user.id, status='active').all()
        
        total_invested = sum(inv.amount_invested for inv in investments)
        current_value = sum(inv.crypto_amount * inv.current_price for inv in investments)
        total_profit_loss = current_value - total_invested
        
        flight_credits = FlightCredit.query.filter_by(
            user_id=current_user.id
        ).filter(
            FlightCredit.remaining_flights > 0,
            or_(
                FlightCredit.valid_until.is_(None),
                FlightCredit.valid_until > datetime.utcnow()
            )
        ).all()
        
        total_available_flights = sum(fc.remaining_flights for fc in flight_credits)
        
        recent_transactions = GreenTokenTransaction.query.filter_by(
            user_id=current_user.id
        ).order_by(GreenTokenTransaction.created_at.desc()).limit(10).all()
        
        crypto_markets = CryptoMarket.query.all()
        random_cryptos = generate_random_cryptos(5)
        
        return jsonify({
            'success': True,
            'balance': current_user.token_balance,
            'total_invested': total_invested,
            'current_investment_value': current_value,
            'total_profit_loss': total_profit_loss,
            'available_flights': total_available_flights,
            'investments': [{
                'id': inv.id,
                'symbol': inv.crypto_symbol,
                'name': inv.crypto_name,
                'amount_invested': inv.amount_invested,
                'crypto_amount': inv.crypto_amount,
                'purchase_price': inv.purchase_price,
                'current_price': inv.current_price,
                'profit_loss': inv.profit_loss,
                'hourly_change': inv.hourly_change,
                'investment_date': inv.investment_date.strftime('%Y-%m-%d %H:%M'),
                'maturity_date': inv.maturity_date.strftime('%Y-%m-%d %H:%M') if inv.maturity_date else None
            } for inv in investments],
            'flight_credits': [{
                'id': fc.id,
                'tokens_spent': fc.tokens_spent,
                'flights_earned': fc.flights_earned,
                'remaining_flights': fc.remaining_flights,
                'conversion_rate': fc.conversion_rate,
                'valid_until': fc.valid_until.strftime('%Y-%m-%d') if fc.valid_until else None,
                'created_at': fc.created_at.strftime('%Y-%m-%d')
            } for fc in flight_credits],
            'recent_transactions': [{
                'id': t.id,
                'type': t.transaction_type,
                'amount': t.amount,
                'crypto_symbol': t.crypto_symbol,
                'crypto_amount': t.crypto_amount,
                'description': t.description,
                'status': t.status,
                'created_at': t.created_at.strftime('%Y-%m-%d %H:%M')
            } for t in recent_transactions],
            'market_data': [{
                'symbol': m.symbol,
                'name': m.name,
                'current_price': m.current_price,
                'hourly_change': m.hourly_change,
                'daily_change': m.daily_change,
                'market_cap': m.market_cap,
                'volume': m.volume,
                'description': m.description
            } for m in crypto_markets],
            'random_cryptos': random_cryptos
        })
        
    except Exception as e:
        print(f"Error getting GreenToken balance: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/invest', methods=['POST'])
@login_required
def invest_greentokens():
    try:
        data = request.json
        crypto_symbol = data.get('crypto_symbol')
        crypto_name = data.get('crypto_name')
        amount = float(data.get('amount', 0))
        
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid investment amount'})
        
        if current_user.token_balance < amount:
            return jsonify({'success': False, 'message': 'Insufficient GreenTokens'})
        
        crypto_market = CryptoMarket.query.filter_by(symbol=crypto_symbol).first()
        if not crypto_market:
            crypto_market = create_random_crypto(crypto_symbol, crypto_name)
        
        transaction_fee = amount * 0.01
        net_amount = amount - transaction_fee
        crypto_amount = net_amount / crypto_market.current_price
        
        maturity_date = datetime.utcnow() + timedelta(hours=1)
        
        investment = CryptoInvestment(
            user_id=current_user.id,
            crypto_symbol=crypto_symbol,
            crypto_name=crypto_name or crypto_market.name,
            amount_invested=amount,
            crypto_amount=crypto_amount,
            purchase_price=crypto_market.current_price,
            current_price=crypto_market.current_price,
            maturity_date=maturity_date,
            hourly_change=crypto_market.hourly_change
        )
        
        current_user.token_balance -= amount
        
        transaction = GreenTokenTransaction(
            user_id=current_user.id,
            transaction_type='investment',
            amount=-amount,
            crypto_symbol=crypto_symbol,
            crypto_amount=crypto_amount,
            exchange_rate=crypto_market.current_price,
            description=f'Invested in {crypto_name or crypto_symbol}',
            status='completed'
        )
        
        db.session.add(investment)
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'investment': {
                'id': investment.id,
                'symbol': crypto_symbol,
                'amount_invested': amount,
                'crypto_amount': crypto_amount,
                'purchase_price': crypto_market.current_price,
                'maturity_date': investment.maturity_date.strftime('%Y-%m-%d %H:%M:%S')
            },
            'new_balance': current_user.token_balance,
            'message': f'Successfully invested {amount} GreenTokens in {crypto_name or crypto_symbol}. Investment matures in 1 hour.'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error investing GreenTokens: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/convert-to-flights', methods=['POST'])
@login_required
def convert_to_flights():
    try:
        data = request.json
        tokens_amount = float(data.get('tokens', 0))
        
        if tokens_amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid amount'})
        
        if current_user.token_balance < tokens_amount:
            return jsonify({'success': False, 'message': 'Insufficient GreenTokens'})
        
        base_rate = 100
        if tokens_amount >= 1000:
            conversion_rate = base_rate * 0.9
        elif tokens_amount >= 500:
            conversion_rate = base_rate * 0.95
        else:
            conversion_rate = base_rate
        
        flights_earned = int(tokens_amount // conversion_rate)
        
        if flights_earned == 0:
            return jsonify({'success': False, 'message': 'Minimum 100 tokens required for 1 flight'})
        
        flight_credit = FlightCredit(
            user_id=current_user.id,
            tokens_spent=tokens_amount,
            flights_earned=flights_earned,
            conversion_rate=conversion_rate,
            valid_until=datetime.utcnow() + timedelta(days=30),
            remaining_flights=flights_earned
        )
        
        current_user.token_balance -= tokens_amount
        
        transaction = GreenTokenTransaction(
            user_id=current_user.id,
            transaction_type='conversion',
            amount=tokens_amount,
            description=f'Converted to {flights_earned} flight(s)',
            status='completed'
        )
        
        db.session.add(flight_credit)
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'flights_earned': flights_earned,
            'tokens_spent': tokens_amount,
            'conversion_rate': conversion_rate,
            'new_balance': current_user.token_balance,
            'valid_until': flight_credit.valid_until.strftime('%Y-%m-%d'),
            'message': f'Successfully converted {tokens_amount} GreenTokens to {flights_earned} flight(s)'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error converting to flights: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/check-investments')
@login_required
def check_investments():
    try:
        investments = CryptoInvestment.query.filter_by(
            user_id=current_user.id,
            status='active'
        ).all()
        
        updated_investments = []
        
        for investment in investments:
            if investment.maturity_date and investment.maturity_date <= datetime.utcnow():
                fluctuation = random.uniform(-0.2, 0.3)
                new_price = investment.current_price * (1 + fluctuation)
                
                investment.current_price = new_price
                investment.profit_loss = (new_price - investment.purchase_price) * investment.crypto_amount
                investment.status = 'matured'
                investment.hourly_change = fluctuation * 100
                
                return_amount = investment.crypto_amount * new_price
                current_user.token_balance += return_amount
                
                transaction = GreenTokenTransaction(
                    user_id=current_user.id,
                    transaction_type='investment_return',
                    amount=return_amount,
                    crypto_symbol=investment.crypto_symbol,
                    crypto_amount=investment.crypto_amount,
                    exchange_rate=new_price,
                    description=f'Investment matured: {investment.crypto_name}',
                    status='completed'
                )
                
                db.session.add(transaction)
                updated_investments.append({
                    'id': investment.id,
                    'symbol': investment.crypto_symbol,
                    'profit_loss': investment.profit_loss,
                    'return_amount': return_amount,
                    'new_balance': current_user.token_balance,
                    'status': 'matured'
                })
        
        if updated_investments:
            db.session.commit()
            return jsonify({
                'success': True,
                'updated_investments': updated_investments,
                'message': f'{len(updated_investments)} investment(s) matured'
            })
        
        return jsonify({
            'success': True,
            'message': 'No investments matured yet'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error checking investments: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/sell-investment/<int:investment_id>', methods=['POST'])
@login_required
def sell_investment(investment_id):
    try:
        investment = CryptoInvestment.query.get_or_404(investment_id)
        
        if investment.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'})
        
        if investment.status != 'active':
            return jsonify({'success': False, 'message': 'Investment not active'})
        
        penalty = investment.crypto_amount * investment.current_price * 0.05
        return_amount = (investment.crypto_amount * investment.current_price) - penalty
        
        investment.status = 'sold'
        investment.profit_loss = return_amount - investment.amount_invested
        
        current_user.token_balance += return_amount
        
        transaction = GreenTokenTransaction(
            user_id=current_user.id,
            transaction_type='investment_sale',
            amount=return_amount,
            crypto_symbol=investment.crypto_symbol,
            crypto_amount=investment.crypto_amount,
            exchange_rate=investment.current_price,
            description=f'Sold investment: {investment.crypto_name} (early withdrawal)',
            status='completed'
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'return_amount': return_amount,
            'penalty': penalty,
            'new_balance': current_user.token_balance,
            'message': f'Sold {investment.crypto_name} investment'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error selling investment: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/use-flight-credit/<int:flight_id>', methods=['POST'])
@login_required
def use_flight_credit(flight_id):
    try:
        flight_credit = FlightCredit.query.get_or_404(flight_id)
        
        if flight_credit.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'})
        
        if flight_credit.remaining_flights <= 0:
            return jsonify({'success': False, 'message': 'No flights remaining'})
        
        if flight_credit.valid_until and flight_credit.valid_until < datetime.utcnow():
            return jsonify({'success': False, 'message': 'Flight credit expired'})
        
        flight_credit.remaining_flights -= 1
        
        transaction = GreenTokenTransaction(
            user_id=current_user.id,
            transaction_type='flight_usage',
            amount=0,
            description='Used flight credit',
            status='completed'
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'remaining_flights': flight_credit.remaining_flights,
            'message': 'Flight credit used successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error using flight credit: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/market-data')
@login_required
def get_market_data():
    try:
        cryptos = CryptoMarket.query.all()
        updated_cryptos = []
        
        for crypto in cryptos:
            hourly_change = random.uniform(-5, 10)
            crypto.hourly_change = hourly_change
            
            crypto.current_price = crypto.current_price * (1 + hourly_change / 100)
            
            crypto.volume = crypto.volume * random.uniform(0.8, 1.2)
            crypto.market_cap = crypto.current_price * random.uniform(1000000, 10000000)
            
            updated_cryptos.append({
                'symbol': crypto.symbol,
                'name': crypto.name,
                'current_price': crypto.current_price,
                'hourly_change': hourly_change,
                'daily_change': crypto.daily_change,
                'market_cap': crypto.market_cap,
                'volume': crypto.volume,
                'description': crypto.description
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'market_data': updated_cryptos,
            'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        print(f"Error getting market data: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/realistic-market-data')
@login_required
def get_realistic_market_data():
    try:
        cryptos = CryptoMarket.query.all()
        market_data = []
        
        for crypto in cryptos:
            market_data.append({
                'symbol': crypto.symbol,
                'name': crypto.name,
                'current_price': crypto.current_price,
                'hourly_change': crypto.hourly_change,
                'description': crypto.description
            })
        
        return jsonify({
            'success': True,
            'market_data': market_data
        })
        
    except Exception as e:
        print(f"Error getting realistic market data: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/price-history/<crypto_symbol>')
@login_required
def get_price_history(crypto_symbol):
    try:
        crypto = CryptoMarket.query.filter_by(symbol=crypto_symbol).first()
        if not crypto:
            return jsonify({'success': False, 'message': 'Crypto not found'})
        
        price_history = []
        base_price = crypto.current_price
        volatility = crypto.volatility
        
        for hour in range(24, -1, -1):
            if hour == 24:
                price = base_price
            else:
                change = random.uniform(-volatility, volatility)
                price = price_history[-1]['price'] * (1 + change)
            
            price_history.append({
                'time': (datetime.utcnow() - timedelta(hours=hour)).strftime('%H:%M'),
                'price': price,
                'volume': random.uniform(100000, 1000000)
            })
        
        return jsonify({
            'success': True,
            'symbol': crypto_symbol,
            'name': crypto.name,
            'price_history': price_history,
            'current_price': crypto.current_price,
            'hourly_change': crypto.hourly_change
        })
        
    except Exception as e:
        print(f"Error getting price history: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/create-crypto', methods=['POST'])
@login_required
def create_crypto():
    try:
        data = request.json
        symbol = data.get('symbol', '').upper()
        name = data.get('name', '')
        
        if not symbol or not name:
            return jsonify({'success': False, 'message': 'Symbol and name required'})
        
        existing = CryptoMarket.query.filter_by(symbol=symbol).first()
        if existing:
            return jsonify({'success': False, 'message': 'Crypto already exists'})
        
        new_crypto = create_random_crypto(symbol, name)
        
        return jsonify({
            'success': True,
            'crypto': {
                'symbol': new_crypto.symbol,
                'name': new_crypto.name,
                'current_price': new_crypto.current_price,
                'description': new_crypto.description,
                'volatility': new_crypto.volatility
            },
            'message': f'Created new crypto: {name} ({symbol})'
        })
        
    except Exception as e:
        print(f"Error creating crypto: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/certification/check')
@login_required
def check_certification():
    try:
        total_actions = CarbonAction.query.filter_by(user_id=current_user.id).count()
        eco_actions = EcoAction.query.filter_by(user_id=current_user.id).count()
        flights_completed = AviationQuest.query.filter_by(user_id=current_user.id, status='completed').count()
        
        base_points = current_user.eco_score
        action_points = total_actions * 10
        eco_action_points = eco_actions * 15
        flight_points = flights_completed * 200
        total_points = base_points + action_points + eco_action_points + flight_points
        
        certifications_data = [
            {
                'type': 'carbon_warrior',
                'title': 'Carbon Warrior',
                'level': 'bronze',
                'points_required': 1000,
                'description': 'Master of carbon footprint reduction',
                'badge': '🌱'
            },
            {
                'type': 'sustainability_expert',
                'title': 'Sustainability Expert',
                'level': 'silver',
                'points_required': 5000,
                'description': 'Expert in sustainable living practices',
                'badge': '♻️'
            },
            {
                'type': 'eco_innovator',
                'title': 'Eco Innovator',
                'level': 'gold',
                'points_required': 15000,
                'description': 'Innovator in environmental solutions',
                'badge': '💡'
            }
        ]
        
        new_certifications = []
        
        for cert_data in certifications_data:
            if total_points >= cert_data['points_required']:
                existing = Certification.query.filter_by(
                    user_id=current_user.id,
                    certification_type=cert_data['type'],
                    level=cert_data['level']
                ).first()
                
                if not existing:
                    ai_message = generate_certification_message(
                        current_user.username,
                        cert_data['title'],
                        cert_data['level'],
                        total_points
                    )
                    
                    cert_id = f"ECV-{current_user.id:06d}-{cert_data['type'].upper()}-{datetime.utcnow().strftime('%Y%m%d')}"
                    
                    qr_data = f"https://ecoverse.com/verify/{cert_id}"
                    
                    new_cert = Certification(
                        user_id=current_user.id,
                        certification_type=cert_data['type'],
                        title=cert_data['title'],
                        level=cert_data['level'],
                        points_required=cert_data['points_required'],
                        user_points=total_points,
                        description=cert_data['description'],
                        ai_generated_text=ai_message,
                        certificate_id=cert_id,
                        qr_data=qr_data,
                        valid_until=datetime.utcnow() + timedelta(days=365)
                    )
                    
                    db.session.add(new_cert)
                    new_certifications.append({
                        'title': cert_data['title'],
                        'level': cert_data['level'],
                        'badge': cert_data['badge']
                    })
                    
                    token_bonus = {
                        'bronze': 500,
                        'silver': 1500,
                        'gold': 5000,
                        'platinum': 15000
                    }
                    current_user.token_balance += token_bonus.get(cert_data['level'], 0)
        
        if new_certifications:
            db.session.commit()
            return jsonify({
                'success': True,
                'new_certifications': new_certifications,
                'total_points': total_points,
                'token_balance': current_user.token_balance
            })
        
        return jsonify({
            'success': True,
            'new_certifications': [],
            'total_points': total_points
        })
        
    except Exception as e:
        print(f"Error checking certification: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/certification/generate-image/<int:cert_id>')
@login_required
def generate_certificate_image(cert_id):
    try:
        cert = Certification.query.get_or_404(cert_id)
        if cert.user_id != current_user.id:
            return "Unauthorized", 403
        
        img = create_certificate_image(
            username=current_user.username,
            certification_title=cert.title,
            level=cert.level,
            date=cert.earned_at,
            certificate_id=cert.certificate_id,
            points=cert.user_points
        )
        
        img_io = BytesIO()
        img.save(img_io, 'PNG', quality=95)
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png', as_attachment=True, 
                        download_name=f"EcoVerse_Certificate_{cert.certificate_id}.png")
        
    except Exception as e:
        print(f"Error generating certificate image: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/certification/ai-assessment')
@login_required
def get_ai_assessment():
    try:
        total_actions = CarbonAction.query.filter_by(user_id=current_user.id).count()
        eco_actions = EcoAction.query.filter_by(user_id=current_user.id).count()
        flights_completed = AviationQuest.query.filter_by(user_id=current_user.id, status='completed').count()
        carbon_footprint = CarbonFootprint.query.filter_by(user_id=current_user.id).first()
        
        assessment = generate_ai_assessment(
            username=current_user.username,
            eco_score=current_user.eco_score,
            total_actions=total_actions,
            eco_actions=eco_actions,
            flights_completed=flights_completed,
            carbon_footprint=carbon_footprint.total_co2 if carbon_footprint else 0,
            join_date=current_user.created_at
        )
        
        return jsonify({
            'success': True,
            'assessment': assessment
        })
        
    except Exception as e:
        print(f"Error generating AI assessment: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/certification/share/<int:cert_id>')
@login_required
def share_certification(cert_id):
    try:
        cert = Certification.query.get_or_404(cert_id)
        if cert.user_id != current_user.id:
            return "Unauthorized", 403
        
        share_message = generate_share_message(
            username=current_user.username,
            certification_title=cert.title,
            level=cert.level,
            points=cert.user_points
        )
        
        verify_link = f"https://ecoverse.com/verify/{cert.certificate_id}"
        
        hashtags = {
            'carbon_warrior': '#CarbonWarrior #EcoHero #Sustainability',
            'sustainability_expert': '#SustainabilityExpert #GreenLiving #EcoFriendly',
            'eco_innovator': '#EcoInnovator #ClimateAction #GreenTech',
            'climate_champion': '#ClimateChampion #SaveThePlanet #EcoVerse'
        }
        
        return jsonify({
            'success': True,
            'share_message': share_message,
            'verify_link': verify_link,
            'hashtags': hashtags.get(cert.certification_type, '#EcoVerse #Sustainability'),
            'certificate_id': cert.certificate_id
        })
        
    except Exception as e:
        print(f"Error sharing certification: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/certification/compare')
@login_required
def compare_certifications():
    try:
        user_certs = Certification.query.filter_by(user_id=current_user.id).all()
        
        community_stats = {
            'total_users': 10000,
            'bronze_certified': 4500,
            'silver_certified': 2500,
            'gold_certified': 800,
            'platinum_certified': 200,
            'top_percentile': 95 if current_user.eco_score > 20000 else 
                             80 if current_user.eco_score > 10000 else 
                             60 if current_user.eco_score > 5000 else 
                             30
        }
        
        comparison = generate_comparison_message(
            username=current_user.username,
            eco_score=current_user.eco_score,
            certifications=len(user_certs),
            community_stats=community_stats
        )
        
        return jsonify({
            'success': True,
            'user_stats': {
                'eco_score': current_user.eco_score,
                'total_certifications': len(user_certs),
                'highest_level': max([cert.level for cert in user_certs], default='none')
            },
            'community_stats': community_stats,
            'comparison_message': comparison
        })
        
    except Exception as e:
        print(f"Error comparing certifications: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/certification/list')
@login_required
def list_certifications():
    try:
        certifications = Certification.query.filter_by(user_id=current_user.id)\
                                          .order_by(Certification.earned_at.desc())\
                                          .all()
        
        cert_list = []
        for cert in certifications:
            cert_list.append({
                'id': cert.id,
                'title': cert.title,
                'level': cert.level,
                'certificate_id': cert.certificate_id,
                'description': cert.description,
                'ai_generated_text': cert.ai_generated_text,
                'points_required': cert.points_required,
                'user_points': cert.user_points,
                'earned_at': cert.earned_at.strftime('%Y-%m-%d'),
                'valid_until': cert.valid_until.strftime('%Y-%m-%d') if cert.valid_until else None
            })
        
        return jsonify({
            'success': True,
            'certifications': cert_list,
            'count': len(cert_list)
        })
        
    except Exception as e:
        print(f"Error listing certifications: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/ecoworld')
@login_required
def city_builder():
    return render_template('ecoworld.html', user=current_user)

@app.route('/api/city-builder/save', methods=['POST'])
@login_required
def save_city_builder():
    try:
        data = request.json
        
        save = EcoWorldSave.query.filter_by(user_id=current_user.id).first()
        if not save:
            save = EcoWorldSave(user_id=current_user.id)
            db.session.add(save)
        
        if 'cityName' in data:
            save.city_name = data['cityName']
        
        if 'buildings' in data:
            save.buildings = json.dumps(data['buildings'])
        
        if 'constructionQueue' in data:
            save.resources = json.dumps({
                'construction_queue': data['constructionQueue'],
                'treasury': data.get('treasury', 50000),
                'population': data.get('population', 1000),
                'happiness': data.get('happiness', 65),
                'pollution': data.get('pollution', 22),
                'crime': data.get('crime', 12),
                'employment': data.get('employment', 45),
                'tax_rate': data.get('taxRate', 9),
                'growth': data.get('growth', 2.1),
                'power': data.get('power', 45),
                'water': data.get('water', 78)
            })
        
        save.last_played = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'City saved successfully',
            'saved_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Error saving city: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/city-builder/load', methods=['GET'])
@login_required
def load_city_builder():
    try:
        save = EcoWorldSave.query.filter_by(user_id=current_user.id).first()
        
        if not save:
            return jsonify({
                'success': True,
                'new_game': True,
                'data': {
                    'cityName': 'New EcoCity',
                    'buildings': [],
                    'constructionQueue': [],
                    'treasury': 50000,
                    'population': 1000,
                    'happiness': 65,
                    'pollution': 22,
                    'crime': 12,
                    'employment': 45,
                    'taxRate': 9,
                    'growth': 2.1,
                    'power': 45,
                    'water': 78
                }
            })
        
        resources = json.loads(save.resources) if save.resources else {}
        
        data = {
            'cityName': save.city_name,
            'buildings': json.loads(save.buildings) if save.buildings else [],
            'constructionQueue': resources.get('construction_queue', []),
            'treasury': resources.get('treasury', 50000),
            'population': resources.get('population', 1000),
            'happiness': resources.get('happiness', 65),
            'pollution': resources.get('pollution', 22),
            'crime': resources.get('crime', 12),
            'employment': resources.get('employment', 45),
            'taxRate': resources.get('tax_rate', 9),
            'growth': resources.get('growth', 2.1),
            'power': resources.get('power', 45),
            'water': resources.get('water', 78)
        }
        
        return jsonify({
            'success': True,
            'new_game': False,
            'data': data,
            'last_played': save.last_played.isoformat()
        })
        
    except Exception as e:
        print(f"Error loading city: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/city-builder/building-types', methods=['GET'])
@login_required
def get_building_types():
    building_types = {
        'low_density_res': {
            'name': 'Low Density Residential',
            'type': 'residential',
            'cost': 1000,
            'population': [20, 50],
            'jobs': [5, 10],
            'tax': 200,
            'pollution': 0,
            'happiness': 5,
            'icon': '🏘️',
            'build_time': 2,
            'upkeep': 50,
            'size': 1,
            'category': 'residential',
            'description': 'Single-family homes for a growing population'
        },
        'medium_density_res': {
            'name': 'Medium Density Apartment',
            'type': 'residential',
            'cost': 2500,
            'population': [50, 150],
            'jobs': [15, 30],
            'tax': 600,
            'pollution': 2,
            'happiness': 10,
            'icon': '🏢',
            'build_time': 4,
            'upkeep': 120,
            'size': 1,
            'category': 'residential',
            'description': 'Multi-story apartments for urban living'
        },
        'small_commercial': {
            'name': 'Small Business Zone',
            'type': 'commercial',
            'cost': 2000,
            'population': 0,
            'jobs': [10, 20],
            'tax': 400,
            'pollution': 5,
            'happiness': 5,
            'icon': '🏪',
            'build_time': 3,
            'upkeep': 80,
            'size': 1,
            'category': 'commercial',
            'description': 'Local shops and services'
        },
        'light_industrial': {
            'name': 'Light Industry',
            'type': 'industrial',
            'cost': 3000,
            'population': 0,
            'jobs': [30, 60],
            'tax': 800,
            'pollution': 15,
            'happiness': -10,
            'icon': '🏭',
            'build_time': 5,
            'upkeep': 150,
            'size': 2,
            'category': 'industrial',
            'description': 'Manufacturing with moderate pollution'
        },
        'coal_power': {
            'name': 'Coal Power Plant',
            'type': 'utility',
            'cost': 15000,
            'population': 0,
            'jobs': [50, 80],
            'tax': 1200,
            'pollution': 50,
            'happiness': -20,
            'icon': '🏭',
            'build_time': 6,
            'upkeep': 500,
            'size': 4,
            'category': 'utilities',
            'description': 'High-capacity power with heavy pollution',
            'power_output': 100
        },
        'solar_farm': {
            'name': 'Solar Farm',
            'type': 'utility',
            'cost': 25000,
            'population': 0,
            'jobs': [10, 15],
            'tax': 300,
            'pollution': -5,
            'happiness': 15,
            'icon': '☀️',
            'build_time': 8,
            'upkeep': 100,
            'size': 6,
            'category': 'utilities',
            'description': 'Clean renewable energy source',
            'power_output': 40
        },
        'water_treatment': {
            'name': 'Water Treatment Plant',
            'type': 'utility',
            'cost': 12000,
            'population': 0,
            'jobs': [20, 30],
            'tax': 400,
            'pollution': -10,
            'happiness': 20,
            'icon': '💧',
            'build_time': 4,
            'upkeep': 300,
            'size': 3,
            'category': 'utilities',
            'description': 'Provides clean water to the city',
            'water_output': 100
        },
        'police_station': {
            'name': 'Police Station',
            'type': 'service',
            'cost': 8000,
            'population': 0,
            'jobs': [30, 40],
            'tax': 200,
            'pollution': 0,
            'happiness': 10,
            'icon': '🚓',
            'build_time': 3,
            'upkeep': 200,
            'size': 2,
            'category': 'services',
            'description': 'Reduces crime and improves safety',
            'crime_reduction': 20
        },
        'hospital': {
            'name': 'Hospital',
            'type': 'service',
            'cost': 20000,
            'population': 0,
            'jobs': [80, 120],
            'tax': 500,
            'pollution': 0,
            'happiness': 30,
            'icon': '🏥',
            'build_time': 10,
            'upkeep': 500,
            'size': 4,
            'category': 'services',
            'description': 'Provides healthcare and increases happiness'
        },
        'small_park': {
            'name': 'Neighborhood Park',
            'type': 'park',
            'cost': 5000,
            'population': 0,
            'jobs': [2, 5],
            'tax': 50,
            'pollution': -5,
            'happiness': 15,
            'icon': '🌳',
            'build_time': 4,
            'upkeep': 50,
            'size': 2,
            'category': 'parks',
            'description': 'Green space that improves quality of life'
        }
    }
    
    return jsonify({
        'success': True,
        'building_types': building_types,
        'categories': ['residential', 'commercial', 'industrial', 'utilities', 'services', 'parks']
    })

@app.route('/api/city-builder/calculate-stats', methods=['POST'])
@login_required
def calculate_city_stats():
    try:
        data = request.json
        buildings = data.get('buildings', [])
        tax_rate = data.get('taxRate', 9)
        
        stats = {
            'population': 1000,
            'total_jobs': 0,
            'total_tax': 0,
            'total_upkeep': 0,
            'total_pollution': 0,
            'total_happiness': 0,
            'total_power': 0,
            'total_water': 0,
            'crime_reduction': 0,
            'monthly_income': 0,
            'monthly_expenses': 0,
            'employment_rate': 0,
            'happiness': 65,
            'pollution': 22,
            'crime': 12,
            'growth': 2.1
        }
        
        building_types_response = get_building_types()
        building_types = building_types_response.get_json()['building_types']
        
        operational_buildings = [b for b in buildings if b.get('operational', True)]
        
        for building in operational_buildings:
            btype = building.get('type')
            if btype in building_types:
                bdata = building_types[btype]
                
                if bdata['type'] == 'residential':
                    pop_range = bdata['population']
                    if isinstance(pop_range, list) and len(pop_range) == 2:
                        pop = random.randint(pop_range[0], pop_range[1])
                        stats['population'] += pop
                
                if bdata.get('jobs'):
                    job_range = bdata['jobs']
                    if isinstance(job_range, list) and len(job_range) == 2:
                        jobs = random.randint(job_range[0], job_range[1])
                        stats['total_jobs'] += jobs
                
                stats['total_tax'] += bdata.get('tax', 0)
                stats['total_upkeep'] += bdata.get('upkeep', 0)
                stats['total_pollution'] += bdata.get('pollution', 0)
                stats['total_happiness'] += bdata.get('happiness', 0)
                stats['total_power'] += bdata.get('power_output', 0)
                stats['total_water'] += bdata.get('water_output', 0)
                stats['crime_reduction'] += bdata.get('crime_reduction', 0)
        
        tax_revenue = stats['population'] * tax_rate * 0.1
        
        stats['monthly_income'] = tax_revenue + stats['total_tax']
        stats['monthly_expenses'] = stats['total_upkeep']
        
        if stats['population'] > 0:
            stats['employment_rate'] = min(95, (stats['total_jobs'] / stats['population']) * 100)
        
        base_happiness = 50 + stats['total_happiness']
        happiness_penalty = max(0, stats['total_pollution'] / 10)
        happiness_penalty += stats['crime']
        happiness_penalty += (tax_rate - 5) * 2
        stats['happiness'] = max(0, min(100, base_happiness - happiness_penalty))
        
        stats['pollution'] = max(0, min(100, 22 + stats['total_pollution']))
        
        crime = 20 - stats['crime_reduction']
        crime += min(30, stats['population'] / 50000 * 10)
        stats['crime'] = max(5, min(95, crime))
        
        growth = 0
        growth += (stats['happiness'] - 50) / 10
        growth += (stats['employment_rate'] - 50) / 10
        growth -= (tax_rate - 10) / 5
        stats['growth'] = max(-5, min(10, round(growth, 1)))
        
        return jsonify({
            'success': True,
            'stats': stats,
            'tax_revenue': tax_revenue
        })
        
    except Exception as e:
        print(f"Error calculating stats: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/city-builder/process-construction', methods=['POST'])
@login_required
def process_construction():
    try:
        data = request.json
        construction_queue = data.get('constructionQueue', [])
        game_speed = data.get('gameSpeed', 1)
        
        updated_queue = []
        completed_buildings = []
        
        for site in construction_queue:
            if not site.get('operational', False):
                site['progress'] = site.get('progress', 0) + game_speed
                
                if site['progress'] >= site.get('totalTime', 30):
                    site['operational'] = True
                    completed_buildings.append({
                        'type': site['type'],
                        'x': site['x'],
                        'y': site['y']
                    })
                else:
                    updated_queue.append(site)
            else:
                updated_queue.append(site)
        
        return jsonify({
            'success': True,
            'updatedQueue': updated_queue,
            'completedBuildings': completed_buildings,
            'message': f'Processed {len(completed_buildings)} completed constructions' if completed_buildings else 'No constructions completed'
        })
        
    except Exception as e:
        print(f"Error processing construction: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/city-builder/trigger-event', methods=['GET'])
@login_required
def trigger_random_event():
    try:
        events = [
            {
                'type': 'positive',
                'title': 'Tourism Boom',
                'message': 'A major festival is attracting tourists! Tourism revenue increased by 15% this month.',
                'effect': {'treasury': 5000, 'happiness': 5},
                'duration': 30
            },
            {
                'type': 'negative',
                'title': 'Power Grid Failure',
                'message': 'A major power outage has affected the city! Industrial production reduced by 20%.',
                'effect': {'happiness': -10, 'treasury': -2000},
                'duration': 15
            },
            {
                'type': 'neutral',
                'title': 'Population Growth',
                'message': 'A baby boom has increased population growth by 3% this year.',
                'effect': {'population': 150},
                'duration': 365
            },
            {
                'type': 'negative',
                'title': 'Economic Recession',
                'message': 'Global economic downturn has reduced tax revenue by 10%.',
                'effect': {'treasury': -3000, 'employment': -5},
                'duration': 90
            },
            {
                'type': 'positive',
                'title': 'Green Initiative Grant',
                'message': 'The city received a federal grant for sustainable development!',
                'effect': {'treasury': 10000, 'happiness': 10},
                'duration': 1
            }
        ]
        
        event = random.choice(events)
        
        event['triggered_at'] = datetime.utcnow().isoformat()
        
        return jsonify({
            'success': True,
            'event': event
        })
        
    except Exception as e:
        print(f"Error triggering event: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/city-builder/simulate-disaster', methods=['POST'])
@login_required
def simulate_disaster():
    try:
        data = request.json
        disaster_type = data.get('type', 'random')
        
        disasters = {
            'earthquake': {
                'name': 'Major Earthquake',
                'description': 'A 7.2 magnitude earthquake strikes the city!',
                'effects': {
                    'building_damage': 0.3,
                    'population_loss': 0.1,
                    'treasury_cost': 20000,
                    'happiness_penalty': -20
                },
                'recovery_time': 180
            },
            'flood': {
                'name': 'Severe Flooding',
                'description': 'Heavy rains cause widespread flooding in low-lying areas!',
                'effects': {
                    'building_damage': 0.2,
                    'population_loss': 0.05,
                    'treasury_cost': 15000,
                    'happiness_penalty': -15,
                    'pollution_increase': 10
                },
                'recovery_time': 120
            },
            'tornado': {
                'name': 'Tornado Outbreak',
                'description': 'Multiple tornadoes touch down across the city!',
                'effects': {
                    'building_damage': 0.4,
                    'population_loss': 0.15,
                    'treasury_cost': 25000,
                    'happiness_penalty': -25
                },
                'recovery_time': 210
            },
            'heatwave': {
                'name': 'Extreme Heat Wave',
                'description': 'Record-breaking temperatures strain infrastructure!',
                'effects': {
                    'population_loss': 0.02,
                    'treasury_cost': 8000,
                    'happiness_penalty': -10,
                    'power_demand': 30
                },
                'recovery_time': 60
            }
        }
        
        if disaster_type == 'random':
            disaster = random.choice(list(disasters.values()))
        elif disaster_type in disasters:
            disaster = disasters[disaster_type]
        else:
            disaster = disasters['earthquake']
        
        disaster['occurred_at'] = datetime.utcnow().isoformat()
        
        return jsonify({
            'success': True,
            'disaster': disaster,
            'message': 'Disaster simulated'
        })
        
    except Exception as e:
        print(f"Error simulating disaster: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/city-builder/export-report', methods=['POST'])
@login_required
def export_city_report():
    try:
        data = request.json
        city_name = data.get('cityName', 'EcoCity')
        stats = data.get('stats', {})
        buildings = data.get('buildings', [])
        
        report = f"""
        ========================================
        CITY REPORT: {city_name}
        Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}
        ========================================
        
        POPULATION STATISTICS
        ----------------------
        Total Population: {stats.get('population', 0):,}
        Employment Rate: {stats.get('employment_rate', 0):.1f}%
        Monthly Growth: {stats.get('growth', 0):+.1f}%
        
        CITY METRICS
        -------------
        Happiness: {stats.get('happiness', 0)}/100
        Pollution: {stats.get('pollution', 0)}/100
        Crime Rate: {stats.get('crime', 0)}/100
        
        FINANCIAL OVERVIEW
        -------------------
        Treasury: ${stats.get('treasury', 0):,}
        Monthly Income: ${stats.get('monthly_income', 0):,}
        Monthly Expenses: ${stats.get('monthly_expenses', 0):,}
        Net Monthly: ${stats.get('monthly_income', 0) - stats.get('monthly_expenses', 0):,}
        
        INFRASTRUCTURE
        ---------------
        Total Buildings: {len(buildings)}
        Operational Buildings: {len([b for b in buildings if b.get('operational', True)])}
        Under Construction: {len([b for b in buildings if not b.get('operational', True)])}
        
        RESOURCE CAPACITY
        ------------------
        Power Generation: {stats.get('total_power', 0)} MW
        Water Supply: {stats.get('total_water', 0)} ML
        
        BUILDING SUMMARY
        -----------------
        """
        
        building_counts = {}
        for building in buildings:
            btype = building.get('type', 'unknown')
            building_counts[btype] = building_counts.get(btype, 0) + 1
        
        for btype, count in building_counts.items():
            report += f"        {btype.replace('_', ' ').title()}: {count}\n"
        
        report += f"""
        ========================================
        END OF REPORT
        """
        
        csv_data = "Category,Metric,Value\n"
        csv_data += f"Population,Total Population,{stats.get('population', 0)}\n"
        csv_data += f"Economy,Employment Rate,{stats.get('employment_rate', 0)}\n"
        csv_data += f"Economy,Monthly Growth,{stats.get('growth', 0)}\n"
        csv_data += f"Metrics,Happiness,{stats.get('happiness', 0)}\n"
        csv_data += f"Metrics,Pollution,{stats.get('pollution', 0)}\n"
        csv_data += f"Metrics,Crime Rate,{stats.get('crime', 0)}\n"
        csv_data += f"Finance,Treasury,{stats.get('treasury', 0)}\n"
        csv_data += f"Finance,Monthly Income,{stats.get('monthly_income', 0)}\n"
        csv_data += f"Finance,Monthly Expenses,{stats.get('monthly_expenses', 0)}\n"
        csv_data += f"Infrastructure,Total Buildings,{len(buildings)}\n"
        
        return jsonify({
            'success': True,
            'report': {
                'text': report,
                'csv': csv_data,
                'timestamp': datetime.utcnow().isoformat(),
                'city_name': city_name
            }
        })
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/city-builder/validate-placement', methods=['POST'])
@login_required
def validate_building_placement():
    try:
        data = request.json
        building_type = data.get('type')
        x = data.get('x')
        y = data.get('y')
        size = data.get('size', 1)
        existing_buildings = data.get('existingBuildings', [])
        grid_width = data.get('gridWidth', 40)
        grid_height = data.get('gridHeight', 30)
        
        if x < 0 or y < 0 or (x + size) > grid_width or (y + size) > grid_height:
            return jsonify({
                'success': True,
                'valid': False,
                'reason': f'Outside grid boundaries (Grid: {grid_width}x{grid_height})'
            })
        
        for building in existing_buildings:
            b_x = building.get('x')
            b_y = building.get('y')
            b_size = building.get('size', 1)
            
            if not (x + size <= b_x or x >= b_x + b_size or
                    y + size <= b_y or y >= b_y + b_size):
                return jsonify({
                    'success': True,
                    'valid': False,
                    'reason': f'Overlaps with existing building at ({b_x},{b_y})'
                })
        
        return jsonify({
            'success': True,
            'valid': True,
            'position': {'x': x, 'y': y}
        })
        
    except Exception as e:
        print(f"Error validating placement: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/city-builder/demolish', methods=['POST'])
@login_required
def demolish_building():
    try:
        data = request.json
        building_id = data.get('buildingId')
        building_type = data.get('type')
        building_cost = data.get('cost', 0)
        
        refund = building_cost * 0.5
        
        building_types_response = get_building_types()
        building_types = building_types_response.get_json()['building_types']
        
        bdata = building_types.get(building_type, {})
        
        pollution_reduction = abs(bdata.get('pollution', 0))
        if pollution_reduction > 0:
            pollution_reduction = -pollution_reduction
        
        return jsonify({
            'success': True,
            'refund': refund,
            'effects': {
                'pollution_change': pollution_reduction,
                'happiness_change': -bdata.get('happiness', 0) * 0.5,
                'tax_loss': -bdata.get('tax', 0),
                'upkeep_savings': bdata.get('upkeep', 0)
            },
            'message': f'Building demolished. Refund: ${refund:,.0f}'
        })
        
    except Exception as e:
        print(f"Error demolishing building: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/city-builder/upgrade', methods=['POST'])
@login_required
def upgrade_building():
    try:
        data = request.json
        building_id = data.get('buildingId')
        building_type = data.get('type')
        current_level = data.get('level', 1)
        
        base_cost = data.get('cost', 0)
        upgrade_cost = base_cost * (current_level * 0.5)
        
        building_types_response = get_building_types()
        building_types = building_types_response.get_json()['building_types']
        bdata = building_types.get(building_type, {})
        
        upgrade_benefits = {
            'population_boost': bdata.get('population', [0, 0])[1] * 0.2 if isinstance(bdata.get('population'), list) else 0,
            'tax_boost': bdata.get('tax', 0) * 0.3,
            'happiness_boost': bdata.get('happiness', 0) * 0.2,
            'upkeep_increase': bdata.get('upkeep', 0) * 0.1
        }
        
        return jsonify({
            'success': True,
            'upgrade_cost': upgrade_cost,
            'new_level': current_level + 1,
            'benefits': upgrade_benefits,
            'message': f'Upgrade to level {current_level + 1} available for ${upgrade_cost:,.0f}'
        })
        
    except Exception as e:
        print(f"Error upgrading building: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/city-builder/daily-maintenance', methods=['POST'])
@login_required
def calculate_daily_maintenance():
    try:
        data = request.json
        buildings = data.get('buildings', [])
        city_age = data.get('cityAge', 1)
        
        total_upkeep = 0
        maintenance_events = []
        
        operational_buildings = [b for b in buildings if b.get('operational', True)]
        
        building_types_response = get_building_types()
        building_types = building_types_response.get_json()['building_types']
        
        for building in operational_buildings:
            btype = building.get('type')
            if btype in building_types:
                bdata = building_types[btype]
                
                upkeep = bdata.get('upkeep', 0)
                total_upkeep += upkeep
                
                if random.random() < 0.05:
                    event_cost = upkeep * random.uniform(0.1, 0.5)
                    total_upkeep += event_cost
                    
                    maintenance_events.append({
                        'building_type': btype,
                        'event': random.choice([
                            'Routine maintenance required',
                            'Equipment replacement needed',
                            'System upgrade recommended',
                            'Safety inspection passed'
                        ]),
                        'cost': event_cost
                    })
        
        if random.random() < 0.02:
            city_event = random.choice([
                {'type': 'infrastructure', 'cost': 1000, 'message': 'Road maintenance required'},
                {'type': 'public_service', 'cost': 500, 'message': 'Public service funding needed'},
                {'type': 'environmental', 'cost': 800, 'message': 'Environmental cleanup initiative'}
            ])
            total_upkeep += city_event['cost']
            maintenance_events.append(city_event)
        
        return jsonify({
            'success': True,
            'daily_upkeep': total_upkeep,
            'maintenance_events': maintenance_events,
            'message': f'Daily maintenance calculated: ${total_upkeep:,.0f}'
        })
        
    except Exception as e:
        print(f"Error calculating maintenance: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/city-builder/complete-tutorial', methods=['POST'])
@login_required
def complete_city_builder_tutorial():
    try:
        current_user.token_balance += 100
        current_user.eco_score += 50
        
        action = EcoAction(
            user_id=current_user.id,
            action_type='city_builder_tutorial',
            co2_saved=5.0,
            tokens_earned=100,
            created_at=datetime.utcnow()
        )
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tokens_awarded': 100,
            'new_balance': current_user.token_balance,
            'message': 'City builder tutorial completed!'
        })
        
    except Exception as e:
        print(f"Error completing tutorial: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/aviation/get-questions/<int:quest_id>', methods=['GET'])
@login_required
def get_questions_for_quest(quest_id):
    import random
    random.shuffle(CARBON_QUESTIONS)
    selected_questions = CARBON_QUESTIONS[:2]
    
    return jsonify({
        'success': True,
        'questions': selected_questions
    })

@app.route('/api/aviation/complete-flight/<int:quest_id>', methods=['POST'])
@login_required
def complete_flight_quest(quest_id):
    quest = AviationQuest.query.get(quest_id)
    
    if not quest or quest.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Quest not found'})
    
    if quest.status != 'active':
        return jsonify({'success': False, 'message': 'Flight already completed'})
    
    distances = {
        'SIN-HKG': 2591,
        'HKG-SIN': 2591,
        'JFK-LHR': 5567,
        'LHR-JFK': 5567,
        'DFW-HKG': 12964,
        'BOM-DXB': 1924,
        'SYD-LAX': 12051,
        'CDG-NRT': 9718
    }
    
    route = f"{quest.departure_airport}-{quest.arrival_airport}"
    distance = distances.get(route, 5000)
    
    base_tokens = 100
    distance_bonus = int(distance / 1000) * 20
    total_tokens = base_tokens + distance_bonus
    
    co2_per_km = 0.115
    total_co2 = distance * co2_per_km
    
    quest.status = 'completed'
    quest.end_time = datetime.utcnow()
    quest.tokens_earned = total_tokens
    quest.co2_offset = total_co2
    
    current_user.token_balance += total_tokens
    current_user.eco_score += 200
    
    action = CarbonAction(
        user_id=current_user.id,
        action_type='aviation_quest_complete',
        co2_saved=total_co2,
        description=f'Completed flight: {quest.departure_airport} to {quest.arrival_airport}'
    )
    db.session.add(action)
    
    db.session.commit()
    
    arrival_country = get_country_from_airport(quest.arrival_airport)
    
    return jsonify({
        'success': True,
        'tokens_earned': total_tokens,
        'co2_offset': total_co2,
        'arrival_country': arrival_country,
        'token_balance': current_user.token_balance,
        'eco_score': current_user.eco_score,
        'flight_number': quest.flight_number,
        'seat': quest.seat,
        'score': 100
    })

@app.route('/api/aviation/simulate-flight/<int:quest_id>', methods=['GET'])
@login_required
def simulate_flight(quest_id):
    quest = AviationQuest.query.get(quest_id)
    
    if not quest or quest.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Quest not found'})
    
    if quest.status != 'active':
        return jsonify({'success': False, 'message': 'Flight already completed'})
    
    departure_info = get_airport_details(quest.departure_airport)
    arrival_info = get_airport_details(quest.arrival_airport)
    
    import random
    random.shuffle(CARBON_QUESTIONS)
    selected_questions = CARBON_QUESTIONS[:2]
    
    simulation_data = {
        'quest_id': quest.id,
        'flight_number': quest.flight_number,
        'airline': quest.airline,
        'aircraft': quest.aircraft,
        'departure': {
            'code': quest.departure_airport,
            'name': departure_info['name'],
            'city': departure_info['city'],
            'country': departure_info['country'],
            'gate': quest.gate
        },
        'arrival': {
            'code': quest.arrival_airport,
            'name': arrival_info['name'],
            'city': arrival_info['city'],
            'country': arrival_info['country']
        },
        'seat': quest.seat,
        'passenger': current_user.username,
        'carbon_questions': selected_questions,
        'simulation_phases': [
            {
                'phase': 'immigration',
                'title': 'Passport Control',
                'duration': 30,
                'description': 'Complete immigration formalities',
                'actions': ['Show passport', 'Answer security questions', 'Get exit stamp']
            },
            {
                'phase': 'preflight',
                'title': 'Pre-flight Checks',
                'duration': 60,
                'description': 'Aircraft preparation',
                'actions': ['APU Start', 'Flight Computer Check', 'Safety Systems Test']
            },
            {
                'phase': 'pushback',
                'title': 'Pushback & Engine Start',
                'duration': 30,
                'description': 'Leaving the gate',
                'actions': ['Disconnect ground power', 'Start engines', 'Pushback from gate']
            },
            {
                'phase': 'taxi',
                'title': 'Taxi to Runway',
                'duration': 45,
                'description': 'Taxiing to takeoff position',
                'actions': ['Follow taxiway', 'Runway check', 'Hold short of runway']
            },
            {
                'phase': 'takeoff',
                'title': 'Takeoff',
                'duration': 30,
                'description': 'Takeoff sequence',
                'actions': ['Takeoff clearance', 'Full throttle', 'Rotation', 'Lift off']
            },
            {
                'phase': 'climb',
                'title': 'Climb to Cruise',
                'duration': 120,
                'description': 'Ascending to cruising altitude',
                'actions': ['Retract flaps', 'Climb power', 'Level off at 35,000ft']
            },
            {
                'phase': 'cruise',
                'title': 'Cruise',
                'duration': 180,
                'description': 'Cruising at altitude',
                'actions': ['Autopilot engaged', 'Carbon quiz time', 'Weather monitoring']
            },
            {
                'phase': 'descent',
                'title': 'Descent',
                'duration': 90,
                'description': 'Beginning descent',
                'actions': ['Start descent', 'Speed reduction', 'Configure for landing']
            },
            {
                'phase': 'approach',
                'title': 'Approach & Landing',
                'duration': 60,
                'description': 'Final approach and landing',
                'actions': ['Final approach', 'Flaps full', 'Gear down', 'Touchdown']
            },
            {
                'phase': 'arrival',
                'title': 'Arrival',
                'duration': 45,
                'description': 'Taxi to gate and disembark',
                'actions': ['Reverse thrust', 'Taxi to gate', 'Park at gate', 'Disembark']
            }
        ]
    }
    
    return jsonify({'success': True, 'simulation': simulation_data})

@app.route('/api/aviation/check-immigration', methods=['POST'])
@login_required
def check_immigration():
    data = request.json
    quest_id = data.get('quest_id')
    
    quest = AviationQuest.query.get(quest_id)
    if not quest or quest.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Quest not found'})
    
    passport_valid = True
    security_questions = [
        "What is the purpose of your trip?",
        "How long will you be staying?",
        "Where will you be staying?"
    ]
    
    return jsonify({
        'success': True,
        'passport_valid': passport_valid,
        'security_questions': security_questions,
        'immigration_completed': True
    })

@app.route('/api/aviation/submit-carbon-quiz/<int:quest_id>', methods=['POST'])
@login_required
def submit_carbon_quiz(quest_id):
    data = request.json
    answers = data.get('answers', [])
    
    quest = AviationQuest.query.get(quest_id)
    if not quest or quest.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Quest not found'})
    
    quiz_questions = CARBON_QUESTIONS[:2]
    
    correct_answers = 0
    results = []
    
    for i, answer in enumerate(answers):
        if i < len(quiz_questions):
            question = quiz_questions[i]
            if answer == question['correct']:
                correct_answers += 1
                results.append({
                    'question': question['question'],
                    'correct': True,
                    'explanation': question['explanation']
                })
            else:
                results.append({
                    'question': question['question'],
                    'correct': False,
                    'explanation': question['explanation']
                })
        else:
            results.append({
                'question': 'Unknown',
                'correct': False,
                'explanation': 'Question not found'
            })
    
    tokens_earned = 0
    if correct_answers == 2:
        tokens_earned = 140
    elif correct_answers == 1:
        tokens_earned = 70
    
    current_user.token_balance += tokens_earned
    db.session.commit()
    
    return jsonify({
        'success': True,
        'correct_answers': correct_answers,
        'total_questions': 2,
        'tokens_earned': tokens_earned,
        'results': results
    })

@app.route('/api/aviation/check-carbon-quiz/<int:quest_id>', methods=['POST'])
@login_required
def check_carbon_quiz(quest_id):
    return submit_carbon_quiz(quest_id)

@app.route('/api/aviation/get-quiz-questions/<int:quest_id>', methods=['GET'])
@login_required
def get_quiz_questions_for_quest(quest_id):
    quest = AviationQuest.query.get(quest_id)
    
    if not quest or quest.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Quest not found'})
    
    selected_questions = CARBON_QUESTIONS[:2]
    
    return jsonify({
        'success': True,
        'questions': selected_questions
    })

@app.route('/api/aviation/get-aircraft/<airline>')
@login_required
def get_aircraft_for_airline(airline):
    airlines = {
        'Singapore Airlines': ['A380', 'A350-900', '777X', '787-9'],
        'Cathay Pacific': ['A350-900', 'A350-1000', '777X'],
        'Scoot': ['A320neo', '787-9'],
        'American Airlines': ['777X', '787-9', 'A330'],
        'British Airways': ['A380', 'A350', '777X', '787-9'],
        'Emirates': ['A380', '777X'],
        'Qatar Airways': ['A350-1000', '777X', '787-9'],
        'Delta': ['A350-900', 'A330', '757'],
        'United': ['777X', '787-9', '767'],
        'Air France': ['A350', '777X', 'A330']
    }
    
    return jsonify({
        'success': True,
        'aircraft': airlines.get(airline, [])
    })

@app.route('/api/aviation/get-gates/<airport>')
@login_required
def get_gates_for_airport(airport):
    gates = {
        'SIN': ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10', 'A11', 'B1', 'B2', 'B3', 'B4'],
        'DFW': ['A21', 'A22', 'A23', 'A24', 'A25', 'B31', 'B32', 'B33', 'B34', 'B35', 'C41', 'C42', 'C43', 'C44'],
        'JFK': ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8'],
        'BOM': ['1A', '1B', '2A', '2B', '3A', '3B', '4A', '4B'],
        'HKG': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14']
    }
    
    return jsonify({
        'success': True,
        'gates': gates.get(airport, ['A1', 'A2', 'A3', 'A4', 'A5'])
    })

@app.route('/api/aviation/start-quest', methods=['POST'])
@login_required
def start_aviation_quest():
    data = request.json
    
    airports = {
        'SIN': {'name': 'Singapore Changi', 'icao': 'WSSS', 'city': 'Singapore'},
        'DFW': {'name': 'Dallas/Fort Worth', 'icao': 'KDFW', 'city': 'Dallas'},
        'JFK': {'name': 'John F. Kennedy', 'icao': 'KJFK', 'city': 'New York'},
        'BOM': {'name': 'Chhatrapati Shivaji', 'icao': 'VABB', 'city': 'Mumbai'},
        'HKG': {'name': 'Hong Kong', 'icao': 'VHHH', 'city': 'Hong Kong'},
        'LHR': {'name': 'London Heathrow', 'icao': 'EGLL', 'city': 'London'},
        'CDG': {'name': 'Paris Charles de Gaulle', 'icao': 'LFPG', 'city': 'Paris'},
        'NRT': {'name': 'Tokyo Narita', 'icao': 'RJAA', 'city': 'Tokyo'},
        'SYD': {'name': 'Sydney Kingsford Smith', 'icao': 'YSSY', 'city': 'Sydney'},
        'DXB': {'name': 'Dubai International', 'icao': 'OMDB', 'city': 'Dubai'}
    }
    
    airlines = {
        'Singapore Airlines': {'code': 'SQ', 'aircraft': ['A380', 'A350-900', '777-300ER', '787-10']},
        'Cathay Pacific': {'code': 'CX', 'aircraft': ['A350-900', 'A350-1000', '777-300ER']},
        'Scoot': {'code': 'TR', 'aircraft': ['A320neo', '787-9']},
        'American Airlines': {'code': 'AA', 'aircraft': ['777-200', '787-9', 'A330-200']},
        'British Airways': {'code': 'BA', 'aircraft': ['A380', 'A350', '777-200', '787-9']},
        'Emirates': {'code': 'EK', 'aircraft': ['A380', '777-300ER']},
        'Qatar Airways': {'code': 'QR', 'aircraft': ['A350-1000', '777-300ER', '787-9']},
        'Delta': {'code': 'DL', 'aircraft': ['A350-900', 'A330-200', '757-200']},
        'United': {'code': 'UA', 'aircraft': ['777-200', '787-9', '767-300']},
        'Air France': {'code': 'AF', 'aircraft': ['A350', '777-200', 'A330']}
    }
    
    departure = data.get('departure', 'SIN')
    arrival = data.get('arrival', 'HKG')
    airline_name = data.get('airline', 'Singapore Airlines')
    aircraft = data.get('aircraft', 'A350-900')
    seat = data.get('seat', '21C')
    gate = data.get('gate', 'A11')
    passport_country = data.get('passport_country', 'India')
    
    if departure not in airports or arrival not in airports:
        return jsonify({'success': False, 'message': 'Invalid airport selection'})
    
    if airline_name not in airlines:
        return jsonify({'success': False, 'message': 'Invalid airline selection'})
    
    if aircraft not in airlines[airline_name]['aircraft']:
        return jsonify({'success': False, 'message': 'This airline does not operate this aircraft type'})
    
    import random
    airline_code = airlines[airline_name]['code']
    flight_number = f"{airline_code}{random.randint(100, 999)}"
    
    quest = AviationQuest(
        user_id=current_user.id,
        quest_type='carbon_offset_flight',
        departure_airport=departure,
        arrival_airport=arrival,
        airline=airline_name,
        aircraft=aircraft,
        seat=seat,
        gate=gate,
        flight_number=flight_number,
        passport_country=passport_country,
        status='booked',
        start_time=datetime.utcnow()
    )

    arrival_airport = data.get('arrival')
    arrival_country = get_country_from_airport_code(arrival_airport)
    
    session['destination_country'] = arrival_country
    session['departure_airport'] = data.get('departure')
    session['arrival_airport'] = arrival_airport
    session['flight_booking_data'] = json.dumps({
        'departure': data.get('departure'),
        'arrival': arrival_airport,
        'airline': data.get('airline'),
        'aircraft': data.get('aircraft'),
        'seat': data.get('seat'),
        'gate': data.get('gate'),
        'arrival_country': arrival_country
    })
    
    db.session.add(quest)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'quest_id': quest.id,
        'flight_number': flight_number,
        'message': 'Flight booking confirmed successfully'
    })

@app.route('/api/aviation/complete-quest/<int:quest_id>', methods=['POST'])
@login_required
def complete_aviation_quest(quest_id):
    quest = AviationQuest.query.get(quest_id)
    
    if not quest or quest.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Quest not found'})
    
    if quest.status != 'active':
        return jsonify({'success': False, 'message': 'Quest already completed'})
    
    duration = datetime.utcnow() - quest.start_time
    hours = duration.total_seconds() / 3600
    
    distances = {
        'SIN-HKG': 2591,
        'HKG-SIN': 2591,
        'JFK-LHR': 5567,
        'LHR-JFK': 5567,
        'DFW-HKG': 12964,
        'BOM-DXB': 1924,
        'SYD-LAX': 12051,
        'CDG-NRT': 9718
    }
    
    route = f"{quest.departure_airport}-{quest.arrival_airport}"
    distance = distances.get(route, 5000)
    
    co2_per_km = 0.115
    total_co2 = distance * co2_per_km
    
    base_tokens = 100
    distance_bonus = int(distance / 1000) * 20
    time_bonus = max(0, 100 - int(hours * 10))
    total_tokens = base_tokens + distance_bonus + time_bonus
    
    quest.status = 'completed'
    quest.end_time = datetime.utcnow()
    quest.tokens_earned = total_tokens
    quest.co2_offset = total_co2
    
    current_user.token_balance += total_tokens
    current_user.eco_score += 200
    
    action = CarbonAction(
        user_id=current_user.id,
        action_type='aviation_quest',
        co2_saved=total_co2,
        description=f'Completed aviation quest: {quest.departure_airport} to {quest.arrival_airport}'
    )
    db.session.add(action)
    
    db.session.commit()
    
    arrival_country = get_country_from_airport(quest.arrival_airport)
    
    return jsonify({
        'success': True,
        'tokens_earned': total_tokens,
        'co2_offset': total_co2,
        'duration_hours': round(hours, 2),
        'token_balance': current_user.token_balance,
        'eco_score': current_user.eco_score,
        'arrival_country': arrival_country,
        'flight_number': quest.flight_number,
        'seat': quest.seat,
        'score': 100
    })

@app.route('/api/ecoworld/delete-object', methods=['POST'])
@login_required
def delete_object():
    data = request.json
    object_id = data.get('object_id')
    obj_type = data.get('type')
    x = data.get('x')
    y = data.get('y')
    
    save = EcoWorldSave.query.filter_by(user_id=current_user.id).first()
    if not save:
        return jsonify({'success': False, 'message': 'Save not found'})
    
    if obj_type == 'building':
        buildings = json.loads(save.buildings)
        buildings = [b for b in buildings if not (b.get('x') == x and b.get('y') == y)]
        save.buildings = json.dumps(buildings)
    elif obj_type == 'tree':
        trees = json.loads(save.trees)
        trees = [t for t in trees if not (t.get('x') == x and t.get('y') == y)]
        save.trees = json.dumps(trees)
    
    resources = json.loads(save.resources)
    save.population = max(100, save.population - 10)
    save.happiness = max(0, save.happiness - 5)
    
    refund = 20 if obj_type == 'building' else 10
    current_user.token_balance += refund
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'resources': resources,
        'population': save.population,
        'happiness': save.happiness,
        'tokens': current_user.token_balance
    })

@app.route('/api/ecoworld/reset-city', methods=['POST'])
@login_required
def reset_city():
    save = EcoWorldSave.query.filter_by(user_id=current_user.id).first()
    if save:
        save.buildings = '[]'
        save.trees = '[]'
        save.resources = '{"energy":100,"water":100,"waste":0,"food":100}'
        save.population = 100
        save.happiness = 75
        save.sustainability_score = 50
        save.biodiversity = 50
        save.carbon_captured = 0
        db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/ecoworld/build', methods=['POST'])
@login_required
def build_in_ecoworld():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'})
        
        building_id = data.get('building_id')
        x = data.get('x')
        y = data.get('y')
        
        building = Building.query.get(building_id)
        if not building:
            return jsonify({'success': False, 'message': 'Building not found'})
        
        if current_user.token_balance < building.cost:
            return jsonify({'success': False, 'message': 'Not enough tokens'})
        
        if building.unlock_level > current_user.level:
            return jsonify({'success': False, 'message': f'Requires level {building.unlock_level}'})
        
        save = EcoWorldSave.query.filter_by(user_id=current_user.id).first()
        if not save:
            save = EcoWorldSave(user_id=current_user.id)
            db.session.add(save)
        
        buildings_list = json.loads(save.buildings)
        
        for b in buildings_list:
            if abs(b.get('x', 0) - x) < 2 and abs(b.get('y', 0) - y) < 2:
                return jsonify({'success': False, 'message': 'Position occupied'})
        
        new_building = {
            'id': len(buildings_list) + 1,
            'type': building.name,
            'building_id': building.id,
            'x': x,
            'y': y,
            'level': 1,
            'icon': building.icon,
            'category': building.category
        }
        buildings_list.append(new_building)
        save.buildings = json.dumps(buildings_list)
        
        resources = json.loads(save.resources)
        resources['energy'] = max(0, resources.get('energy', 100) + building.energy_production - building.energy_consumption)
        resources['water'] = max(0, resources.get('water', 100) + building.water_production - building.water_consumption)
        resources['waste'] = max(0, resources.get('waste', 0) + building.waste_production)
        resources['food'] = max(0, resources.get('food', 100) + building.food_production)
        save.resources = json.dumps(resources)
        
        save.population += building.population_capacity
        save.sustainability_score -= building.carbon_impact
        save.sustainability_score = max(0, min(100, save.sustainability_score))
        save.happiness += building.happiness_effect
        save.happiness = max(0, min(100, save.happiness))
        save.biodiversity += building.biodiversity_effect
        
        current_user.token_balance -= building.cost
        current_user.eco_score += 10
        save.carbon_captured += abs(building.carbon_impact) * 0.1
        
        if current_user.eco_score >= current_user.level * 100:
            current_user.level += 1
            current_user.token_balance += 100
            save.level = max(save.level, current_user.level)
        
        save.last_played = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tokens': current_user.token_balance,
            'resources': resources,
            'population': save.population,
            'sustainability_score': save.sustainability_score,
            'happiness': save.happiness,
            'carbon_captured': save.carbon_captured,
            'biodiversity': save.biodiversity,
            'user_level': current_user.level,
            'eco_score': current_user.eco_score
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ecoworld/plant-tree', methods=['POST'])
@login_required
def plant_tree():
    try:
        data = request.get_json()
        tree_type = data.get('type', 'oak')
        x = data.get('x')
        y = data.get('y')
        
        tree_costs = {'oak': 50, 'pine': 30, 'maple': 70, 'fruit': 100}
        cost = tree_costs.get(tree_type, 50)
        
        if current_user.token_balance < cost:
            return jsonify({'success': False, 'message': 'Not enough tokens'})
        
        save = EcoWorldSave.query.filter_by(user_id=current_user.id).first()
        if not save:
            return jsonify({'success': False, 'message': 'Save not found'})
        
        trees = json.loads(save.trees)
        
        for tree in trees:
            if tree.get('x') == x and tree.get('y') == y:
                return jsonify({'success': False, 'message': 'Position occupied'})
        
        new_tree = {
            'id': len(trees) + 1,
            'type': tree_type,
            'x': x,
            'y': y,
            'age': 0,
            'health': 100
        }
        trees.append(new_tree)
        save.trees = json.dumps(trees)
        
        carbon_per_tree = {'oak': 5, 'pine': 3, 'maple': 4, 'fruit': 2}
        save.carbon_captured += carbon_per_tree.get(tree_type, 3)
        save.biodiversity = min(100, save.biodiversity + 2)
        save.sustainability_score = min(100, save.sustainability_score + 3)
        current_user.token_balance -= cost
        current_user.eco_score += 5
        
        save.last_played = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tokens': current_user.token_balance,
            'carbon_captured': save.carbon_captured,
            'biodiversity': save.biodiversity,
            'sustainability_score': save.sustainability_score,
            'trees': trees
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ecoworld/save', methods=['POST'])
@login_required
def save_ecoworld():
    try:
        data = request.get_json()
        save = EcoWorldSave.query.filter_by(user_id=current_user.id).first()
        if not save:
            return jsonify({'success': False, 'message': 'Save not found'})
        
        if data and 'city_name' in data:
            save.city_name = data['city_name']
        
        save.last_played = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ecoworld/data')
@login_required
def get_ecoworld_data():
    try:
        save = EcoWorldSave.query.filter_by(user_id=current_user.id).first()
        if not save:
            return jsonify({'success': False, 'message': 'No save found'})
        
        buildings = Building.query.filter(Building.unlock_level <= current_user.level).all()
        
        return jsonify({
            'success': True,
            'city_name': save.city_name,
            'buildings': json.loads(save.buildings),
            'trees': json.loads(save.trees),
            'resources': json.loads(save.resources),
            'population': save.population,
            'happiness': save.happiness,
            'sustainability_score': save.sustainability_score,
            'carbon_captured': save.carbon_captured,
            'biodiversity': save.biodiversity,
            'level': save.level,
            'available_buildings': [{
                'id': b.id,
                'name': b.name,
                'cost': b.cost,
                'icon': b.icon,
                'description': b.description,
                'category': b.category,
                'energy_production': b.energy_production,
                'energy_consumption': b.energy_consumption,
                'water_production': b.water_production,
                'water_consumption': b.water_consumption,
                'food_production': b.food_production,
                'population_capacity': b.population_capacity,
                'unlock_level': b.unlock_level
            } for b in buildings]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/ai-stories')
@login_required
def ai_stories():
    return render_template('ai_stories.html', user=current_user)

@app.route('/api/ai-stories/generate', methods=['POST'])
@login_required
def generate_ai_story():
    try:
        data = request.json
        story_type = data.get('type', 'weekly')
        
        token_costs = {
            'weekly': 50,
            'achievement': 75,
            'educational': 60,
            'future': 100,
            'fable': 80
        }
        
        cost = token_costs.get(story_type, 50)
        
        if current_user.token_balance < cost:
            return jsonify({'success': False, 'message': 'Insufficient tokens'}), 400
        
        current_user.token_balance -= cost
        db.session.commit()
        
        story_data = generate_story_with_gpt(current_user, story_type)
        
        story = AIStory(
            user_id=current_user.id,
            title=story_data['title'],
            type=story_type,
            script=story_data['script'],
            visuals=json.dumps(story_data['visuals']),
            duration=60,
            tokens_earned=50,
            status='generated'
        )
        
        db.session.add(story)
        db.session.commit()
        
        current_user.token_balance += 50
        db.session.commit()
        
        return jsonify({
            'success': True,
            'story': {
                'id': story.id,
                'title': story.title,
                'script': story.script,
                'visuals': json.loads(story.visuals),
                'duration': story.duration
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/ai-stories/play/<int:story_id>')
@login_required
def play_story(story_id):
    story = AIStory.query.get_or_404(story_id)
    if story.user_id != current_user.id:
        return "Unauthorized", 403
    
    save = EcoWorldSave.query.filter_by(user_id=current_user.id).first()
    
    return render_template('story_player.html',
                         story=story,
                         user=current_user,
                         save=save,
                         visuals=story.visuals)

@app.route('/api/ai-stories/export/<int:story_id>/<format>')
@login_required
def export_story(story_id, format):
    try:
        story = AIStory.query.get_or_404(story_id)
        if story.user_id != current_user.id:
            return "Unauthorized", 403
        
        if format == 'video':
            video_path = create_silent_video(story)
            
            return send_file(
                video_path,
                mimetype='video/mp4',
                as_attachment=True,
                download_name=f"eco-story-{story.id}.mp4"
            )
        
        return jsonify({'success': False, 'message': 'Invalid format'}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ai-stories/history')
@login_required
def get_story_history():
    stories = AIStory.query.filter_by(user_id=current_user.id)\
                          .order_by(AIStory.created_at.desc())\
                          .limit(10)\
                          .all()
    
    return jsonify({
        'success': True,
        'stories': [{
            'id': story.id,
            'title': story.title,
            'type': story.type,
            'created_at': story.created_at.strftime('%Y-%m-%d'),
            'duration': story.duration,
            'tokens_earned': story.tokens_earned
        } for story in stories]
    })

def generate_certification_questions(level):
    try:
        print(f"Starting to generate questions for {level} level...")
        
        if level != 'ultra':
            print(f"No quiz required for {level} in new system")
            return []
        
        config = {
            'total_questions': 40,
            'hard_questions': 25,
            'medium_questions': 10,
            'easy_questions': 5,
            'topics': [
                'Advanced Climate Science',
                'Carbon Capture Technology',
                'International Climate Agreements',
                'Sustainable Development Goals',
                'Green Finance and Investments',
                'Climate Justice and Equity',
                'Biodiversity Conservation',
                'Sustainable Urban Planning',
                'Renewable Energy Grid Integration',
                'Climate Adaptation Strategies',
                'Circular Economy Models',
                'Environmental Policy Analysis',
                'Climate Risk Assessment',
                'Sustainable Agriculture Innovation',
                'Ocean Conservation Science'
            ]
        }
        
        print(f"Generating {config['total_questions']} questions for Ultra Legend...")
        
        all_questions = []
        
        batches = [
            {'count': 10, 'difficulty': 'hard', 'label': 'Batch 1 - Hard'},
            {'count': 10, 'difficulty': 'hard', 'label': 'Batch 2 - Hard'},
            {'count': 5, 'difficulty': 'hard', 'label': 'Batch 3 - Hard'},
            {'count': 10, 'difficulty': 'medium', 'label': 'Batch 4 - Medium'},
            {'count': 5, 'difficulty': 'easy', 'label': 'Batch 5 - Easy'}
        ]
        
        for batch_idx, batch in enumerate(batches):
            print(f"\nGenerating {batch['label']} ({batch['count']} questions)...")
            
            try:
                prompt = f"""Generate exactly {batch['count']} {batch['difficulty']}-level multiple-choice questions about sustainability.
                
                Return ONLY a valid JSON array. No markdown, no explanations.

                TOPICS: {', '.join(config['topics'][batch_idx*3:batch_idx*3+3]) if batch_idx*3 < len(config['topics']) else ', '.join(config['topics'][-3:])}

                FORMAT EACH QUESTION AS:
                {{
                    "question": "Question text?",
                    "options": ["A", "B", "C", "D"],
                    "correct": 0,
                    "difficulty": "{batch['difficulty']}",
                    "category": "Specific Topic",
                    "explanation": "Brief explanation."
                }}

                RULES:
                1. Make questions challenging and academic
                2. Ensure options are plausible
                3. Return ONLY the JSON array
                4. Difficulty must be "{batch['difficulty']}"
                """
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You output ONLY valid JSON arrays. Escape quotes with backslash. No other text."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500,
                )
                
                response_text = response.choices[0].message.content.strip()
                print(f"Batch {batch_idx+1} response received ({len(response_text)} chars)")
                
                import re
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                json_match = re.search(r'(\[\s*\{.*\}\s*\])', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
                
                batch_questions = json.loads(response_text)
                print(f"Successfully parsed {len(batch_questions)} questions from batch {batch_idx+1}")
                
                if len(batch_questions) != batch['count']:
                    print(f"Warning: Expected {batch['count']} questions, got {len(batch_questions)}")
                
                all_questions.extend(batch_questions)
                
                import time
                if batch_idx < len(batches) - 1:
                    time.sleep(2)
                    
            except Exception as batch_error:
                print(f"Error in batch {batch_idx+1}: {str(batch_error)}")
                print(f"Response preview: {response_text[:200] if 'response_text' in locals() else 'No response'}")
                continue
        
        print(f"\nTotal questions generated: {len(all_questions)}")
        
        if len(all_questions) < config['total_questions']:
            print(f"Need {config['total_questions'] - len(all_questions)} more questions")
            try:
                supplemental_count = config['total_questions'] - len(all_questions)
                print(f"Generating supplemental batch of {supplemental_count} questions...")
                
                supplemental_prompt = f"Generate {supplemental_count} mixed-difficulty questions about sustainability. Return JSON array."
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Output valid JSON only."},
                        {"role": "user", "content": supplemental_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000,
                )
                
                supplemental_text = response.choices[0].message.content.strip()
                json_match = re.search(r'(\[\s*\{.*\}\s*\])', supplemental_text, re.DOTALL)
                if json_match:
                    supplemental_questions = json.loads(json_match.group(1))
                    all_questions.extend(supplemental_questions[:supplemental_count])
                    print(f"Added {len(supplemental_questions[:supplemental_count])} supplemental questions")
            except:
                print("Supplemental generation failed")
        
        if len(all_questions) < config['total_questions']:
            print(f"Only have {len(all_questions)} questions, need {config['total_questions']}")
            hardcoded = get_simple_hardcoded_questions()
            needed = config['total_questions'] - len(all_questions)
            all_questions.extend(hardcoded[:needed])
            print(f"Added {min(needed, len(hardcoded))} hardcoded questions")
        
        saved_questions = []
        for i, q in enumerate(all_questions[:config['total_questions']]):
            if not isinstance(q, dict) or 'question' not in q or 'options' not in q:
                print(f"Skipping invalid question {i}")
                continue
            
            import hashlib
            question_hash = hashlib.sha256(
                f"{q['question']}ultra{q.get('difficulty','medium')}{i}".encode()
            ).hexdigest()
            
            existing = CertificationQuestion.query.filter_by(
                question_hash=question_hash
            ).first()
            
            if not existing:
                options_data = {
                    'options': q['options'],
                    'explanation': q.get('explanation', 'Correct based on sustainability principles.')
                }
                
                question = CertificationQuestion(
                    certification_type='sustainability',
                    level='ultra',
                    question_hash=question_hash,
                    question_text=q['question'][:500],
                    options=json.dumps(options_data),
                    correct_answer=q.get('correct', 0),
                    difficulty=q.get('difficulty', 'medium'),
                    category=q.get('category', 'Sustainability'),
                    ai_generated=True
                )
                db.session.add(question)
                saved_questions.append(question)
        
        db.session.commit()
        print(f"Saved {len(saved_questions)} new questions for Ultra Legend")
        return saved_questions
        
    except Exception as e:
        print(f"Error generating questions for Ultra Legend: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def get_simple_hardcoded_questions():
    return [
        {
            "question": "What is the primary goal of the Paris Agreement?",
            "options": [
                "Limit global warming to well below 2°C above pre-industrial levels",
                "Eliminate all fossil fuel use by 2050",
                "Achieve zero deforestation by 2030",
                "Reduce plastic waste by 50% by 2030"
            ],
            "correct": 0,
            "difficulty": "medium",
            "category": "International Climate Agreements",
            "explanation": "The Paris Agreement aims to limit global temperature increase to well below 2°C, preferably to 1.5°C."
        },
        {
            "question": "Which sector is the largest contributor to global greenhouse gas emissions?",
            "options": [
                "Energy production",
                "Agriculture",
                "Transportation",
                "Industry"
            ],
            "correct": 0,
            "difficulty": "easy",
            "category": "Advanced Climate Science",
            "explanation": "Energy production, primarily from burning fossil fuels, accounts for about 73% of global greenhouse gas emissions."
        },
        {
            "question": "What does ESG stand for in sustainable investing?",
            "options": [
                "Environmental, Social, and Governance",
                "Energy, Sustainability, and Growth",
                "Eco-friendly, Social, and Green",
                "Emission, Safety, and Governance"
            ],
            "correct": 0,
            "difficulty": "easy",
            "category": "Green Finance and Investments",
            "explanation": "ESG refers to Environmental, Social, and Governance factors used to evaluate corporate behavior and future financial performance."
        },
        {
            "question": "Which UN Sustainable Development Goal focuses specifically on climate action?",
            "options": [
                "SDG 13",
                "SDG 7",
                "SDG 11",
                "SDG 15"
            ],
            "correct": 0,
            "difficulty": "medium",
            "category": "Sustainable Development Goals",
            "explanation": "SDG 13 is 'Climate Action' which calls for urgent action to combat climate change and its impacts."
        },
        {
            "question": "What is carbon sequestration?",
            "options": [
                "The process of capturing and storing atmospheric carbon dioxide",
                "The trading of carbon credits between countries",
                "The reduction of carbon emissions from factories",
                "The measurement of carbon footprint"
            ],
            "correct": 0,
            "difficulty": "medium",
            "category": "Carbon Capture Technology",
            "explanation": "Carbon sequestration involves capturing carbon dioxide from the atmosphere and storing it in geological formations, oceans, or terrestrial ecosystems."
        }
    ]

@app.route('/test-openai')
def test_openai():
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'OpenAI is working' if you can read this."}
            ],
            max_tokens=10
        )
        return jsonify({
            'success': True,
            'message': response.choices[0].message.content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'note': 'Make sure you have a valid OpenAI API key'
        })

@app.route('/clear-bad-questions')
@login_required
def clear_bad_questions():
    try:
        bad_questions = CertificationQuestion.query.filter(
            CertificationQuestion.question_text.like('%Variation%')
        ).all()
        
        count = len(bad_questions)
        for question in bad_questions:
            db.session.delete(question)
        
        db.session.commit()
        
        for level in ['bronze', 'silver', 'gold', 'platinum']:
            questions = generate_certification_questions(level)
            print(f"Generated {len(questions)} questions for {level} level")
        
        return jsonify({
            'success': True,
            'message': f'Cleared {count} bad questions and regenerated all certification questions'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/carbon-dashboard')
@login_required
def carbon_dashboard():
    flight_data = {}
    if 'flight_booking_data' in session:
        try:
            flight_data = json.loads(session.get('flight_booking_data', '{}'))
        except:
            flight_data = {}
    
    immigration_completed = check_immigration_status()
    
    return render_template('carbon_dashboard.html', 
                         user=current_user,
                         immigration_completed=immigration_completed,
                         flight_data=flight_data)

def get_country_from_airport_code(airport_code):
    airport_countries = {
        'SIN': 'Singapore',
        'HKG': 'Hong Kong SAR, China',
        'JFK': 'United States',
        'LHR': 'United Kingdom',
        'CDG': 'France',
        'NRT': 'Japan',
        'SYD': 'Australia',
        'DXB': 'United Arab Emirates',
        'BOM': 'India',
        'DFW': 'United States'
    }
    return airport_countries.get(airport_code, 'Unknown')

@app.route('/api/carbon/calculate', methods=['POST'])
@login_required
def calculate_carbon():
    data = request.json
    responses = data.get('responses', {})
    
    try:
        prompt = f"""
        Analyze this user's carbon footprint based on their lifestyle choices:
        
        Transportation Habits:
        - {responses.get('step1', 'car|gasoline|20')}
        
        Home Energy Usage:
        - {responses.get('step2', 'average|grid|apartment')}
        
        Dietary Choices:
        - {responses.get('step3', 'meat_heavy|high_waste')}
        
        Consumption Patterns:
        - {responses.get('step4', 'frequent|new|electronics_heavy')}
        
        Travel Frequency:
        - {responses.get('step5', '0')} flights per year
        
        Calculate an accurate carbon footprint in kg CO2 per year.
        
        Return a JSON object with this exact structure:
        {{
            "total_co2": number,
            "daily_budget": number,
            "breakdown": {{
                "transportation": number,
                "home": number,
                "food": number,
                "consumption": number
            }},
            "suggestions": [
                "First personalized recommendation",
                "Second actionable suggestion", 
                "Third improvement tip"
            ]
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert carbon footprint analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        result = json.loads(response.choices[0].message.content)
        
        if result['total_co2'] <= 0:
            result['total_co2'] = 12000
            result['daily_budget'] = 15.0
        
        carbon_footprint = CarbonFootprint.query.filter_by(user_id=current_user.id).first()
        if not carbon_footprint:
            carbon_footprint = CarbonFootprint(user_id=current_user.id)
            db.session.add(carbon_footprint)
        
        carbon_footprint.total_co2 = result['total_co2']
        carbon_footprint.daily_budget = result['daily_budget']
        carbon_footprint.categories = json.dumps(result['breakdown'])
        
        current_user.eco_score += 50
        
        action = CarbonAction(
            user_id=current_user.id,
            action_type='carbon_calculator',
            co2_saved=0,
            description='Completed carbon footprint analysis'
        )
        db.session.add(action)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': result,
            'eco_score': current_user.eco_score
        })
        
    except Exception as e:
        print(f"Error calculating carbon with AI: {e}")
        return jsonify({
            'success': True,
            'data': {
                'total_co2': 12500,
                'daily_budget': 15.0,
                'breakdown': {
                    'transportation': 4500,
                    'home': 3800,
                    'food': 3200,
                    'consumption': 1000
                },
                'suggestions': [
                    "Consider public transport 3 days a week to reduce transportation emissions",
                    "Switch to LED bulbs and reduce thermostat by 2°C for home energy savings",
                    "Try meat-free Mondays to lower food-related carbon footprint"
                ]
            },
            'eco_score': current_user.eco_score + 50
        })

@app.route('/api/carbon/log-action', methods=['POST'])
@login_required
def log_carbon_action():
    data = request.json
    action_type = data.get('type')
    co2_saved = data.get('co2_saved', 0)
    description = data.get('description', '')
    
    try:
        if not description and action_type:
            prompt = f"""
            Create a brief, descriptive title for this eco-action: {action_type}
            Saved CO2: {co2_saved} kg
            Return just the description text.
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an eco-action logger."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            description = response.choices[0].message.content.strip()
    except:
        descriptions = {
            'bike': f'Biked to work instead of driving, saving {co2_saved}kg CO₂',
            'recycle': f'Properly recycled materials, saving {co2_saved}kg CO₂',
            'vegetarian': f'Meat-free day, reducing food emissions by {co2_saved}kg CO₂',
            'public': f'Used public transport, avoiding {co2_saved}kg CO₂ emissions'
        }
        description = descriptions.get(action_type, f'Eco-action saved {co2_saved}kg CO₂')
    
    action = CarbonAction(
        user_id=current_user.id,
        action_type=action_type,
        co2_saved=co2_saved,
        description=description
    )
    
    db.session.add(action)
    
    tokens_earned = max(5, int(co2_saved))
    current_user.token_balance += tokens_earned
    current_user.eco_score += 10
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'tokens_earned': tokens_earned,
        'token_balance': current_user.token_balance,
        'eco_score': current_user.eco_score,
        'description': description
    })

@app.route('/api/carbon/get-dashboard-data')
@login_required
def get_carbon_dashboard_data():
    try:
        carbon_footprint = CarbonFootprint.query.filter_by(user_id=current_user.id).first()
        actions = CarbonAction.query.filter_by(user_id=current_user.id).order_by(CarbonAction.created_at.desc()).limit(10).all()
        quests = AviationQuest.query.filter_by(user_id=current_user.id).order_by(AviationQuest.start_time.desc()).limit(5).all()
        
        cert = Certification.query.filter_by(user_id=current_user.id).order_by(Certification.earned_at.desc()).first()
        
        insights = []
        try:
            if actions:
                prompt = f"""
                Based on these recent eco-actions by {current_user.username}:
                {[f"{a.description} ({a.co2_saved}kg)" for a in actions[:3]]}
                
                Generate 2-3 brief, encouraging insights about their progress.
                Return as a JSON array of strings.
                """
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an encouraging sustainability coach."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                
                insights = json.loads(response.choices[0].message.content)
        except:
            insights = ["Keep up the great work on your sustainability journey!", "Every small action makes a difference for our planet."]
        
        dashboard_data = {
            'carbon_footprint': {
                'total_co2': carbon_footprint.total_co2 if carbon_footprint else 0,
                'daily_budget': carbon_footprint.daily_budget if carbon_footprint else 15.0,
                'breakdown': json.loads(carbon_footprint.categories) if carbon_footprint and carbon_footprint.categories else {}
            } if carbon_footprint else None,
            'recent_actions': [{
                'type': action.action_type,
                'co2_saved': action.co2_saved,
                'description': action.description,
                'created_at': action.created_at.strftime('%Y-%m-%d %H:%M')
            } for action in actions],
            'recent_quests': [{
                'id': quest.id,
                'departure': quest.departure_airport,
                'arrival': quest.arrival_airport,
                'airline': quest.airline,
                'status': quest.status,
                'tokens_earned': quest.tokens_earned,
                'co2_offset': quest.co2_offset,
                'start_time': quest.start_time.strftime('%Y-%m-%d %H:%M') if quest.start_time else None
            } for quest in quests],
            'certification': {
                'level': cert.level if cert else 'none',
                'title': cert.title if cert else 'No certification',
                'points': cert.user_points if cert else 0,
                'earned_at': cert.earned_at.strftime('%Y-%m-%d') if cert else None,
                'certificate_id': cert.certificate_id if cert else None
            } if cert else None,
            'user_stats': {
                'eco_score': current_user.eco_score,
                'token_balance': current_user.token_balance,
                'avatar_level': current_user.avatar_level
            },
            'insights': insights
        }
        
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
        
    except Exception as e:
        print(f"Error in get_carbon_dashboard_data: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error loading dashboard data'
        }), 500

@app.route('/api/carbon/quick-actions', methods=['POST'])
@login_required
def quick_carbon_actions():
    data = request.json
    action_type = data.get('type', 'suggestion')
    
    try:
        if action_type == 'suggestion':
            prompt = f"""
            Suggest a quick, easy eco-action for {current_user.username} based on their time availability.
            Consider actions that can be done in 5-30 minutes.
            Return a JSON object with: {{"action": "description", "co2_saved": number, "difficulty": "easy/medium/hard"}}
            """

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a quick-action eco-coach. Suggest simple, impactful environmental actions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            suggestion = json.loads(response.choices[0].message.content)
            
            return jsonify({
                'success': True,
                'suggestion': suggestion
            })
            
    except Exception as e:
        print(f"Error generating quick action: {e}")
        return jsonify({
            'success': True,
            'suggestion': {
                'action': 'Turn off unused lights and electronics for 1 hour',
                'co2_saved': 0.5,
                'difficulty': 'easy'
            }
        })

@app.route('/api/eco-action', methods=['POST'])
@login_required
def log_eco_action():
    try:
        data = request.get_json()
        action = EcoAction(
            user_id=current_user.id,
            action_type=data.get('type', 'unknown'),
            co2_saved=data.get('co2_saved', 0),
            tokens_earned=data.get('tokens', 0)
        )
        
        current_user.eco_score += 10
        current_user.token_balance += data.get('tokens', 0)
        
        db.session.add(action)
        db.session.commit()
        
        return jsonify({'success': True, 'tokens': current_user.token_balance, 'eco_score': current_user.eco_score})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/avatar/save', methods=['POST'])
@login_required
def save_avatar():
    try:
        data = request.get_json()
        total_cost = data.get('cost', 0)
        
        if current_user.token_balance < total_cost:
            return jsonify({'success': False, 'message': 'Insufficient tokens'})
        
        current_user.avatar_skin = data.get('skin', current_user.avatar_skin)
        current_user.avatar_hair = data.get('hair', current_user.avatar_hair)
        current_user.avatar_outfit = data.get('outfit', current_user.avatar_outfit)
        current_user.avatar_aura = data.get('aura', current_user.avatar_aura)
        current_user.avatar_accessories = json.dumps(data.get('accessories', []))
        current_user.token_balance -= total_cost
        
        xp_gain = total_cost * 2
        current_user.avatar_xp += xp_gain
        
        level_up = False
        while current_user.avatar_xp >= current_user.avatar_level * 100:
            current_user.avatar_xp -= current_user.avatar_level * 100
            current_user.avatar_level += 1
            current_user.token_balance += 50
            level_up = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tokens': current_user.token_balance,
            'level': current_user.avatar_level,
            'xp': current_user.avatar_xp,
            'level_up': level_up
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/avatar/data')
@login_required
def avatar_data():
    try:
        accessories = json.loads(current_user.avatar_accessories) if current_user.avatar_accessories else []
        return jsonify({
            'skin': current_user.avatar_skin,
            'hair': current_user.avatar_hair,
            'outfit': current_user.avatar_outfit,
            'aura': current_user.avatar_aura,
            'accessories': accessories,
            'level': current_user.avatar_level,
            'xp': current_user.avatar_xp,
            'tokens': current_user.token_balance
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/avatar/unlock', methods=['POST'])
@login_required
def unlock_avatar_style():
    try:
        data = request.get_json()
        style_type = data.get('type')
        style_id = data.get('id')
        
        unlocked = json.loads(current_user.unlocked_styles or '[]')
        unlock_key = f"{style_type}_{style_id}"
        
        if unlock_key not in unlocked:
            unlocked.append(unlock_key)
            current_user.unlocked_styles = json.dumps(unlocked)
            db.session.commit()
            
        return jsonify({'success': True, 'unlocked': unlocked})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/music/available')
def get_available_music():
    static_path = os.path.join(os.path.dirname(__file__), 'static')
    
    music_files = {
        'heroic': [],
        'unaccomplished': []
    }
    for i in range(1, 4):
        if os.path.exists(os.path.join(static_path, f'h{i}.mp3')):
            music_files['heroic'].append(f'h{i}.mp3')
    for i in range(1, 4):
        if os.path.exists(os.path.join(static_path, f'u{i}.mp3')):
            music_files['unaccomplished'].append(f'u{i}.mp3')
    
    return jsonify({
        'success': True,
        'music_files': music_files,
        'static_path': static_path
    })

@app.route('/static/<filename>')
def serve_static_file(filename):
    static_path = os.path.join(os.path.dirname(__file__), 'static')
    file_path = os.path.join(static_path, filename)
    
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        return "File not found", 404

@app.route('/api/certification/requirements', methods=['GET'])
@login_required
def get_certification_requirements():
    try:
        total_points = calculate_user_points(current_user.id)
        
        requirements = [
            {
                'level': 'bronze',
                'title': 'Bronze ECODIST',
                'points_required': 1000,
                'description': 'Basic sustainability knowledge',
                'completed': total_points >= 1000,
                'quiz_available': total_points >= 1000,
                'quiz_info': '20 questions (15 to pass), 5 hard questions, 24h cooldown if failed'
            },
            {
                'level': 'silver',
                'title': 'Silver ECOGUARDIAN',
                'points_required': 5000,
                'description': 'Intermediate sustainability expertise',
                'completed': total_points >= 5000,
                'quiz_available': total_points >= 5000,
                'quiz_info': '25 questions (18 to pass), 8 hard questions, 24h cooldown if failed'
            },
            {
                'level': 'gold',
                'title': 'Gold ECOMAGE',
                'points_required': 15000,
                'description': 'Advanced sustainability mastery',
                'completed': total_points >= 15000,
                'quiz_available': total_points >= 15000,
                'quiz_info': '30 questions (22 to pass), 10 hard questions, 24h cooldown if failed'
            },
            {
                'level': 'platinum',
                'title': 'Platinum ECOLEGEND',
                'points_required': 50000,
                'description': 'Elite sustainability leadership',
                'completed': total_points >= 50000,
                'quiz_available': total_points >= 50000,
                'quiz_info': '35 questions (26 to pass), 15 hard questions, 24h cooldown if failed'
            }
        ]
        
        for req in requirements:
            eligibility = CertificationEligibility.query.filter_by(
                user_id=current_user.id,
                level=req['level']
            ).first()
            
            if not eligibility:
                eligibility = CertificationEligibility(
                    user_id=current_user.id,
                    level=req['level'],
                    points_required=req['points_required'],
                    user_points=total_points,
                    eligible=req['quiz_available']
                )
                db.session.add(eligibility)
            else:
                eligibility.user_points = total_points
                eligibility.eligible = req['quiz_available']
                eligibility.last_checked = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'requirements': requirements,
            'user_points': total_points
        })
        
    except Exception as e:
        print(f"Error getting requirements: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/certification/user-progress', methods=['GET'])
@login_required
def get_user_progress():
    try:
        total_points = calculate_user_points(current_user.id)
        
        cert_count = Certification.query.filter_by(user_id=current_user.id).count()
        
        eco_score = current_user.eco_score
        
        streak_days = 7
        
        eligibility = {
            'bronze': total_points >= 1000,
            'silver': total_points >= 5000,
            'gold': total_points >= 15000,
            'platinum': total_points >= 50000
        }
        
        can_retake = {}
        for level in ['bronze', 'silver', 'gold', 'platinum']:
            last_test = CertificationTest.query.filter_by(
                user_id=current_user.id,
                level=level
            ).order_by(CertificationTest.created_at.desc()).first()
            
            if last_test and last_test.passed == False:
                time_since_last_attempt = datetime.utcnow() - last_test.last_attempt
                can_retake[level] = time_since_last_attempt.total_seconds() >= 86400
            else:
                can_retake[level] = True
        
        return jsonify({
            'success': True,
            'total_points': total_points,
            'certifications_count': cert_count,
            'eco_score': eco_score,
            'streak_days': streak_days,
            'eligible_for': eligibility,
            'can_retake': can_retake
        })
        
    except Exception as e:
        print(f"Error getting user progress: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/certification/start-quiz/<level>', methods=['GET'])
@login_required
def start_certification_quiz(level):
    try:
        valid_levels = ['bronze', 'silver', 'gold', 'ultra']
        if level not in valid_levels:
            return jsonify({
                'success': False,
                'message': 'Invalid certification level'
            })
        
        existing_cert = Certification.query.filter_by(
            user_id=current_user.id,
            level=level
        ).first()
        
        if existing_cert:
            return jsonify({
                'success': False,
                'message': f'You already have {level} certification!'
            })
        
        if level != 'ultra':
            return jsonify({
                'success': False,
                'message': f'{level.capitalize()} certification is earned through points, not a quiz'
            })
        
        last_test = CertificationTest.query.filter_by(
            user_id=current_user.id,
            level='ultra',
            passed=False
        ).order_by(CertificationTest.created_at.desc()).first()
        
        if last_test:
            time_since_last_attempt = datetime.utcnow() - last_test.last_attempt
            if time_since_last_attempt.total_seconds() < 86400:
                hours_left = (86400 - time_since_last_attempt.total_seconds()) / 3600
                return jsonify({
                    'success': False,
                    'message': f'You must wait {hours_left:.1f} hours before retaking the Ultra Legend test.'
                })
        
        questions = get_certification_questions(level)
        
        if not questions:
            questions = generate_certification_questions(level)
        
        questions = [q for q in questions if "Variation" not in q.question_text]
        
        if not questions or len(questions) < 40:
            return jsonify({
                'success': False,
                'message': 'Not enough questions available. Please try again later.'
            })
        
        questions = questions[:40]
        
        test = CertificationTest(
            user_id=current_user.id,
            certification_type='sustainability',
            level=level,
            question_ids=json.dumps([q.id for q in questions]),
            attempts_count=CertificationTest.query.filter_by(
                user_id=current_user.id,
                level=level
            ).count() + 1,
            last_attempt=datetime.utcnow()
        )
        
        db.session.add(test)
        db.session.commit()
        
        formatted_questions = []
        for question in questions:
            try:
                options_data = json.loads(question.options)
                if isinstance(options_data, dict) and 'options' in options_data:
                    options_list = options_data['options']
                else:
                    options_list = options_data
            except:
                options_list = []
            
            formatted_questions.append({
                'id': question.id,
                'question': question.question_text,
                'options': options_list,
                'difficulty': question.difficulty,
                'category': question.category
            })
        
        return jsonify({
            'success': True,
            'questions': formatted_questions,
            'quiz_id': test.id,
            'total_questions': len(questions),
            'level': level,
            'is_ultra': level == 'ultra'
        })
        
    except Exception as e:
        print(f"Error starting quiz: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/passport')
@login_required
def passport_page():
    from datetime import timedelta
    
    passport_country = session.get('passport_country', 'India')
    
    supported_passports = ['India', 'United States', 'Japan', 'Germany', 'United Arab Emirates', 'Singapore']
    
    if passport_country not in supported_passports:
        flash('This passport is not currently supported by Carbon Immigration.', 'error')
        return redirect(url_for('carbon_dashboard'))
    
    return render_template('passport.html', 
                         user=current_user,
                         passport_country=passport_country,
                         timedelta=timedelta)

@app.route('/border-initiation')
@login_required
def border_initiation():
    if 'flight_booking_data' not in session:
        flash('Please book a flight first before proceeding to immigration.', 'warning')
        return redirect(url_for('carbon_dashboard'))
    
    username = current_user.username
    email = current_user.email
    
    destination_country = 'Singapore'
    
    flight_data = json.loads(session['flight_booking_data'])
    if flight_data and flight_data.get('arrival_country'):
        destination_country = flight_data.get('arrival_country')
    
    now = datetime.now()
    
    template_vars = {
        'name': username,
        'email': email,
        'username': username,
        'destination_country': destination_country,
        'now': now,
        'datetime': datetime,
        'current_date': now.strftime('%y%m%d'),
        'current_time': now.strftime('%H%M%S'),
        'name_escaped': json.dumps(username),
        'username_escaped': json.dumps(username),
        'email_escaped': json.dumps(email),
        'destination_escaped': json.dumps(destination_country)
    }
    
    return render_template('immigration_clearance.html', **template_vars)

def check_immigration_status():
    return session.get('immigration_cleared', False)

@app.route('/api/immigration/complete', methods=['POST'])
@login_required
def complete_immigration():
    try:
        session['immigration_cleared'] = True
        session['immigration_completed_at'] = datetime.utcnow().isoformat()
        
        action = EcoAction(
            user_id=current_user.id,
            action_type='immigration_cleared',
            co2_saved=5.0,
            tokens_earned=50,
            created_at=datetime.utcnow()
        )
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Immigration clearance completed',
            'redirect': '/carbon-dashboard'
        })
    except Exception as e:
        print(f"Error completing immigration: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route("/paperwork-for-humans")
def paperwork_for_humans():
    return redirect("/border-initiation")

@app.route('/greentoken')
@login_required
def greentoken_realistic_dashboard():
    return render_template('greentoken_dashboard.html', user=current_user)

@app.route('/api/greentoken/realistic-data')
@login_required
def get_realistic_dashboard_data():
    try:
        if CryptoMarket.query.count() == 0:
            init_greentoken_market()
        
        investments = CryptoInvestment.query.filter_by(
            user_id=current_user.id, 
            status='active'
        ).all()
        
        market_data = CryptoMarket.query.all()
        
        flight_credits = FlightCredit.query.filter_by(
            user_id=current_user.id
        ).filter(
            FlightCredit.remaining_flights > 0
        ).all()
        
        transactions = GreenTokenTransaction.query.filter_by(
            user_id=current_user.id
        ).order_by(GreenTokenTransaction.created_at.desc()).limit(10).all()
        
        total_invested = sum(inv.amount_invested for inv in investments)
        total_current_value = sum(inv.crypto_amount * inv.current_price for inv in investments)
        total_profit_loss = total_current_value - total_invested
        
        daily_return = random.uniform(-2, 5) if investments else 0
        
        annual_return = daily_return * 365 if daily_return > 0 else 0
        volatility = random.uniform(5, 25) if investments else 0
        sharpe_ratio = (annual_return / volatility) if volatility > 0 else 0
        
        enhanced_market_data = []
        for crypto in market_data:
            hourly_change = random.uniform(-5, 10)
            crypto.hourly_change = hourly_change
            crypto.current_price = crypto.current_price * (1 + hourly_change / 100)
            
            enhanced_market_data.append({
                'symbol': crypto.symbol,
                'name': crypto.name,
                'current_price': crypto.current_price,
                'hourly_change': hourly_change,
                'daily_change': crypto.daily_change,
                'market_cap': crypto.market_cap,
                'volume': crypto.volume,
                'description': crypto.description,
                'volatility': crypto.volatility
            })
        
        db.session.commit()
        
        investments_data = []
        for inv in investments:
            current_value = inv.crypto_amount * inv.current_price
            profit_loss = current_value - inv.amount_invested
            return_rate = ((current_value - inv.amount_invested) / inv.amount_invested * 100)
            
            days_held = (datetime.utcnow() - inv.investment_date).days if inv.investment_date else 0
            
            investments_data.append({
                'id': inv.id,
                'symbol': inv.crypto_symbol,
                'name': inv.crypto_name,
                'amount_invested': inv.amount_invested,
                'crypto_amount': inv.crypto_amount,
                'purchase_price': inv.purchase_price,
                'current_price': inv.current_price,
                'profit_loss': profit_loss,
                'hourly_change': inv.hourly_change,
                'current_value': current_value,
                'return_rate': return_rate,
                'days_held': days_held,
                'maturity_date': inv.maturity_date.strftime('%Y-%m-%d %H:%M:%S') if inv.maturity_date else None,
                'investment_date': inv.investment_date.strftime('%Y-%m-%d %H:%M:%S') if inv.investment_date else None
            })
        
        return jsonify({
            'success': True,
            'balance': current_user.token_balance,
            'investments': investments_data,
            'market_data': enhanced_market_data,
            'flight_credits': [{
                'id': fc.id,
                'tokens_spent': fc.tokens_spent,
                'flights_earned': fc.flights_earned,
                'remaining_flights': fc.remaining_flights,
                'conversion_rate': fc.conversion_rate,
                'valid_until': fc.valid_until.strftime('%Y-%m-%d') if fc.valid_until else None,
                'created_at': fc.created_at.strftime('%Y-%m-%d')
            } for fc in flight_credits],
            'recent_transactions': [{
                'type': t.transaction_type,
                'amount': t.amount,
                'crypto_symbol': t.crypto_symbol,
                'description': t.description,
                'created_at': t.created_at.strftime('%Y-%m-%d %H:%M')
            } for t in transactions],
            'portfolio_metrics': {
                'total_value': total_current_value,
                'total_invested': total_invested,
                'total_profit_loss': total_profit_loss,
                'daily_return': daily_return,
                'risk_level': 'LOW' if total_current_value < 1000 else 'MEDIUM' if total_current_value < 5000 else 'HIGH',
                'sharpe_ratio': round(sharpe_ratio, 2),
                'annual_return': round(annual_return, 2),
                'volatility': round(volatility, 2),
                'max_drawdown': random.uniform(5, 20) if investments else 0,
                'win_rate': random.uniform(50, 90) if investments else 0
            },
            'available_flights': sum(fc.remaining_flights for fc in flight_credits)
        })
        
    except Exception as e:
        print(f"Realistic dashboard data error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def calculate_risk_level(investments):
    if not investments:
        return 'LOW'
    
    total_value = sum(inv.crypto_amount * inv.current_price for inv in investments)
    if total_value < 1000:
        return 'LOW'
    elif total_value < 5000:
        return 'MEDIUM'
    else:
        return 'HIGH'

def calculate_sharpe_ratio(investments):
    if not investments:
        return 0.0
    
    total_return = sum((inv.current_price - inv.purchase_price) / inv.purchase_price * 100 for inv in investments) / len(investments)
    volatility = random.uniform(5, 25)
    return round(total_return / volatility, 2) if volatility > 0 else 0

def calculate_portfolio_volatility(investments):
    return random.uniform(5, 25) if investments else 0

def calculate_max_drawdown(investments):
    return random.uniform(5, 20) if investments else 0

def calculate_win_rate(investments):
    return random.uniform(50, 90) if investments else 0

def calculate_annualized_return(investments):
    if not investments:
        return 0
    daily_return = random.uniform(-2, 5)
    return round(daily_return * 365, 2)

@app.route('/api/greentoken/advanced-invest', methods=['POST'])
@login_required
def advanced_invest():
    try:
        data = request.json
        crypto_symbol = data.get('crypto_symbol')
        amount = float(data.get('amount', 0))
        strategy = data.get('strategy', 'balanced')
        investment_type = data.get('investment_type', 'market')
        
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid investment amount'})
        
        if current_user.token_balance < amount:
            return jsonify({'success': False, 'message': 'Insufficient GreenTokens'})
        crypto_market = CryptoMarket.query.filter_by(symbol=crypto_symbol).first()
        if not crypto_market:
            return jsonify({'success': False, 'message': 'Crypto not found'})
        transaction_fee = amount * 0.005
        net_amount = amount - transaction_fee
        crypto_amount = net_amount / crypto_market.current_price
        if strategy == 'conservative':
            maturity_hours = 2
        elif strategy == 'aggressive':
            maturity_hours = 3
        else:
            maturity_hours = 2.5
        
        maturity_date = datetime.utcnow() + timedelta(hours=maturity_hours)
        investment = CryptoInvestment(
            user_id=current_user.id,
            crypto_symbol=crypto_symbol,
            crypto_name=crypto_market.name,
            amount_invested=amount,
            crypto_amount=crypto_amount,
            purchase_price=crypto_market.current_price,
            current_price=crypto_market.current_price,
            maturity_date=maturity_date,
            hourly_change=crypto_market.hourly_change
        )
        current_user.token_balance -= amount
        transaction = GreenTokenTransaction(
            user_id=current_user.id,
            transaction_type='investment',
            amount=-amount,
            crypto_symbol=crypto_symbol,
            crypto_amount=crypto_amount,
            exchange_rate=crypto_market.current_price,
            description=f'Advanced investment in {crypto_market.name} ({strategy} strategy)',
            status='completed'
        )
        action = EcoAction(
            user_id=current_user.id,
            action_type='advanced_investment',
            co2_saved=amount * 0.1,
            tokens_earned=0,
            created_at=datetime.utcnow()
        )
        
        db.session.add(investment)
        db.session.add(transaction)
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'investment': {
                'id': investment.id,
                'symbol': crypto_symbol,
                'amount_invested': amount,
                'crypto_amount': crypto_amount,
                'purchase_price': crypto_market.current_price,
                'maturity_date': investment.maturity_date.strftime('%Y-%m-%d %H:%M:%S'),
                'strategy': strategy
            },
            'new_balance': current_user.token_balance,
            'transaction_fee': transaction_fee,
            'message': f'Advanced investment successful! Strategy: {strategy}, Matures in {maturity_hours} hours.'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Advanced invest error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/greentoken/limit-order', methods=['POST'])
@login_required
def place_limit_order():
    try:
        data = request.json
        crypto_symbol = data.get('crypto_symbol')
        order_type = data.get('order_type', 'buy')
        limit_price = float(data.get('limit_price', 0))
        amount = float(data.get('amount', 0))
        expiry_hours = int(data.get('expiry_hours', 168))
        
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid amount'})
        
        if limit_price <= 0:
            return jsonify({'success': False, 'message': 'Invalid limit price'})
        
        if order_type == 'buy' and current_user.token_balance < amount:
            return jsonify({'success': False, 'message': 'Insufficient balance for buy order'})
        crypto = CryptoMarket.query.filter_by(symbol=crypto_symbol).first()
        if not crypto:
            return jsonify({'success': False, 'message': 'Crypto not found'})
        
        current_price = crypto.current_price
        if order_type == 'buy' and limit_price > current_price * 1.1:
            return jsonify({'success': False, 'message': 'Buy limit price too high (max 10% above current)'})
        if order_type == 'sell' and limit_price < current_price * 0.9:
            return jsonify({'success': False, 'message': 'Sell limit price too low (min 10% below current)'})

        expiry_date = datetime.utcnow() + timedelta(hours=expiry_hours) if expiry_hours > 0 else None

        if order_type == 'buy':
            current_user.token_balance -= amount
        transaction = GreenTokenTransaction(
            user_id=current_user.id,
            transaction_type=f'limit_order_{order_type}',
            amount=-amount if order_type == 'buy' else amount,
            crypto_symbol=crypto_symbol,
            description=f'Limit {order_type} order for {crypto_symbol} at {limit_price} GT (expires: {expiry_date.strftime("%Y-%m-%d %H:%M") if expiry_date else "GTC"})',
            status='pending'
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'order_id': transaction.id,
            'order_type': order_type,
            'crypto_symbol': crypto_symbol,
            'limit_price': limit_price,
            'amount': amount,
            'expiry_date': expiry_date.strftime('%Y-%m-%d %H:%M:%S') if expiry_date else None,
            'current_price': current_price,
            'new_balance': current_user.token_balance,
            'message': f'Limit {order_type} order placed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Limit order error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def init_greentoken_market():
    default_cryptos = [
        ('ECOG', 'EcoGreen', 'Sustainable blockchain for environmental projects', 5.0, 0.05),
        ('SOLAR', 'SolarCoin', 'Tokenized solar energy production', 2.5, 0.06),
        ('CARB', 'CarbonCredit', 'Digital carbon credit marketplace', 10.0, 0.08),
        ('ECO', 'EcoVerse', 'Native ecosystem token', 1.0, 0.07),
        ('TREE', 'TreeToken', 'Reforestation and forest conservation', 3.0, 0.07),
        ('WIND', 'WindEnergy', 'Wind farm energy tokenization', 4.0, 0.09),
        ('OCEAN', 'OceanClean', 'Ocean cleanup and marine conservation', 1.5, 0.1)
    ]
    
    for symbol, name, desc, price, volatility in default_cryptos:
        existing = CryptoMarket.query.filter_by(symbol=symbol).first()
        if not existing:
            crypto = CryptoMarket(
                symbol=symbol,
                name=name,
                current_price=price,
                hourly_change=random.uniform(-5, 5),
                daily_change=random.uniform(-10, 15),
                market_cap=price * random.uniform(1000000, 50000000),
                volume=random.uniform(100000, 10000000),
                description=desc,
                volatility=volatility
            )
            db.session.add(crypto)
    
    db.session.commit()
    print("Advanced GreenToken market initialized")

@app.route('/api/greentoken/stop-loss', methods=['POST'])
@login_required
def set_stop_loss():
    try:
        data = request.json
        investment_id = data.get('investment_id')
        stop_price = float(data.get('stop_price', 0))
        stop_type = data.get('stop_type', 'percentage')
        
        investment = CryptoInvestment.query.get(investment_id)
        if not investment or investment.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Investment not found'})
        
        if investment.status != 'active':
            return jsonify({'success': False, 'message': 'Investment not active'})
        
        if stop_price <= 0:
            return jsonify({'success': False, 'message': 'Invalid stop price'})
        
        current_price = investment.current_price
        if stop_type == 'percentage':
            percentage = float(data.get('percentage', 15))
            calculated_stop = investment.purchase_price * (1 - percentage / 100)
            stop_price = calculated_stop
        
        if stop_price >= current_price:
            return jsonify({'success': False, 'message': 'Stop price must be below current price'})
        transaction = GreenTokenTransaction(
            user_id=current_user.id,
            transaction_type='stop_loss_set',
            amount=0,
            crypto_symbol=investment.crypto_symbol,
            description=f'Stop loss set for {investment.crypto_symbol} at {stop_price} GT (type: {stop_type})',
            status='pending'
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'investment_id': investment_id,
            'crypto_symbol': investment.crypto_symbol,
            'stop_price': stop_price,
            'stop_type': stop_type,
            'current_price': current_price,
            'purchase_price': investment.purchase_price,
            'potential_loss': ((current_price - stop_price) / current_price * 100),
            'message': f'Stop loss set at {stop_price} GT for {investment.crypto_symbol}'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Stop loss error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/immigration')
@login_required
def immigration_page():
    from datetime import datetime, timedelta
    if 'destination_country' not in session:
        flash('No flight destination selected. Please book a flight first.', 'warning')
        return redirect(url_for('carbon_dashboard'))
    
    passport_country = session.get('passport_country', 'India')
    destination_country = session['destination_country']
    visa_rules = {
        "India": {
            "visa_free": ["Nepal", "Bhutan", "Maldives", "Mauritius"],
            "visa_required": ["United States", "Japan", "Hong Kong SAR, China", "United Kingdom", 
                            "Germany", "France", "Australia", "Singapore", "United Arab Emirates"],
            "eta_required": [],
            "notes": "Indian passport holders require visas for most countries."
        },
        "United States": {
            "visa_free": ["United Kingdom", "Germany", "France", "Japan", "Australia", 
                         "Singapore", "United Arab Emirates"],
            "visa_required": [],
            "eta_required": [],
            "notes": "US passport offers extensive visa-free access."
        },
        "Japan": {
            "visa_free": ["Singapore", "United Kingdom", "Germany", "France", "Australia"],
            "visa_required": [],
            "eta_required": [],
            "notes": "Japanese passport ranks among the most powerful."
        },
        "Germany": {
            "visa_free": ["United States", "United Kingdom", "Japan", "Australia", 
                         "Singapore", "France"],
            "visa_required": [],
            "eta_required": [],
            "notes": "German passport offers extensive visa-free travel."
        },
        "United Arab Emirates": {
            "visa_free": ["Germany", "France", "Singapore"],
            "visa_required": ["United States", "United Kingdom", "Japan", "Australia"],
            "eta_required": [],
            "notes": "UAE passport offers growing visa-free access."
        },
        "Singapore": {
            "visa_free": ["United States", "United Kingdom", "Germany", "Japan", 
                         "Australia", "France", "United Arab Emirates"],
            "visa_required": [],
            "eta_required": [],
            "notes": "Singapore passport is one of the world's most powerful."
        }
    }

    requires_visa = False
    visa_type = "visa_free"
    
    if passport_country in visa_rules:
        if destination_country in visa_rules[passport_country]["visa_required"]:
            requires_visa = True
            visa_type = "visa_required"
        elif destination_country in visa_rules[passport_country]["eta_required"]:
            requires_visa = True
            visa_type = "eta_required"
    
    return render_template('immigration.html',
                         user=current_user,
                         passport_country=passport_country,
                         destination_country=destination_country,
                         requires_visa=requires_visa,
                         visa_type=visa_type,
                         visa_rules=visa_rules.get(passport_country, {}),
                         datetime=datetime,
                         timedelta=timedelta)

@app.route('/process-visa', methods=['POST'])
@login_required
def process_visa():
    passport_country = session.get('passport_country', 'India')
    destination_country = session.get('destination_country', 'Singapore')
    travel_purpose = request.form.get('travel_purpose', 'Tourism')
    duration = request.form.get('duration', '14')
    occupation = request.form.get('occupation', 'Professional')
    visa_number = f"VISA-{random.randint(100000, 999999)}-{datetime.utcnow().strftime('%y%m')}"
    issue_date = datetime.utcnow().strftime('%d %b %Y')
    expiry_date = (datetime.utcnow() + timedelta(days=365)).strftime('%d %b %Y')
    
    visa_data = {
        'visa_number': visa_number,
        'passport_country': passport_country,
        'destination_country': destination_country,
        'holder_name': current_user.username,
        'issue_date': issue_date,
        'expiry_date': expiry_date,
        'purpose': travel_purpose,
        'duration_days': duration,
        'occupation': occupation,
        'status': 'APPROVED',
        'type': 'TOURIST VISA'
    }
    session['visa_data'] = visa_data
    
    return jsonify({'success': True, 'visa': visa_data})

@app.route('/stamp')
@login_required
def stamp_page():
    from datetime import datetime
    
    return render_template('stamp.html', 
                         user=current_user,
                         datetime=datetime)
@app.route('/security-check')
@login_required
def security_check():
    if not session.get('immigration_completed'):
        flash('Please complete immigration first', 'warning')
        return redirect(url_for('carbon_dashboard'))
    
    return render_template('security_check.html')


@app.route('/api/flight/start-flight-after-security', methods=['POST'])
@login_required
def start_flight_after_security():
    try:
        session['security_agreed'] = True
        session['security_cleared'] = True
        flight_data = None
        if 'flight_booking_data' in session:
            flight_data = json.loads(session['flight_booking_data'])
        quest = None
        if flight_data:
            existing_quest = AviationQuest.query.filter_by(
                user_id=current_user.id,
                departure_airport=flight_data.get('departure'),
                arrival_airport=flight_data.get('arrival'),
                status='active'
            ).order_by(AviationQuest.created_at.desc()).first()
            
            if existing_quest:
                quest = existing_quest
            else:
                quest = AviationQuest(
                    user_id=current_user.id,
                    quest_type='carbon_offset_flight',
                    departure_airport=flight_data.get('departure'),
                    arrival_airport=flight_data.get('arrival'),
                    airline=flight_data.get('airline', 'Singapore Airlines'),
                    aircraft=flight_data.get('aircraft', 'A350-900'),
                    seat=flight_data.get('seat', '21C'),
                    gate=flight_data.get('gate', 'A11'),
                    passport_country=session.get('passport_country', 'India'),
                    status='active',
                    start_time=datetime.utcnow()
                )
                airlines = {
                    'Singapore Airlines': 'SQ',
                    'Cathay Pacific': 'CX',
                    'Scoot': 'TR',
                    'American Airlines': 'AA',
                    'British Airways': 'BA',
                    'Emirates': 'EK',
                    'Qatar Airways': 'QR',
                    'Delta': 'DL',
                    'United': 'UA',
                    'Air France': 'AF'
                }
                
                airline_code = airlines.get(flight_data.get('airline'), 'XX')
                quest.flight_number = f"{airline_code}{random.randint(100, 999)}"
                
                db.session.add(quest)
        action = EcoAction(
            user_id=current_user.id,
            action_type='security_cleared',
            co2_saved=2.0,
            tokens_earned=25,
            created_at=datetime.utcnow()
        )
        db.session.add(action)
        current_user.token_balance += 25
        current_user.eco_score += 10
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Security cleared and flight ready',
            'quest_id': quest.id if quest else None,
            'flight_number': quest.flight_number if quest else None,
            'redirect': '/carbon-dashboard?flight_ready=true'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error starting flight after security: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/flight/security-agree', methods=['POST'])
@login_required
def security_agree():
    try:
        session['security_agreed'] = True
        session['security_agreed_at'] = datetime.utcnow().isoformat()
        session['security_cleared'] = True
        action = EcoAction(
            user_id=current_user.id,
            action_type='security_agreed',
            co2_saved=0,
            tokens_earned=10,
            created_at=datetime.utcnow()
        )
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Security declaration accepted',
            'redirect': '/carbon-dashboard?security_cleared=true'
        })
    except Exception as e:
        print(f"Security agree error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/flight/security-disagree', methods=['POST'])
@login_required
def security_disagree():
    try:
        session['security_agreed'] = False
        session['security_declined_at'] = datetime.utcnow().isoformat()
        
        return jsonify({
            'success': True,
            'message': 'Security declaration declined',
            'redirect': '/carbon-dashboard'
        })
    except Exception as e:
        print(f"Security disagree error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/clear-immigration-session', methods=['POST'])
@login_required
def clear_immigration_session():
    try:
        immigration_completed = session.get('immigration_completed')
        session.pop('immigration_status', None)
        session.pop('immigration_completed', None)
        session.pop('requires_visa', None)
        session.pop('visa_data', None)

        if immigration_completed:
            session['immigration_cleared_for_security'] = True
        action = EcoAction(
            user_id=current_user.id,
            action_type='immigration_completed',
            co2_saved=5.0,
            tokens_earned=50,
            created_at=datetime.utcnow()
        )
        db.session.add(action)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Immigration session cleared and ready for security check'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/flight/start-after-checks', methods=['POST'])
@login_required
def start_flight_after_checks():
    try:
        immigration_completed = session.get('immigration_completed')
        security_agreed = session.get('security_agreed')
        
        if not immigration_completed or not security_agreed:
            return jsonify({
                'success': False,
                'message': 'Please complete immigration and security checks first'
            }), 400
        flight_data = json.loads(session.get('flight_booking_data', '{}'))
        
        if not flight_data:
            return jsonify({
                'success': False,
                'message': 'No flight booking found. Please book a flight first.'
            }), 400
        quest = AviationQuest(
            user_id=current_user.id,
            quest_type='carbon_offset_flight',
            departure_airport=flight_data.get('departure'),
            arrival_airport=flight_data.get('arrival'),
            airline=flight_data.get('airline'),
            aircraft=flight_data.get('aircraft'),
            seat=flight_data.get('seat'),
            gate=flight_data.get('gate'),
            passport_country=session.get('passport_country', 'India'),
            status='active',
            start_time=datetime.utcnow()
        )
        airlines = {
            'Singapore Airlines': 'SQ',
            'Cathay Pacific': 'CX',
            'Scoot': 'TR',
            'American Airlines': 'AA',
            'British Airways': 'BA',
            'Emirates': 'EK',
            'Qatar Airways': 'QR',
            'Delta': 'DL',
            'United': 'UA',
            'Air France': 'AF'
        }
        
        airline_code = airlines.get(flight_data.get('airline'), 'XX')
        quest.flight_number = f"{airline_code}{random.randint(100, 999)}"
        
        db.session.add(quest)
        db.session.commit()
        session['current_flight_quest_id'] = quest.id
        
        return jsonify({
            'success': True,
            'quest_id': quest.id,
            'message': 'Flight ready to start',
            'flight_number': quest.flight_number,
            'redirect': '/flight-animation'
        })
        
    except Exception as e:
        print(f"Start flight error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/certification/check-eligibility', methods=['GET'])
@login_required
def check_eligibility():
    try:
        total_points = calculate_user_points(current_user.id)
        existing_certs = Certification.query.filter_by(user_id=current_user.id).all()
        earned_levels = [cert.level for cert in existing_certs]
        requirements = get_certification_requirements_new()
        ultra_test = CertificationTest.query.filter_by(
            user_id=current_user.id,
            level='ultra',
            passed=True
        ).first()
        
        eligibility_data = []
        
        for req in requirements:
            if req['type'] == 'points':
                eligible = total_points >= req['points_required'] and req['level'] not in earned_levels
                has_cert = req['level'] in earned_levels
                
                eligibility_data.append({
                    'level': req['level'],
                    'eligible': eligible,
                    'has_certificate': has_cert,
                    'points_required': req['points_required'],
                    'user_points': total_points,
                    'type': 'points'
                })
            else:
                has_ultra_cert = 'ultra' in earned_levels
                quiz_passed = ultra_test is not None
                
                eligibility_data.append({
                    'level': req['level'],
                    'eligible': True,
                    'has_certificate': has_ultra_cert,
                    'quiz_passed': quiz_passed,
                    'points_required': 0,
                    'user_points': total_points,
                    'type': 'quiz'
                })
        
        return jsonify({
            'success': True,
            'total_points': total_points,
            'earned_certificates': len(existing_certs),
            'eligibility': eligibility_data
        })
        
    except Exception as e:
        print(f"Error checking eligibility: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

def get_certification_requirements_new():
    return [
        {
            'level': 'bronze',
            'title': 'Bronze ECODIST',
            'points_required': 1000,
            'description': 'Basic sustainability foundation',
            'badge_icon': '🥉',
            'color_scheme': '{"primary": "#CD7F32", "secondary": "#FFD700", "bg": "#FFF8DC"}',
            'type': 'points',
            'quiz_questions': 0,
            'passing_score': 0
        },
        {
            'level': 'silver',
            'title': 'Silver ECOGUARDIAN',
            'points_required': 5000,
            'description': 'Intermediate sustainability expertise',
            'badge_icon': '🥈',
            'color_scheme': '{"primary": "#C0C0C0", "secondary": "#E8E8E8", "bg": "#F5F5F5"}',
            'type': 'points',
            'quiz_questions': 0,
            'passing_score': 0
        },
        {
            'level': 'gold',
            'title': 'Gold ECOMAGE',
            'points_required': 15000,
            'description': 'Advanced sustainability mastery',
            'badge_icon': '🥇',
            'color_scheme': '{"primary": "#FFD700", "secondary": "#FFF8DC", "bg": "#FFFACD"}',
            'type': 'points',
            'quiz_questions': 0,
            'passing_score': 0
        },
        {
            'level': 'ultra',
            'title': 'ULTRA LEGEND',
            'points_required': 0,
            'description': 'Ultimate sustainability knowledge champion',
            'badge_icon': '⭐',
            'color_scheme': '{"primary": "#8A2BE2", "secondary": "#9370DB", "bg": "#F8F8FF"}',
            'type': 'quiz',
            'quiz_questions': 40,
            'passing_score': 80
        }
    ]

@app.route('/api/certification/check-points-certificates', methods=['POST'])
@login_required
def check_points_certificates():
    try:
        total_points = calculate_user_points(current_user.id)
        existing_certs = Certification.query.filter_by(user_id=current_user.id).all()
        earned_levels = [cert.level for cert in existing_certs]
        requirements = [r for r in get_certification_requirements_new() if r['type'] == 'points']
        
        awarded_certificates = []
        
        for req in requirements:
            if req['level'] not in earned_levels and total_points >= req['points_required']:
                cert_id = f"ECV-PTS-{current_user.id:06d}-{req['level'].upper()}-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
                
                cert = Certification(
                    user_id=current_user.id,
                    certification_type='points_achievement',
                    title=req['title'],
                    level=req['level'],
                    points_required=req['points_required'],
                    user_points=total_points,
                    description=f'Awarded for achieving {req["points_required"]} sustainability points',
                    ai_generated_text=f'Congratulations! Your dedication to sustainability has earned you the {req["title"]} certification.',
                    certificate_id=cert_id,
                    qr_data=f'https://ecoverse.com/verify/{cert_id}',
                    valid_until=datetime.utcnow() + timedelta(days=365),
                    earned_at=datetime.utcnow(),
                    score=None
                )
                
                db.session.add(cert)
                token_rewards = {
                    'bronze': 500,
                    'silver': 1000,
                    'gold': 2000
                }
                tokens_earned = token_rewards.get(req['level'], 0)
                current_user.token_balance += tokens_earned
                action = EcoAction(
                    user_id=current_user.id,
                    action_type='certification_awarded_points',
                    co2_saved=req['points_required'] * 0.1,
                    tokens_earned=tokens_earned,
                    created_at=datetime.utcnow()
                )
                db.session.add(action)
                
                awarded_certificates.append({
                    'title': req['title'],
                    'level': req['level'],
                    'points_required': req['points_required']
                })
        
        if awarded_certificates:
            db.session.commit()
            
        return jsonify({
            'success': True,
            'awarded_certificates': awarded_certificates,
            'count': len(awarded_certificates)
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error checking points certificates: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/certification/test-history', methods=['GET'])
@login_required
def get_test_history():
    try:
        tests = CertificationTest.query.filter_by(
            user_id=current_user.id,
            level='ultra'
        ).order_by(CertificationTest.created_at.desc()).all()
        
        history = []
        for test in tests:
            if test.completed_at:
                history.append({
                    'level': test.level,
                    'score': test.score,
                    'passed': test.passed,
                    'completed_at': test.completed_at.strftime('%Y-%m-%d %H:%M') if test.completed_at else None,
                    'attempts': test.attempts_count
                })
        
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        print(f"Error getting test history: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/certification/last-test/<level>', methods=['GET'])
@login_required
def get_last_test(level):
    try:
        last_test = CertificationTest.query.filter_by(
            user_id=current_user.id,
            level=level
        ).order_by(CertificationTest.created_at.desc()).first()
        
        if last_test:
            return jsonify({
                'success': True,
                'last_test': {
                    'id': last_test.id,
                    'level': last_test.level,
                    'score': last_test.score,
                    'passed': last_test.passed,
                    'last_attempt': last_test.last_attempt.isoformat() if last_test.last_attempt else None,
                    'attempts_count': last_test.attempts_count
                }
            })
        
        return jsonify({
            'success': True,
            'last_test': None
        })
        
    except Exception as e:
        print(f"Error getting last test: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/certification/auto-award', methods=['POST'])
@login_required
def auto_award_certificates():
    return check_points_certificates()

@app.route('/api/certification/submit-quiz', methods=['POST'])
@login_required
def submit_certification_quiz():
    try:
        data = request.json
        quiz_id = data.get('quiz_id')
        level = data.get('level')
        answers = data.get('answers', [])
        if level != 'ultra':
            return jsonify({
                'success': False,
                'message': 'Only Ultra Legend certification requires a quiz'
            })
        test = CertificationTest.query.get(quiz_id)
        if not test or test.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Test not found'})
        question_ids = json.loads(test.question_ids)
        questions = CertificationQuestion.query.filter(
            CertificationQuestion.id.in_(question_ids)
        ).all()
        correct_answers = 0
        total_questions = len(questions)
        
        for i, question in enumerate(questions):
            if i < len(answers) and answers[i] == question.correct_answer:
                correct_answers += 1
        
        score_percentage = (correct_answers / total_questions) * 100
        passing_score = 80
        passed = score_percentage >= passing_score
        test.user_answers = json.dumps(answers)
        test.score = score_percentage
        test.passed = passed
        test.completed_at = datetime.utcnow()
        if passed:
            cert_title = 'ULTRA LEGEND'
            cert_id = f"ECV-ULTRA-{current_user.id:06d}-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
            cert = Certification(
                user_id=current_user.id,
                certification_type='ultra_legend_quiz',
                title=cert_title,
                level='ultra',
                points_required=0,
                user_points=0,
                description=f'Passed Ultra Legend sustainability challenge with {score_percentage:.1f}% score',
                ai_generated_text='You have proven yourself as a true sustainability master! The ULTRA LEGEND title is reserved for those with exceptional knowledge and dedication to our planet.',
                certificate_id=cert_id,
                valid_until=datetime.utcnow() + timedelta(days=365),
                earned_at=datetime.utcnow(),
                score=score_percentage
            )
            db.session.add(cert)
            tokens_earned = 10000
            current_user.token_balance += tokens_earned
            current_user.eco_score += 5000
            action = EcoAction(
                user_id=current_user.id,
                action_type='ultra_legend_earned',
                co2_saved=5000,
                tokens_earned=tokens_earned,
                created_at=datetime.utcnow()
            )
            db.session.add(action)
        else:
            tokens_earned = 0
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'score': round(score_percentage, 1),
            'passed': passed,
            'correct_answers': correct_answers,
            'total_questions': total_questions,
            'tokens_earned': tokens_earned,
            'new_certification': passed,
            'is_ultra': True,
            'message': f'Ultra Legend Challenge: {score_percentage:.1f}% - {"🎉 ULTRA LEGEND ACHIEVED!" if passed else f"Need {passing_score}% to pass."}'
        })
        
    except Exception as e:
        print(f"Error submitting quiz: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
# NEW CERTIFICATION SYSTEM
@app.route('/api/certification/user-certificates', methods=['GET'])
@login_required
def get_user_certificates_route():
    try:
        certs = Certification.query.filter_by(user_id=current_user.id)\
                                  .order_by(
                                      db.case(
                                          (Certification.level == 'ultra', 1),
                                          (Certification.level == 'gold', 2),
                                          (Certification.level == 'silver', 3),
                                          (Certification.level == 'bronze', 4),
                                          else_=5
                                      )
                                  ).all()
        
        cert_list = []
        for cert in certs:
            cert_list.append({
                'id': cert.id,
                'title': cert.title,
                'level': cert.level,
                'certificate_id': cert.certificate_id,
                'score': cert.score if cert.score else None,
                'description': cert.description,
                'points_required': cert.points_required,
                'user_points': cert.user_points,
                'earned_at': cert.earned_at.strftime('%Y-%m-%d %H:%M'),
                'valid_until': cert.valid_until.strftime('%Y-%m-%d') if cert.valid_until else None,
                'is_ultra': cert.level == 'ultra'
            })
        
        return jsonify({
            'success': True,
            'certificates': cert_list,
            'count': len(certs)
        })
        
    except Exception as e:
        print(f"Error getting certificates: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/certification/list', methods=['GET'])
@login_required
def list_user_certifications():
    try:
        certs = Certification.query.filter_by(user_id=current_user.id)\
                                  .order_by(Certification.earned_at.desc())\
                                  .all()
        
        cert_list = []
        for cert in certs:
            cert_list.append({
                'id': cert.id,
                'title': cert.title,
                'level': cert.level,
                'certificate_id': cert.certificate_id,
                'description': cert.description,
                'points_required': cert.points_required,
                'user_points': cert.user_points,
                'earned_at': cert.earned_at.strftime('%Y-%m-%d %H:%M'),
                'valid_until': cert.valid_until.strftime('%Y-%m-%d') if cert.valid_until else None
            })
        
        return jsonify({
            'success': True,
            'certifications': cert_list,
            'count': len(certs)
        })
        
    except Exception as e:
        print(f"Error listing certifications: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
# OLD
@app.route('/api/certification/next-milestone', methods=['GET'])
@login_required
def get_next_milestone():
    try:
        total_points = calculate_user_points(current_user.id)
        
        milestones = [
            {'level': 'bronze', 'points': 1000, 'title': 'Bronze ECODIST'},
            {'level': 'silver', 'points': 5000, 'title': 'Silver ECOGUARDIAN'},
            {'level': 'gold', 'points': 15000, 'title': 'Gold ECOMAGE'},
            {'level': 'platinum', 'points': 50000, 'title': 'Platinum ECOLEGEND'}
        ]
        next_milestone = None
        for milestone in milestones:
            if total_points < milestone['points']:
                next_milestone = milestone
                break
        
        if next_milestone:
            points_needed = next_milestone['points'] - total_points
            
            return jsonify({
                'success': True,
                'next_milestone': next_milestone,
                'current_points': total_points,
                'points_needed': points_needed
            })
        return jsonify({
            'success': True,
            'next_milestone': None,
            'message': 'All certification milestones achieved!',
            'current_points': total_points
        })
        
    except Exception as e:
        print(f"Error getting next milestone: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# OLD CERTIFICATION SYSTEM. IGNORE.
@app.route('/api/certification/ai-assessment', methods=['GET'])
@login_required
def get_ai_assessment_for_cert():
    try:
        total_points = calculate_user_points(current_user.id)
        if total_points >= 50000:
            rating = "⭐⭐⭐⭐⭐"
            level = "Platinum"
        elif total_points >= 15000:
            rating = "⭐⭐⭐⭐"
            level = "Gold"
        elif total_points >= 5000:
            rating = "⭐⭐⭐"
            level = "Silver"
        elif total_points >= 1000:
            rating = "⭐⭐"
            level = "Bronze"
        else:
            rating = "⭐"
            level = "Beginner"
        assessment = {
            'rating': rating,
            'level': level,
            'strengths': [
                f"Consistent sustainability tracking",
                f"Active participation in eco-actions",
                f"Growing knowledge through quizzes"
            ],
            'improvements': [
                f"Reach {max(0, 1000 - total_points)} more points for Bronze certification" if total_points < 1000 else
                f"Reach {max(0, 5000 - total_points)} more points for Silver certification" if total_points < 5000 else
                f"Reach {max(0, 15000 - total_points)} more points for Gold certification" if total_points < 15000 else
                f"Maintain Platinum status with continued actions"
            ],
            'tips': [
                "Complete daily carbon calculator for consistent points",
                "Take certification quizzes to test your knowledge",
                "Log eco-actions regularly to build your streak",
                "Participate in flight simulations for bonus points"
            ]
        }
        
        return jsonify({
            'success': True,
            'assessment': assessment
        })
        
    except Exception as e:
        print(f"Error getting AI assessment: {str(e)}")
        return jsonify({
            'success': True,
            'assessment': {
                'rating': "⭐",
                'level': "Beginner",
                'strengths': ["Starting your sustainability journey"],
                'improvements': ["Complete your first carbon calculator"],
                'tips': ["Begin with the carbon calculator to understand your impact"]
            }
        })

def calculate_user_points(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return 0
        total_points = user.eco_score
        carbon_actions = CarbonAction.query.filter_by(user_id=user_id).all()
        total_points += len(carbon_actions) * 10
        eco_actions = EcoAction.query.filter_by(user_id=user_id).all()
        total_points += len(eco_actions) * 15
        completed_flights = AviationQuest.query.filter_by(
            user_id=user_id,
            status='completed'
        ).all()
        total_points += len(completed_flights) * 200
        climate_actions = ClimateSnapshot.query.filter_by(user_id=user_id).all()
        total_points += len(climate_actions) * 50
        recycling_actions = EcoAction.query.filter_by(
            user_id=user_id
        ).filter(
            EcoAction.action_type.like('%recycling%')
        ).all()
        total_points += len(recycling_actions) * 25
        
        return total_points
        
    except Exception as e:
        print(f"Error calculating user points: {str(e)}")
        return 0

def get_certification_questions(level):
    try:
        if level != 'ultra':
            return []
        
        num_questions = 40
        questions = CertificationQuestion.query.filter_by(
            level='ultra'
        ).order_by(func.random()).limit(num_questions).all()
        if len(questions) < num_questions:
            print(f"Only {len(questions)} questions found for Ultra Legend, generating more...")
            new_questions = generate_certification_questions('ultra')
            if new_questions:
                questions = CertificationQuestion.query.filter_by(
                    level='ultra'
                ).order_by(func.random()).limit(num_questions).all()
        
        return questions
        
    except Exception as e:
        print(f"Error getting questions: {str(e)}")
        return []

@app.route('/music-test')
def music_test():
    return render_template('music_test.html')
def get_historical_events(year):
    events = {
        1850: ['First reliable global temperature records begin (HadCRUT)'],
        1886: ['Karl Benz patents the first gasoline-powered automobile'],
        1896: ['Svante Arrhenius publishes first calculation of global warming from CO2'],
        1958: ['Charles Keeling begins continuous CO2 measurements at Mauna Loa'],
        1979: ['First satellite measurements of Arctic sea ice (NASA/NSIDC)'],
        1988: ['NASA scientist James Hansen testifies to Congress about climate change'],
        1992: ['UN Framework Convention on Climate Change adopted at Earth Summit'],
        1997: ['Kyoto Protocol adopted'],
        2006: ['Al Gore\'s "An Inconvenient Truth" raises public awareness'],
        2015: ['Paris Agreement adopted by 196 countries'],
        2018: ['IPCC Special Report on 1.5°C warming'],
        2022: ['Global CO2 reaches 420 ppm, 50% above pre-industrial levels'],
        2023: ['Hottest year on record globally']
    }
    event_list = []
    for event_year, event_descriptions in events.items():
        if abs(event_year - year) <= 2:
            event_list.extend(event_descriptions)
    
    return event_list

@app.route('/points-debug')
@login_required
def points_debug():
    current_user.eco_score = 50000
    current_user.token_balance = 50000
    db.session.commit()
    
    flash('50,000 points and tokens awarded!', 'success')
    return redirect(url_for('certifications'))

def get_historical_explanations(year, data):
    explanations = []
    
    if year <= 1900:
        explanations.append("Pre-industrial era: Natural climate variability dominated")
    elif year <= 1950:
        explanations.append("Early industrialization: CO2 begins rising from fossil fuel use")
    elif year <= 1980:
        explanations.append("Post-war boom: Rapid increase in emissions and warming")
    elif year <= 2000:
        explanations.append("Scientific consensus emerges: IPCC formed, Kyoto Protocol")
    else:
        explanations.append("Anthropocene era: Human activity dominates climate system")
    if data.get('co2', 0) > 400:
        explanations.append(f"CO2 levels {data['co2']} ppm: 50% above pre-industrial levels")
    
    if data.get('temp', 0) > 1.0:
        explanations.append(f"Temperature anomaly +{data['temp']}°C: Approaching Paris Agreement limits")
    
    return explanations

def generate_impacts_assessment(year, scenario, ratio):
    impacts = {
        'bau': {
            'temperature': 'Extreme heat waves affecting 3 billion people annually',
            'sea_level': '100+ million people affected by annual coastal flooding',
            'agriculture': 'Major crop yield reductions (20-30%) in tropical regions',
            'ecosystems': '70-90% of coral reefs lost, mass extinction events',
            'economy': '5-20% GDP loss globally, trillions in climate damages'
        },
        'moderate': {
            'temperature': 'Moderate heat stress increase, adaptation possible',
            'sea_level': 'Coastal communities need protection, some relocation',
            'agriculture': 'Crop shifts and adaptation required',
            'ecosystems': 'Significant coral bleaching, some forest dieback',
            'economy': '2-10% GDP loss, manageable with investment'
        },
        'radical': {
            'temperature': 'Limited additional heat stress, within adaptation capacity',
            'sea_level': 'Managed coastal protection, limited relocation',
            'agriculture': 'Minor impacts with adaptation',
            'ecosystems': 'Some ecosystem stress but major systems preserved',
            'economy': '1-3% GDP loss, transition costs manageable'
        }
    }
    
    scenario_impacts = impacts.get(scenario, impacts['moderate'])
    scaled_impacts = {}
    for key, impact in scenario_impacts.items():
        if scenario == 'bau':
            severity = f"{int(ratio * 100)}% of maximum impact: {impact}"
        elif scenario == 'radical':
            severity = f"{int((1 - ratio) * 100)}% impact reduction: {impact}"
        else:
            severity = impact
        
        scaled_impacts[key] = severity
    
    return scaled_impacts

def get_key_changes_for_year(year, scenario):
    changes = []
    
    if scenario == 'bau':
        if year >= 2030:
            changes.append('Frequent unprecedented heat waves become common')
        if year >= 2040:
            changes.append('Arctic sea ice-free summers become regular')
        if year >= 2050:
            changes.append('Major tipping points (Amazon dieback, permafrost melt) become likely')
        if year >= 2070:
            changes.append('Large-scale climate migration begins')
        if year >= 2100:
            changes.append('Planet largely unrecognizable from pre-industrial state')
    
    elif scenario == 'moderate':
        if year >= 2030:
            changes.append('Noticeable increase in extreme weather events')
        if year >= 2050:
            changes.append('Significant sea level rise impacts coastal cities')
        if year >= 2070:
            changes.append('Major ecosystem shifts and species range changes')
        if year >= 2100:
            changes.append('Managed but significant climate impacts')
    
    else:
        if year >= 2030:
            changes.append('Peak emissions followed by rapid decline')
        if year >= 2050:
            changes.append('Net-zero emissions achieved globally')
        if year >= 2070:
            changes.append('Temperature stabilization begins')
        if year >= 2100:
            changes.append('Climate system stabilization achieved')
    
    return changes

def generate_scenario_education(scenario, year, projections):
    education = {
        'bau': {
            'title': 'Business as Usual Scenario',
            'summary': 'This represents a future where emissions continue to grow rapidly with limited climate action.',
            'key_points': [
                'Based on IPCC SSP5-8.5 scenario',
                'Assumes continued fossil fuel dependence',
                'Limited deployment of clean energy',
                'High population growth and resource use'
            ],
            'implications': 'Leads to severe climate impacts that would be difficult to adapt to.',
            'avoidance': 'Requires immediate, drastic action to avoid this path.'
        },
        'moderate': {
            'title': 'Moderate Action Scenario',
            'summary': 'This represents current policy trajectories and pledged climate actions.',
            'key_points': [
                'Based on IPCC SSP2-4.5 scenario',
                'Moderate emissions reductions',
                'Some clean energy deployment',
                'Mixed success in international cooperation'
            ],
            'implications': 'Results in significant but manageable climate impacts.',
            'improvement': 'Could be improved with stronger policies and faster action.'
        },
        'radical': {
            'title': 'Radical Change Scenario',
            'summary': 'This represents aggressive climate action consistent with 1.5°C Paris goal.',
            'key_points': [
                'Based on IPCC SSP1-2.6 scenario',
                'Rapid emissions reductions',
                'Massive clean energy deployment',
                'Strong international cooperation',
                'Sustainable development pathways'
            ],
            'implications': 'Limits warming to manageable levels with adaptation possible.',
            'challenges': 'Requires unprecedented global cooperation and investment.'
        }
    }
    
    scenario_edu = education.get(scenario, education['moderate'])
    scenario_edu['year_specific'] = f"In {year}, this scenario projects: CO₂ = {projections['co2_ppm']} ppm, Temperature = +{projections['temp_increase']}°C, Sea Level = +{projections['sea_level_cm']} cm"
    
    return scenario_edu

def get_global_comparisons(user_co2):
    comparisons = {
        'global_average': 4000,
        'sustainable_target': 2000,
        'usa_average': 16000,
        'eu_average': 6000,
        'china_average': 7000,
        'india_average': 2000,
        'africa_average': 1000
    }
    
    results = {}
    for region, average in comparisons.items():
        difference = user_co2 - average
        percentage = (difference / average * 100) if average > 0 else 0
        results[region] = {
            'average': average,
            'difference': difference,
            'percentage': round(percentage, 1),
            'comparison': 'above' if difference > 0 else 'below' if difference < 0 else 'equal'
        }
    
    return results

def get_personalized_recommendations(user_co2, categories):
    recommendations = []
    if categories.get('transportation', 0) > 2000:
        recommendations.append({
            'category': 'transportation',
            'action': 'Switch to electric vehicle or use public transit',
            'impact_kg': 1500,
            'cost': 'Medium-High',
            'difficulty': 'Medium',
            'priority': 'High'
        })
    if categories.get('home', 0) > 1500:
        recommendations.append({
            'category': 'home',
            'action': 'Switch to renewable energy provider',
            'impact_kg': 800,
            'cost': 'Low',
            'difficulty': 'Easy',
            'priority': 'High'
        })
    if categories.get('food', 0) > 1000:
        recommendations.append({
            'category': 'food',
            'action': 'Reduce meat consumption by 50%',
            'impact_kg': 600,
            'cost': 'Low (savings)',
            'difficulty': 'Medium',
            'priority': 'Medium'
        })
    if user_co2 > 10000:
        recommendations.append({
            'category': 'lifestyle',
            'action': 'Consider carbon offsetting for unavoidable emissions',
            'impact_kg': 2000,
            'cost': 'Medium',
            'difficulty': 'Easy',
            'priority': 'Medium'
        })
    
    if user_co2 < 3000:
        recommendations.append({
            'category': 'advocacy',
            'action': 'Advocate for climate policies in your community',
            'impact_kg': 'Variable',
            'cost': 'Low',
            'difficulty': 'Medium',
            'priority': 'Low'
        })
    ai_recommendations = generate_ai_recommendations(user_co2, categories)
    recommendations.extend(ai_recommendations[:2])
    
    return recommendations

def calculate_potential_impact(recommendations):
    total_impact = sum(r.get('impact_kg', 0) for r in recommendations)
    
    return {
        'total_reduction_kg': total_impact,
        'percentage_reduction': round((total_impact / 5000) * 100, 1) if total_impact > 0 else 0,
        'equivalent_trees': round(total_impact / 21),
        'equivalent_cars': round(total_impact / 2000, 1),
        'timeline': '6-12 months for full implementation'
    }

def generate_personal_insights(user_co2, comparisons):
    insights = []
    
    global_comp = comparisons.get('global_average', {})
    if global_comp.get('comparison') == 'above':
        insights.append(f"Your carbon footprint is {abs(global_comp['percentage'])}% above the global average.")
    elif global_comp.get('comparison') == 'below':
        insights.append(f"Great! Your footprint is {abs(global_comp['percentage'])}% below the global average.")
    
    sustainable_comp = comparisons.get('sustainable_target', {})
    if sustainable_comp.get('comparison') == 'above':
        insights.append(f"To reach sustainable levels, reduce by {abs(sustainable_comp['difference'])} kg CO₂/year.")
    ai_insight = generate_ai_insight(user_co2, comparisons)
    insights.append(ai_insight)
    
    return insights

def generate_ai_recommendations(user_co2, categories):
    try:
        prompt = f"""
        User has carbon footprint of {user_co2} kg CO2/year.
        Breakdown: {json.dumps(categories, indent=2)}
        
        Provide 2-3 specific, actionable recommendations to reduce their footprint.
        Focus on:
        1. Highest impact areas
        2. Realistic changes they can make
        3. Estimated CO2 savings
        
        Return as a JSON array of objects with keys: category, action, impact_kg, difficulty, priority
        """
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a personal sustainability coach providing actionable recommendations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"AI recommendations error: {e}")
        return []

def generate_ai_insight(user_co2, comparisons):
    try:
        prompt = f"""
        User has a carbon footprint of {user_co2} kg CO2/year.
        Comparisons: {json.dumps(comparisons, indent=2)}
        
        Provide one brief, encouraging insight about their situation.
        Focus on:
        1. Their relative position compared to averages
        2. One key area for improvement
        3. Positive encouragement
        
        Return just the insight text (1-2 sentences).
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a supportive climate coach providing encouraging insights."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"AI insight error: {e}")
        return "Every reduction counts! Your awareness is the first step toward meaningful change."

def get_climate_solutions_by_category(category, difficulty):
    all_solutions = [
        {
            'action': 'Install solar panels',
            'category': 'energy',
            'impact_kg': 1500,
            'cost': 'High',
            'difficulty': 'Medium',
            'timeframe': '3-6 months',
            'description': 'Generate clean electricity from sunlight',
            'resources': ['Federal tax credits', 'Local incentives', 'Solar installers']
        },
        {
            'action': 'Switch to wind/solar utility',
            'category': 'energy',
            'impact_kg': 800,
            'cost': 'Low',
            'difficulty': 'Easy',
            'timeframe': '1 month',
            'description': 'Choose electricity from renewable sources',
            'resources': ['Utility green programs', 'Community solar']
        },
        {
            'action': 'Switch to electric vehicle',
            'category': 'transportation',
            'impact_kg': 2500,
            'cost': 'High',
            'difficulty': 'Medium',
            'timeframe': 'When replacing vehicle',
            'description': 'Zero tailpipe emissions, lower lifecycle emissions',
            'resources': ['EV tax credits', 'Charging infrastructure']
        },
        {
            'action': 'Use public transit/bike 3+ days/week',
            'category': 'transportation',
            'impact_kg': 600,
            'cost': 'Low',
            'difficulty': 'Easy',
            'timeframe': 'Immediate',
            'description': 'Reduce car dependence and emissions',
            'resources': ['Transit apps', 'Bike sharing programs']
        },
        {
            'action': 'Reduce meat consumption by 50%',
            'category': 'food',
            'impact_kg': 800,
            'cost': 'Low (savings)',
            'difficulty': 'Medium',
            'timeframe': 'Ongoing',
            'description': 'Plant-based diets have lower carbon footprint',
            'resources': ['Meatless Monday', 'Plant-based recipes']
        },
        {
            'action': 'Reduce food waste',
            'category': 'food',
            'impact_kg': 400,
            'cost': 'Savings',
            'difficulty': 'Easy',
            'timeframe': 'Immediate',
            'description': 'Plan meals and use leftovers effectively',
            'resources': ['Meal planning apps', 'Composting guides']
        },
        {
            'action': 'Improve home insulation',
            'category': 'home',
            'impact_kg': 500,
            'cost': 'Medium',
            'difficulty': 'Medium',
            'timeframe': '3 months',
            'description': 'Reduce heating and cooling energy use',
            'resources': ['Energy audits', 'Insulation rebates']
        },
        {
            'action': 'Install smart thermostat',
            'category': 'home',
            'impact_kg': 200,
            'cost': 'Low',
            'difficulty': 'Easy',
            'timeframe': '1 day',
            'description': 'Optimize heating and cooling automatically',
            'resources': ['Energy Star products', 'Utility rebates']
        },
        {
            'action': 'Buy less, choose quality',
            'category': 'consumption',
            'impact_kg': 300,
            'cost': 'Variable',
            'difficulty': 'Medium',
            'timeframe': 'Ongoing',
            'description': 'Reduce consumption and choose durable goods',
            'resources': ['Minimalism guides', 'Repair cafes']
        },
        {
            'action': 'Offset unavoidable emissions',
            'category': 'offsetting',
            'impact_kg': 'Variable',
            'cost': 'Low-Medium',
            'difficulty': 'Easy',
            'timeframe': 'Immediate',
            'description': 'Support verified carbon reduction projects',
            'resources': ['Gold Standard', 'Verified Carbon Standard']
        }
    ]
    if category != 'all':
        all_solutions = [s for s in all_solutions if s['category'] == category]
    if difficulty != 'all':
        all_solutions = [s for s in all_solutions if s['difficulty'] == difficulty]
    
    return all_solutions

def generate_ai_explanation(topic):
    try:
        prompt = f"""
        Provide a comprehensive educational explanation about {topic} in climate science.
        
        Include:
        1. Definition and basic science
        2. Causes and contributing factors
        3. Current trends and data
        4. Impacts and consequences
        5. Solutions and mitigation strategies
        6. Reliable sources for further learning
        
        Return as a JSON object with these keys: title, content, sources (array), difficulty, category.
        Make it accurate, educational, and suitable for general audience.
        """
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a climate science educator creating accurate, engaging explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        explanation_text = response.choices[0].message.content
        return json.loads(explanation_text)
        
    except Exception as e:
        print(f"AI explanation error: {e}")
        return {
            'title': f'Understanding {topic}',
            'content': f'Climate {topic} refers to changes in climate patterns over time, primarily driven by human activities like burning fossil fuels.',
            'sources': ['IPCC AR6', 'NASA Climate Change', 'NOAA Climate.gov'],
            'difficulty': 'intermediate',
            'category': 'science'
        }

def get_future_projections(year, scenario):
    base = {
        'bau': {'co2_ppm': 425, 'temp_increase': 1.2, 'sea_level_cm': 24, 'arctic_ice': 3.9},
        'moderate': {'co2_ppm': 425, 'temp_increase': 1.2, 'sea_level_cm': 24, 'arctic_ice': 3.9},
        'radical': {'co2_ppm': 425, 'temp_increase': 1.2, 'sea_level_cm': 24, 'arctic_ice': 3.9}
    }
    
    projections = base.get(scenario, base['moderate'])
    years_from_now = year - 2024
    
    if scenario == 'bau':
        projections['co2_ppm'] += years_from_now * 2.5
        projections['temp_increase'] += years_from_now * 0.04
        projections['sea_level_cm'] += years_from_now * 0.4
        projections['arctic_ice'] = max(0, projections['arctic_ice'] - years_from_now * 0.05)
    elif scenario == 'moderate':
        projections['co2_ppm'] += years_from_now * 1.5
        projections['temp_increase'] += years_from_now * 0.025
        projections['sea_level_cm'] += years_from_now * 0.25
        projections['arctic_ice'] = max(0, projections['arctic_ice'] - years_from_now * 0.03)
    else:
        projections['co2_ppm'] = max(425, 425 + years_from_now * 0.5)
        projections['temp_increase'] += years_from_now * 0.015
        projections['sea_level_cm'] += years_from_now * 0.15
        projections['arctic_ice'] = max(0, projections['arctic_ice'] - years_from_now * 0.01)
    
    return projections

def calculate_differences(proj1, proj2):
    return {
        'co2_difference': proj1.get('co2_ppm', 0) - proj2.get('co2_ppm', 0),
        'temp_difference': proj1.get('temp_increase', 0) - proj2.get('temp_increase', 0),
        'sea_level_difference': proj1.get('sea_level_cm', 0) - proj2.get('sea_level_cm', 0),
        'arctic_ice_difference': proj1.get('arctic_ice', 0) - proj2.get('arctic_ice', 0)
    }

def compare_impacts(proj1, proj2):
    impacts1 = generate_impacts_assessment(proj1.get('year', 2050), proj1.get('scenario', 'moderate'), 0.5)
    impacts2 = generate_impacts_assessment(proj2.get('year', 2050), proj2.get('scenario', 'moderate'), 0.5)
    
    return {
        'scenario1_impacts': impacts1,
        'scenario2_impacts': impacts2,
        'key_differences': [
            f"Temperature: {abs(proj1.get('temp_increase', 0) - proj2.get('temp_increase', 0)):.1f}°C difference",
            f"Sea Level: {abs(proj1.get('sea_level_cm', 0) - proj2.get('sea_level_cm', 0)):.0f} cm difference",
            f"CO2: {abs(proj1.get('co2_ppm', 0) - proj2.get('co2_ppm', 0)):.0f} ppm difference"
        ]
    }

def generate_comparison_insights(scenario1, scenario2, year):
    insights = []
    
    if scenario1 == 'bau' and scenario2 == 'radical':
        insights.append(f"By {year}, choosing radical action over business as usual could prevent:")
        insights.append(f"• {abs(calculate_differences(get_future_projections(year, 'bau'), get_future_projections(year, 'radical'))['temp_difference']):.1f}°C of additional warming")
        insights.append(f"• {abs(calculate_differences(get_future_projections(year, 'bau'), get_future_projections(year, 'radical'))['sea_level_difference']):.0f} cm of sea level rise")
        insights.append(f"• Millions of climate-related deaths and trillions in economic damages")
    
    elif scenario1 == 'moderate' and scenario2 == 'radical':
        insights.append(f"Enhanced climate action could still make a significant difference by {year}:")
        insights.append(f"• Prevent irreversible tipping points like Amazon dieback")
        insights.append(f"• Save millions of species from extinction")
        insights.append(f"• Reduce climate adaptation costs by 50%")
    
    return insights

def prepare_comparison_visualization(proj1, proj2):
    return {
        'labels': ['CO2 (ppm)', 'Temperature (°C)', 'Sea Level (cm)', 'Arctic Ice (M km²)'],
        'scenario1': [
            proj1.get('co2_ppm', 0),
            proj1.get('temp_increase', 0),
            proj1.get('sea_level_cm', 0),
            proj1.get('arctic_ice', 0)
        ],
        'scenario2': [
            proj2.get('co2_ppm', 0),
            proj2.get('temp_increase', 0),
            proj2.get('sea_level_cm', 0),
            proj2.get('arctic_ice', 0)
        ]
    }

def generate_climate_quiz(difficulty, category):
    questions = {
        'easy': [
            {
                'question': 'What is the main greenhouse gas causing climate change?',
                'options': ['Carbon Dioxide (CO₂)', 'Oxygen (O₂)', 'Nitrogen (N₂)', 'Helium (He)'],
                'correct': 0,
                'explanation': 'Carbon dioxide is the primary greenhouse gas emitted through human activities.',
                'category': 'basics'
            },
            {
                'question': 'How much has Earth warmed since pre-industrial times?',
                'options': ['0.5°C', '1.2°C', '2.0°C', '3.5°C'],
                'correct': 1,
                'explanation': 'Earth has warmed approximately 1.2°C since 1850-1900 according to NASA and IPCC.',
                'category': 'temperature'
            }
        ],
        'medium': [
            {
                'question': 'What percentage of global emissions comes from agriculture?',
                'options': ['10%', '25%', '40%', '60%'],
                'correct': 1,
                'explanation': 'Agriculture accounts for about 25% of global greenhouse gas emissions.',
                'category': 'emissions'
            },
            {
                'question': 'Which renewable energy source has grown the fastest in recent years?',
                'options': ['Solar', 'Wind', 'Hydro', 'Geothermal'],
                'correct': 0,
                'explanation': 'Solar energy has seen the fastest growth, with costs dropping 90% in the last decade.',
                'category': 'solutions'
            }
        ],
        'hard': [
            {
                'question': 'What is climate sensitivity?',
                'options': [
                    'Public sensitivity to climate news',
                    'How much temperatures rise for a doubling of CO₂',
                    'Economic sensitivity to climate policies',
                    'Ecosystem sensitivity to temperature changes'
                ],
                'correct': 1,
                'explanation': 'Climate sensitivity refers to the warming expected from a doubling of atmospheric CO₂.',
                'category': 'science'
            },
            {
                'question': 'What is the albedo effect?',
                'options': [
                    'Reflection of sunlight by Earth\'s surface',
                    'Absorption of heat by oceans',
                    'Greenhouse gas trapping efficiency',
                    'Cloud formation patterns'
                ],
                'correct': 0,
                'explanation': 'Albedo is Earth\'s reflectivity. Ice has high albedo, oceans have low albedo.',
                'category': 'science'
            }
        ]
    }
    quiz_questions = questions.get(difficulty, questions['medium'])

    if category != 'all':
        quiz_questions = [q for q in quiz_questions if q.get('category') == category]
    
    return random.sample(quiz_questions, min(5, len(quiz_questions)))

def generate_climate_story(year, scenario, projections):
    try:
        prompt = f"""
        Create a narrative about what life might be like in the year {year} under the {scenario} climate scenario.
        
        Scenario details:
        - CO₂: {projections.get('co2_ppm', 'Unknown')} ppm
        - Temperature increase: +{projections.get('temp_increase', 'Unknown')}°C
        - Sea level rise: +{projections.get('sea_level_cm', 'Unknown')} cm
        
        Write a 3-paragraph story that includes:
        1. Daily life and weather patterns
        2. Environmental changes and impacts
        3. Societal adaptations and responses
        
        Make it realistic based on climate science, engaging, and thought-provoking.
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a science fiction writer creating plausible climate futures based on scientific projections."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        return {
            'title': f'Life in {year}: A {scenario.replace("_", " ").title()} Scenario',
            'content': response.choices[0].message.content.strip(),
            'scenario': scenario,
            'year': year,
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Climate story error: {e}")
        return {
            'title': f'Life in {year}',
            'content': f'In {year}, the world continues to adapt to climate change...',
            'scenario': scenario,
            'year': year
        }

def get_random_climate_fact():
    facts = [
        "The last decade was the hottest in 125,000 years (IPCC).",
        "Oceans have absorbed 90% of excess heat from global warming.",
        "Renewable energy is now cheaper than fossil fuels in most places.",
        "Climate change affects wine production by changing grape growing conditions.",
        "Burning fossil fuels releases carbon stored for millions of years.",
        "Permafrost thaw could release vast amounts of methane, a potent greenhouse gas.",
        "Climate change is shifting bird migration patterns and timing.",
        "Coral reefs could decline by 70-90% with 1.5°C warming.",
        "Planting trees is helpful but not enough to solve climate change alone.",
        "Climate solutions could create 65 million new jobs by 2030."
    ]
    
    return random.choice(facts)

def generate_snapshot_image(scenario, year, projections, username):
    try:
        width, height = 800, 400
        img = Image.new('RGB', (width, height), color=(13, 36, 97))
        draw = ImageDraw.Draw(img)
        try:
            title_font = ImageFont.truetype("arial.ttf", 32)
            text_font = ImageFont.truetype("arial.ttf", 20)
            small_font = ImageFont.truetype("arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        draw.text((width//2, 40), f"Climate Snapshot: {year}", fill=(255, 255, 255), font=title_font, anchor="mm")
        scenario_text = {
            'bau': 'Business as Usual (+4°C)',
            'moderate': 'Moderate Action (+2°C)',
            'radical': 'Radical Change (+1.5°C)'
        }.get(scenario, 'Moderate Action')
        
        scenario_color = {
            'bau': (231, 76, 60),
            'moderate': (243, 156, 18),
            'radical': (39, 174, 96)
        }.get(scenario, (243, 156, 18))
        
        draw.text((width//2, 80), scenario_text, fill=scenario_color, font=text_font, anchor="mm")
        y_pos = 130
        data_points = [
            (f"CO₂: {projections.get('co2_ppm', '--')} ppm", (255, 255, 255)),
            (f"Temperature: +{projections.get('temp_increase', '--')}°C", (255, 159, 67)),
            (f"Sea Level: +{projections.get('sea_level_cm', '--')} cm", (52, 152, 219)),
            (f"Arctic Ice: {projections.get('arctic_ice', '--')} M km²", (155, 89, 182))
        ]
        
        for text, color in data_points:
            draw.text((width//2, y_pos), text, fill=color, font=text_font, anchor="mm")
            y_pos += 40
        draw.text((width//2, height - 60), f"Prepared by: {username}", fill=(200, 200, 200), font=small_font, anchor="mm")
        draw.text((width//2, height - 40), datetime.now().strftime("%Y-%m-%d"), fill=(150, 150, 150), font=small_font, anchor="mm")
        draw.text((width//2, height - 20), "EcoVerse Climate Time Machine", fill=(100, 100, 100), font=small_font, anchor="mm")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
        
    except Exception as e:
        print(f"Snapshot image error: {e}")
        return None

def generate_progress_timeline(user_id):
    return [
        {'date': '2024-01', 'action': 'Joined EcoVerse', 'co2_saved': 0},
        {'date': '2024-02', 'action': 'First carbon calculation', 'co2_saved': 500},
        {'date': '2024-03', 'action': 'Completed 5 eco-actions', 'co2_saved': 1500},
        {'date': '2024-04', 'action': 'Earned Carbon Warrior certification', 'co2_saved': 3000}
    ]

def make_openai_call(messages, model="gpt-3.5-turbo", temperature=0.7, max_tokens=500):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in OpenAI call: {e}")
        return None

def get_major_cities_climate_data():
    cities = [
        {
            'name': 'New York, USA',
            'coordinates': {'lat': 40.7128, 'lon': -74.0060},
            'weather': get_simulated_weather_data(40.7128, -74.0060),
            'climate_risk': get_climate_risk_assessment(40.7128, -74.0060),
            'note': 'Major financial center vulnerable to sea level rise and extreme weather'
        },
        {
            'name': 'London, UK',
            'coordinates': {'lat': 51.5074, 'lon': -0.1278},
            'weather': get_simulated_weather_data(51.5074, -0.1278),
            'climate_risk': get_climate_risk_assessment(51.5074, -0.1278),
            'note': 'Temperate climate with increasing flood risk'
        },
        {
            'name': 'Singapore',
            'coordinates': {'lat': 1.3521, 'lon': 103.8198},
            'weather': get_simulated_weather_data(1.3521, 103.8198),
            'climate_risk': get_climate_risk_assessment(1.3521, 103.8198),
            'note': 'Tropical island nation highly vulnerable to sea level rise'
        },
        {
            'name': 'Mumbai, India',
            'coordinates': {'lat': 19.0760, 'lon': 72.8777},
            'weather': get_simulated_weather_data(19.0760, 72.8777),
            'climate_risk': get_climate_risk_assessment(19.0760, 72.8777),
            'note': 'Coastal megacity facing heat stress and monsoon changes'
        },
        {
            'name': 'Sydney, Australia',
            'coordinates': {'lat': -33.8688, 'lon': 151.2093},
            'weather': get_simulated_weather_data(-33.8688, 151.2093),
            'climate_risk': get_climate_risk_assessment(-33.8688, 151.2093),
            'note': 'Bushfire risk increasing with climate change'
        }
    ]
    
    return cities

def get_vulnerability_factors(lat, lon):
    factors = []
    if abs(lat) < 30:
        factors.append('Low-lying coastal area')
    if (lat > 20 and lat < 40) or (lat < -20 and lat > -40):
        factors.append('Water scarcity risk')
    
    return factors

def get_adaptation_strategies(lat, lon, risk_assessment):
    strategies = []
    
    if any(r['type'] == 'sea_level_rise' for r in risk_assessment.get('specific_risks', [])):
        strategies.extend([
            'Coastal defense infrastructure',
            'Managed retreat planning',
            'Elevated building standards'
        ])
    
    if any(r['type'] == 'heat_waves' for r in risk_assessment.get('specific_risks', [])):
        strategies.extend([
            'Urban green spaces and cooling centers',
            'Heat-resistant building materials',
            'Early warning systems'
        ])
    
    if any(r['type'] == 'drought' for r in risk_assessment.get('specific_risks', [])):
        strategies.extend([
            'Water conservation and recycling',
            'Drought-resistant agriculture',
            'Improved irrigation efficiency'
        ])
    
    if any(r['type'] == 'wildfire' for r in risk_assessment.get('specific_risks', [])):
        strategies.extend([
            'Firebreaks and fuel management',
            'Fire-resistant construction',
            'Community evacuation plans'
        ])
    
    return strategies

def get_local_climate_impacts(lat, lon):
    impacts = []
    if lat > 60:
        impacts.extend([
            'Rapid warming (3x global average)',
            'Sea ice loss affecting ecosystems',
            'Permafrost thaw and infrastructure damage'
        ])
    elif lat > 30:
        impacts.extend([
            'Increasing heat waves',
            'Changing precipitation patterns',
            'More intense storms'
        ])
    elif lat > 0:
        impacts.extend([
            'Hurricane/cyclone intensity increasing',
            'Sea level rise impacts',
            'Heat stress and health impacts'
        ])
    else:
        impacts.extend([
            'Coral bleaching and marine impacts',
            'Rainfall pattern changes',
            'Vector-borne disease range expansion'
        ])
    
    return impacts

def get_location_based_education(lat, lon):
    education = {}
    
    if lat > 60:
        education = {
            'title': 'Arctic Amplification',
            'content': 'The Arctic is warming 3 times faster than the global average due to ice-albedo feedback. This affects global weather patterns and sea levels.',
            'key_facts': [
                'Arctic sea ice has declined about 13% per decade since 1979',
                'Permafrost thaw releases methane, a potent greenhouse gas',
                'Arctic warming affects jet stream and extreme weather globally'
            ]
        }
    elif lat > 30:
        education = {
            'title': 'Temperate Climate Changes',
            'content': 'Temperate regions are experiencing more extreme weather events, changing seasons, and impacts on agriculture and ecosystems.',
            'key_facts': [
                'Heat waves are becoming more frequent and intense',
                'Precipitation patterns are shifting, with more intense rainfall',
                'Growing seasons are lengthening but becoming more variable'
            ]
        }
    elif lat > 0:
        education = {
            'title': 'Subtropical Climate Challenges',
            'content': 'Subtropical regions face increasing heat stress, water scarcity, and tropical storm intensity with climate change.',
            'key_facts': [
                'Desert regions are expanding',
                'Hurricane intensity is increasing with warmer oceans',
                'Water scarcity affects agriculture and communities'
            ]
        }
    else:
        education = {
            'title': 'Tropical Climate Impacts',
            'content': 'Tropical regions are experiencing coral bleaching, changing rainfall patterns, and impacts on biodiversity and agriculture.',
            'key_facts': [
                'Coral reefs could decline 70-90% with 1.5°C warming',
                'Rainforests are becoming drier in some regions',
                'Rice yields could decline 10-20% per degree of warming'
            ]
        }
    
    return education

def generate_certification_message(username, title, level, points):
    try:
        prompt = f"""
        Create a personalized, inspiring certification message for {username} who just earned the {title} ({level}) certification in EcoVerse with {points} points.
        
        The message should:
        1. Congratulate them personally
        2. Highlight their achievement
        3. Mention the impact they've made
        4. Inspire continued environmental action
        5. Be 2-3 sentences long
        6. Sound professional but warm
        
        Return only the message text.
        """
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a climate science educator creating accurate, engaging explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"AI message generation error: {e}")
        return f"Congratulations {username}! You've earned the {title} certification through your dedication to sustainability. Your {points} points demonstrate remarkable commitment to our planet. Keep inspiring others on this green journey!"
def generate_ai_assessment(username, eco_score, total_actions, eco_actions, flights_completed, carbon_footprint, join_date):
    try:
        days_active = (datetime.utcnow() - join_date).days
        
        prompt = f"""
        Provide a personalized sustainability assessment for {username}, an EcoVerse user.
        
        Stats:
        - Eco Score: {eco_score}
        - Days Active: {days_active}
        - Carbon Actions: {total_actions}
        - Eco Actions: {eco_actions}
        - Flights Completed: {flights_completed}
        - Carbon Footprint: {carbon_footprint} kg CO2/year
        
        Assessment should include:
        1. Overall progress rating (1-5 stars)
        2. Key strengths
        3. Areas for improvement
        4. Personalized tips
        5. Next goals
        
        Return as a JSON object with keys: rating, strengths, improvements, tips, goals
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert sustainability analyst providing detailed, actionable feedback."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"AI assessment error: {e}")
        return {
            "rating": "⭐⭐⭐⭐",
            "strengths": ["Active participant", "Consistent eco-actions"],
            "improvements": ["Could reduce carbon footprint further"],
            "tips": ["Try meat-free days", "Use public transport more often"],
            "goals": ["Reach 10,000 eco points", "Complete 50 eco-actions"]
        }

def generate_share_message(username, certification_title, level, points):
    try:
        prompt = f"""
        Create an inspiring social media post for {username} to share their new {certification_title} ({level}) certification earned with {points} points in EcoVerse.
        
        Requirements:
        - 1-2 sentences maximum
        - Include emojis
        - Sound excited and proud
        - Mention the achievement
        - Encourage others to join
        - Add relevant hashtags
        
        Return only the post text.
        """
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a social media expert creating engaging, shareable content about sustainability achievements."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Share message generation error: {e}")
        return f"🎉 Just earned the {certification_title} certification in EcoVerse with {points} points! Proud to be making a difference for our planet 🌍 #EcoVerse #Sustainability #{certification_title.replace(' ', '')}"

def generate_milestone_suggestions(current_points, target_points, points_needed, milestone_title):
    try:
        prompt = f"""
        User has {current_points} points and needs {points_needed} more points to reach {target_points} points for the {milestone_title} certification.
        
        Suggest 3-4 specific, actionable activities they can do in EcoVerse to earn these points.
        Each suggestion should:
        - Be specific to EcoVerse features
        - Estimate points earned
        - Be realistic and achievable
        - Include a time estimate
        
        Return as a JSON array of objects with keys: activity, points_estimate, time_estimate, description
        """
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert EcoVerse coach suggesting specific in-app activities to earn points."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Milestone suggestions error: {e}")
        return [
            {
                "activity": "Complete Carbon Calculator",
                "points_estimate": 50,
                "time_estimate": "10 minutes",
                "description": "Analyze your carbon footprint"
            },
            {
                "activity": "Log 5 Eco Actions",
                "points_estimate": 50,
                "time_estimate": "15 minutes",
                "description": "Track your daily sustainable activities"
            },
            {
                "activity": "Complete a Flight Quest",
                "points_estimate": 200,
                "time_estimate": "20 minutes",
                "description": "Learn about aviation emissions"
            }
        ]

@app.route('/clear-all-certificates')
@login_required
def clear_all_certificates():
    try:
        fake_certs = Certification.query.filter_by(
            user_id=current_user.id
        ).all()
        
        count = len(fake_certs)
        for cert in fake_certs:
            db.session.delete(cert)
        fake_tests = CertificationTest.query.filter_by(
            user_id=current_user.id
        ).all()
        
        test_count = len(fake_tests)
        for test in fake_tests:
            db.session.delete(test)
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'Cleared {count} certificates and {test_count} test records'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def generate_comparison_message(username, eco_score, certifications, community_stats):
    try:
        prompt = f"""
        User {username} has {eco_score} eco points and {certifications} certifications.
        Community statistics:
        - Total users: {community_stats['total_users']}
        - Top percentile: {community_stats['top_percentile']}%
        - Bronze certified: {community_stats['bronze_certified']}
        - Silver certified: {community_stats['silver_certified']}
        - Gold certified: {community_stats['gold_certified']}
        - Platinum certified: {community_stats['platinum_certified']}
        
        Create a motivating comparison message that:
        1. Shows their standing in the community
        2. Highlights their achievements
        3. Encourages continued progress
        4. Is positive and inspiring
        5. Is 2-3 sentences
        
        Return only the message text.
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a motivational coach comparing user achievements with community statistics."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Comparison message error: {e}")
        return f"Great work {username}! You're in the top {community_stats['top_percentile']}% of EcoVerse users. Your {certifications} certifications show impressive dedication to sustainability!"

def create_certificate_image(username, certification_title, level, date, certificate_id, points):
    colors = {
        'bronze': {'primary': '#CD7F32', 'secondary': '#FFD700', 'bg': '#FFF8DC'},
        'silver': {'primary': '#C0C0C0', 'secondary': '#E8E8E8', 'bg': '#F5F5F5'},
        'gold': {'primary': '#FFD700', 'secondary': '#FFF8DC', 'bg': '#FFFACD'},
        'platinum': {'primary': '#E5E4E2', 'secondary': '#B9B9B9', 'bg': '#F8F8FF'}
    }
    
    level_colors = colors.get(level, colors['bronze'])
    img = Image.new('RGB', (1200, 800), color=level_colors['bg'])
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("arial.ttf", 60)
        name_font = ImageFont.truetype("arial.ttf", 48)
        text_font = ImageFont.truetype("arial.ttf", 28)
        small_font = ImageFont.truetype("arial.ttf", 20)
    except:
        title_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    draw.rectangle([(50, 50), (1150, 750)], outline=level_colors['primary'], width=5)
    draw.rectangle([(50, 50), (150, 150)], outline=level_colors['primary'], width=3)
    draw.rectangle([(1050, 50), (1150, 150)], outline=level_colors['primary'], width=3)
    draw.rectangle([(50, 650), (150, 750)], outline=level_colors['primary'], width=3)
    draw.rectangle([(1050, 650), (1150, 750)], outline=level_colors['primary'], width=3)
    draw.text((600, 100), "ECO-VERSE", fill=level_colors['primary'], font=title_font, anchor="mm")
    draw.text((600, 180), "CERTIFICATE OF ACHIEVEMENT", fill=level_colors['secondary'], font=text_font, anchor="mm")
    draw.text((600, 300), "This certifies that", fill=(100, 100, 100), font=text_font, anchor="mm")
    draw.text((600, 370), username.upper(), fill=level_colors['primary'], font=name_font, anchor="mm")
    draw.text((600, 450), f"has successfully earned the", fill=(100, 100, 100), font=text_font, anchor="mm")
    draw.text((600, 500), f"{certification_title.upper()} ({level.upper()})", fill=level_colors['secondary'], font=text_font, anchor="mm")
    draw.text((600, 550), f"with {points:,} sustainability points", fill=(100, 100, 100), font=text_font, anchor="mm")
    draw.text((600, 650), f"Awarded on {date.strftime('%B %d, %Y')}", fill=(150, 150, 150), font=small_font, anchor="mm")
    draw.text((600, 680), f"Certificate ID: {certificate_id}", fill=(150, 150, 150), font=small_font, anchor="mm")
    verification_url = f"https://ecoverse.com/verify/{certificate_id}"
    qr_data = generate_qr_code(verification_url)
    
    if qr_data:
        try:
            import base64
            from io import BytesIO
            qr_base64 = qr_data.split(',')[1]
            qr_image = Image.open(BytesIO(base64.b64decode(qr_base64)))

            qr_size = (150, 150)
            qr_image = qr_image.resize(qr_size)

            img.paste(qr_image, (100, 600))

            draw.text((175, 760), "Scan to verify", fill=(100, 100, 100), font=small_font)
        except Exception as e:
            print(f"Error adding QR code to image: {e}")

    draw.text((1100, 780), "ECO-VERSE", fill=level_colors['primary'], font=small_font, anchor="rb")
    
    return img
CARBON_QUESTIONS = [
    {
        "question": "What percentage of global CO₂ emissions comes from aviation?",
        "options": ["2%", "5%", "10%", "15%"],
        "correct": 0,
        "explanation": "Aviation contributes about 2-3% of global CO₂ emissions."
    },
    {
        "question": "Which aircraft type is generally more fuel-efficient?",
        "options": ["Boeing 747", "Airbus A350", "Boeing 777", "Airbus A380"],
        "correct": 1,
        "explanation": "The Airbus A350 uses advanced materials and engines for better fuel efficiency."
    },
    {
        "question": "What is Sustainable Aviation Fuel (SAF) made from?",
        "options": ["Traditional petroleum", "Renewable biomass", "Natural gas", "Coal"],
        "correct": 1,
        "explanation": "SAF is made from renewable sources like used cooking oil and agricultural waste."
    },
    {
        "question": "How much CO₂ does a flight from Singapore to Hong Kong emit per passenger?",
        "options": ["50 kg", "150 kg", "300 kg", "500 kg"],
        "correct": 2,
        "explanation": "A 4-hour flight emits about 300-350 kg CO₂ per passenger in economy class."
    },
    {
        "question": "What's the most effective way to reduce aviation emissions?",
        "options": ["Use larger aircraft", "Improve air traffic management", "Fly slower", "All of the above"],
        "correct": 3,
        "explanation": "Combining multiple strategies is most effective for reducing emissions."
    },
    {
        "question": "What percentage of SAF can be blended with conventional jet fuel?",
        "options": ["Up to 10%", "Up to 30%", "Up to 50%", "Up to 100%"],
        "correct": 2,
        "explanation": "Current regulations allow up to 50% SAF blend with conventional fuel."
    },
    {
        "question": "Which seating class has the lowest carbon footprint per passenger?",
        "options": ["First Class", "Business Class", "Premium Economy", "Economy"],
        "correct": 3,
        "explanation": "Economy class has the lowest footprint as more passengers share the same aircraft."
    },
    {
        "question": "What is carbon offsetting in aviation?",
        "options": ["Reducing flight frequency", "Investing in environmental projects", "Using electric planes", "Flying at night"],
        "correct": 1,
        "explanation": "Carbon offsetting involves investing in projects that reduce emissions elsewhere."
    },
    {
        "question": "How much CO₂ can be saved by using SAF instead of conventional jet fuel?",
        "options": ["Up to 20%", "Up to 50%", "Up to 80%", "Up to 100%"],
        "correct": 2,
        "explanation": "SAF can reduce CO₂ emissions by up to 80% compared to conventional jet fuel."
    },
    {
        "question": "Which airline was the first to operate a commercial flight using 100% SAF?",
        "options": ["Singapore Airlines", "British Airways", "United Airlines", "Qatar Airways"],
        "correct": 2,
        "explanation": "United Airlines operated the first commercial flight using 100% SAF in December 2021."
    },
    {
        "question": "What is the main greenhouse gas emitted by aircraft?",
        "options": ["Methane", "Carbon Dioxide", "Nitrous Oxide", "Water Vapor"],
        "correct": 1,
        "explanation": "Aircraft primarily emit carbon dioxide (CO₂) from burning jet fuel."
    },
    {
        "question": "How does flying at higher altitudes affect the climate impact?",
        "options": ["Reduces impact", "Increases impact", "No effect", "Depends on the aircraft"],
        "correct": 1,
        "explanation": "Flying at higher altitudes increases climate impact due to contrails and other non-CO₂ effects."
    },
    {
        "question": "What is the typical fuel consumption of a modern A350 per passenger per 100km?",
        "options": ["1.5 liters", "2.5 liters", "3.5 liters", "4.5 liters"],
        "correct": 1,
        "explanation": "Modern aircraft like the A350 consume about 2.5 liters per passenger per 100km."
    },
    {
        "question": "Which country has the highest per capita aviation emissions?",
        "options": ["United States", "United Arab Emirates", "Singapore", "Australia"],
        "correct": 1,
        "explanation": "The UAE has the highest per capita aviation emissions due to high flight frequency."
    },
    {
        "question": "What percentage of flights are for leisure travel?",
        "options": ["25%", "40%", "60%", "80%"],
        "correct": 3,
        "explanation": "Approximately 80% of flights are for leisure or visiting friends and family."
    },
    {
        "question": "How long do aircraft contrails typically persist?",
        "options": ["Minutes", "Hours", "Days", "Weeks"],
        "correct": 1,
        "explanation": "Contrails can persist for hours and contribute to climate warming."
    },
    {
        "question": "What is the carbon footprint of a round-trip flight from New York to London?",
        "options": ["500 kg CO₂", "1000 kg CO₂", "1500 kg CO₂", "2000 kg CO₂"],
        "correct": 1,
        "explanation": "A round-trip flight from NYC to London emits about 1000 kg CO₂ per passenger."
    },
    {
        "question": "Which aviation technology shows the most promise for zero-emission flights?",
        "options": ["Electric planes", "Hydrogen planes", "Biofuels", "Solar-powered planes"],
        "correct": 1,
        "explanation": "Hydrogen-powered aircraft show great promise for medium to long-haul zero-emission flights."
    },
    {
        "question": "What percentage of aviation emissions come from long-haul flights?",
        "options": ["30%", "50%", "70%", "90%"],
        "correct": 2,
        "explanation": "Long-haul flights (over 1500km) account for about 70% of aviation emissions."
    },
    {
        "question": "How much could aviation emissions grow by 2050 without action?",
        "options": ["Double", "Triple", "Quadruple", "Increase 5x"],
        "correct": 1,
        "explanation": "Aviation emissions could triple by 2050 without significant mitigation efforts."
    },
    {
        "question": "What is the EU's plan to reduce aviation emissions called?",
        "options": ["Fit for 55", "Green Sky", "Clean Flight", "Eco Aviation"],
        "correct": 0,
        "explanation": "The EU's 'Fit for 55' package includes measures to reduce aviation emissions by 55% by 2030."
    },
    {
        "question": "Which aircraft is known as the most fuel-efficient in its class?",
        "options": ["Boeing 787", "Airbus A320neo", "Boeing 777X", "Airbus A220"],
        "correct": 3,
        "explanation": "The Airbus A220 is considered the most fuel-efficient aircraft in its class."
    },
    {
        "question": "What is 'flight shaming'?",
        "options": ["Criticizing poor service", "Avoiding flights for environmental reasons", "Complaining about delays", "None of the above"],
        "correct": 1,
        "explanation": "Flight shaming refers to avoiding air travel due to its environmental impact."
    },
    {
        "question": "How much CO₂ does aviation emit annually?",
        "options": ["500 million tons", "1 billion tons", "2.5 billion tons", "5 billion tons"],
        "correct": 1,
        "explanation": "Aviation emits about 1 billion tons of CO₂ annually."
    },
    {
        "question": "What is the ICAO's carbon offsetting scheme called?",
        "options": ["CORSIA", "CARBONFLY", "AVIATION+", "SKYCLEAN"],
        "correct": 0,
        "explanation": "CORSIA (Carbon Offsetting and Reduction Scheme for International Aviation) is ICAO's scheme."
    },
    {
        "question": "Which airline has committed to net-zero emissions by 2050?",
        "options": ["All major airlines", "Only European airlines", "Only low-cost carriers", "No airlines"],
        "correct": 0,
        "explanation": "All major airlines have committed to net-zero emissions by 2050 through the IATA agreement."
    },
    {
        "question": "What percentage improvement in fuel efficiency has aviation achieved since 1990?",
        "options": ["10%", "25%", "50%", "75%"],
        "correct": 2,
        "explanation": "Aviation has improved fuel efficiency by about 50% since 1990."
    },
    {
        "question": "How do contrails affect global warming?",
        "options": ["Cool the planet", "Warm the planet", "No effect", "Only affect ozone"],
        "correct": 1,
        "explanation": "Contrails trap heat and contribute to global warming."
    },
    {
        "question": "What is the main barrier to electric aviation?",
        "options": ["Cost", "Battery weight", "Regulations", "Public acceptance"],
        "correct": 1,
        "explanation": "Battery weight is the main technical barrier to electric aviation for larger aircraft."
    },
    {
        "question": "Which country produces the most sustainable aviation fuel?",
        "options": ["United States", "Germany", "Brazil", "China"],
        "correct": 0,
        "explanation": "The United States is the largest producer of sustainable aviation fuel."
    }
]

def generate_boarding_pass(quest, airports, airline_code):
    departure_info = airports.get(quest.departure_airport, {'name': 'Unknown', 'icao': 'XXXX', 'city': 'Unknown'})
    arrival_info = airports.get(quest.arrival_airport, {'name': 'Unknown', 'icao': 'XXXX', 'city': 'Unknown'})

    departure_time = datetime.utcnow()
    boarding_time = (departure_time).strftime('%H:%M')
    flight_durations = {
        'SIN-HKG': 180,
        'HKG-SIN': 180,
        'JFK-LHR': 420,
        'LHR-JFK': 420,
        'DFW-HKG': 900,
        'BOM-DXB': 180,
        'SYD-LAX': 900,
        'CDG-NRT': 720, 
        'SIN-SYD': 480,
        'DXB-LHR': 420
    }
    
    route = f"{quest.departure_airport}-{quest.arrival_airport}"
    duration_minutes = flight_durations.get(route, 240)
    arrival_time = departure_time + timedelta(minutes=duration_minutes)
    barcode_data = f"{quest.flight_number}|{quest.departure_airport}|{quest.arrival_airport}|{quest.seat}|{quest.user_id}"
    
    boarding_pass = {
        'departure': {
            'airport': quest.departure_airport,
            'name': departure_info['name'],
            'icao': departure_info['icao'],
            'city': departure_info['city'],
            'time': departure_time.strftime('%H:%M'),
            'terminal': random.choice(['T1', 'T2', 'T3'])
        },
        'arrival': {
            'airport': quest.arrival_airport,
            'name': arrival_info['name'],
            'icao': arrival_info['icao'],
            'city': arrival_info['city'],
            'time': arrival_time.strftime('%H:%M'),
            'terminal': random.choice(['T1', 'T2', 'T3'])
        },
        'passenger': current_user.username,
        'passport_country': quest.passport_country,
        'flight_number': quest.flight_number,
        'airline': quest.airline,
        'airline_code': airline_code,
        'aircraft': quest.aircraft,
        'gate': quest.gate,
        'seat': quest.seat,
        'date': departure_time.strftime('%d %b %Y'),
        'boarding_time': boarding_time,
        'flight_duration': duration_minutes,
        'barcode_data': barcode_data,
        'booking_reference': ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)),
        'baggage_drop': random.choice(['A', 'B', 'C']) + str(random.randint(1, 20)),
        'sequence_number': random.randint(1, 999)
    }
    
    return boarding_pass

def get_country_from_airport(airport_code):
    countries = {
        'SIN': 'Singapore',
        'DFW': 'United States',
        'JFK': 'United States',
        'BOM': 'India',
        'HKG': 'Hong Kong SAR, China',
        'LHR': 'United Kingdom',
        'CDG': 'France',
        'NRT': 'Japan',
        'SYD': 'Australia',
        'DXB': 'United Arab Emirates'
    }
    return countries.get(airport_code, 'Unknown Country')

def get_airport_details(airport_code):
    airports = {
        'SIN': {
            'name': 'Singapore Changi Airport', 
            'city': 'Singapore', 
            'country': 'Singapore',
            'icao': 'WSSS'
        },
        'HKG': {
            'name': 'Hong Kong International Airport', 
            'city': 'Hong Kong', 
            'country': 'Hong Kong SAR',
            'icao': 'VHHH'
        },
        'JFK': {
            'name': 'John F. Kennedy International Airport', 
            'city': 'New York', 
            'country': 'USA',
            'icao': 'KJFK'
        },
        'LHR': {
            'name': 'London Heathrow Airport', 
            'city': 'London', 
            'country': 'UK',
            'icao': 'EGLL'
        },
        'DFW': {
            'name': 'Dallas/Fort Worth International Airport', 
            'city': 'Dallas', 
            'country': 'USA',
            'icao': 'KDFW'
        },
        'BOM': {
            'name': 'Chhatrapati Shivaji Maharaj International Airport', 
            'city': 'Mumbai', 
            'country': 'India',
            'icao': 'VABB'
        },
        'SYD': {
            'name': 'Sydney Kingsford Smith Airport', 
            'city': 'Sydney', 
            'country': 'Australia',
            'icao': 'YSSY'
        },
        'NRT': {
            'name': 'Narita International Airport', 
            'city': 'Tokyo', 
            'country': 'Japan',
            'icao': 'RJAA'
        },
        'CDG': {
            'name': 'Charles de Gaulle Airport', 
            'city': 'Paris', 
            'country': 'France',
            'icao': 'LFPG'
        },
        'DXB': {
            'name': 'Dubai International Airport', 
            'city': 'Dubai', 
            'country': 'UAE',
            'icao': 'OMDB'
        }
    }
    return airports.get(airport_code, {
        'name': 'Unknown Airport', 
        'city': 'Unknown', 
        'country': 'Unknown',
        'icao': 'XXXX'
    })

def generate_random_cryptos(count=5):
    crypto_names = [
        ('ECOG', 'EcoGreen', 'Sustainable blockchain for green initiatives'),
        ('SOLAR', 'SolarCoin', 'Token for solar energy production'),
        ('CARB', 'CarbonCredit', 'Digital carbon credit trading'),
        ('TREE', 'TreeToken', 'Tokenized tree planting and conservation'),
        ('WIND', 'WindEnergy', 'Wind farm energy tokenization'),
        ('OCEAN', 'OceanClean', 'Ocean cleanup and conservation token'),
        ('BIO', 'BioDiversity', 'Biodiversity preservation token'),
        ('RECYCLE', 'RecycleChain', 'Recycling incentive token'),
        ('WATER', 'CleanWater', 'Clean water access token'),
        ('ECO', 'EcoVerse', 'Native EcoVerse ecosystem token')
    ]
    
    random_cryptos = []
    selected = random.sample(crypto_names, min(count, len(crypto_names)))
    
    for symbol, name, description in selected:
        price = random.uniform(0.1, 100)
        change = random.uniform(-10, 20)
        
        random_cryptos.append({
            'symbol': symbol,
            'name': name,
            'current_price': price,
            'hourly_change': change,
            'description': description,
            'market_cap': price * random.uniform(1000000, 10000000),
            'volume': random.uniform(100000, 1000000)
        })
    
    return random_cryptos

def create_random_crypto(symbol, name):
    price = random.uniform(0.1, 100)
    volatility = random.uniform(0.02, 0.1)
    
    descriptions = [
        f"A sustainable cryptocurrency focusing on {name.lower()} initiatives",
        f"Green blockchain solution for {name.lower()} projects",
        f"Tokenized environmental asset for {name.lower()}",
        f"Eco-friendly crypto supporting {name.lower()} sustainability"
    ]
    
    crypto = CryptoMarket(
        symbol=symbol,
        name=name,
        current_price=price,
        hourly_change=0,
        daily_change=0,
        market_cap=price * random.uniform(1000000, 10000000),
        volume=random.uniform(100000, 1000000),
        description=random.choice(descriptions),
        volatility=volatility
    )
    
    db.session.add(crypto)
    db.session.commit()
    
    return crypto

def generate_story_with_gpt(user, story_type):
    save = EcoWorldSave.query.filter_by(user_id=user.id).first()
    
    prompt = f"""
    Create a personalized eco-story for {user.username}, the Eco-Guardian.
    
    User Profile:
    - Level: {user.level}
    - Avatar Level: {user.avatar_level}
    - Eco Score: {user.eco_score}
    - City: {save.city_name if save else 'EcoCity'}
    - Tokens: {user.token_balance}
    
    Story Type: {story_type}
    
    Generate a script with 4 scenes in this format:
    
    [SCENE 1 - INTRODUCTION]
    NARRATOR: "Welcome to the story of {user.username}, the Eco-Guardian!"
    VISUAL: {user.username}'s avatar appears with glowing green aura.
    
    [SCENE 2 - THE JOURNEY]
    NARRATOR: "This week in {save.city_name if save else 'EcoCity'}, our hero accomplished amazing feats..."
    VISUAL: Animated scenes showing recent eco-actions.
    
    [SCENE 3 - THE IMPACT]
    NARRATOR: "Together, they saved 150kg of CO₂ and planted 12 trees!"
    VISUAL: Growing trees, clean energy effects, happy citizens.
    
    [SCENE 4 - INSPIRATION]
    NARRATOR: "Every action counts. Your journey inspires others!"
    VISUAL: Epic wide shot of sustainable city, avatar standing tall.
    
    Make it inspiring, personalized, and eco-focused.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative storyteller specializing in sustainability narratives."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.8
        )
        
        script = response.choices[0].message.content
        visuals = [
            {
                "scene": 1,
                "description": f"Avatar introduction with glowing effects",
                "effects": ["glow", "particles"],
                "duration": 15
            },
            {
                "scene": 2,
                "description": f"Journey through sustainable city",
                "effects": ["time_lapse", "growth"],
                "duration": 20
            },
            {
                "scene": 3,
                "description": f"Impact visualization with trees and clean energy",
                "effects": ["particles", "absorption"],
                "duration": 15
            },
            {
                "scene": 4,
                "description": f"Inspiring panoramic view",
                "effects": ["bloom", "cinematic"],
                "duration": 10
            }
        ]
        
        return {
            'title': f"{user.username}'s {story_type.replace('_', ' ').title()} Story",
            'script': script,
            'visuals': visuals
        }
        
    except Exception as e:
        return {
            'title': f"{user.username}'s Eco Journey",
            'script': """[SCENE 1 - INTRODUCTION]
NARRATOR: "Welcome to the story of admin, the Eco-Guardian!"
VISUAL: admin's avatar appears with glowing green aura.

[SCENE 2 - THE JOURNEY]
NARRATOR: "This week in EcoCity, our hero accomplished amazing feats..."
VISUAL: Animated scenes showing recent eco-actions.

[SCENE 3 - THE IMPACT]
NARRATOR: "Together, they saved 150kg of CO₂ and planted 12 trees!"
VISUAL: Growing trees, clean energy effects, happy citizens.

[SCENE 4 - INSPIRATION]
NARRATOR: "Every action counts. Your journey inspires others!"
VISUAL: Epic wide shot of sustainable city, avatar standing tall.""",
            'visuals': [
                {"scene": 1, "description": "Avatar introduction", "effects": ["glow"], "duration": 15},
                {"scene": 2, "description": "City journey", "effects": ["time_lapse"], "duration": 20},
                {"scene": 3, "description": "Impact visualization", "effects": ["particles"], "duration": 15},
                {"scene": 4, "description": "Inspiring view", "effects": ["bloom"], "duration": 10}
            ]
        }

def create_silent_video(story):
    try:
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, f"story_{story.id}.mp4")
        from moviepy.editor import ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips
        
        clips = []
        visuals = json.loads(story.visuals)
        
        for i, visual in enumerate(visuals[:4]):
            duration = visual.get('duration', 10)
            clip = ColorClip(size=(1280, 720), color=(0, 100, 0), duration=duration)
            txt = TextClip(f"Scene {i+1}", fontsize=40, color='white')
            txt = txt.set_position('center').set_duration(duration)
            
            scene = CompositeVideoClip([clip, txt])
            clips.append(scene)
        
        if clips:
            final = concatenate_videoclips(clips)
            final.write_videofile(output_path, fps=24, codec='libx264')
            return output_path
        
        return None
        
    except Exception as e:
        print(f"Video creation error: {e}")
        return None

def determine_story_mood(script):
    script_lower = script.lower()
    heroic_keywords = ['amazing', 'success', 'achieved', 'saved', 'hero', 'inspiring', 
                      'celebrate', 'victory', 'triumph', 'wonderful', 'excellent', 'great']
    
    unaccomplished_keywords = ['failed', 'struggle', 'difficult', 'challenge', 'need', 
                              'must', 'should', 'unfortunately', 'however', 'but', 'although']
    
    heroic_count = sum(1 for word in heroic_keywords if word in script_lower)
    unaccomplished_count = sum(1 for word in unaccomplished_keywords if word in script_lower)

    if 'co₂ saved' in script_lower or 'trees planted' in script_lower:
        import re
        co2_match = re.search(r'(\d+)kg of co₂', script_lower)
        trees_match = re.search(r'(\d+) trees', script_lower)
        
        if co2_match and trees_match:
            co2_saved = int(co2_match.group(1))
            trees_planted = int(trees_match.group(1))
            if co2_saved > 100 or trees_planted > 10:
                return 'heroic'
    if heroic_count > unaccomplished_count:
        return 'heroic'
    elif unaccomplished_count > heroic_count:
        return 'unaccomplished'
    else:
        return 'heroic' if 'amazing' in script_lower or 'success' in script_lower else 'unaccomplished'

def add_background_music(video_duration, mood='heroic'):
    try:
        static_path = os.path.join(os.path.dirname(__file__), 'static')
        if not os.path.exists(static_path):
            print(f"⚠️ Static folder not found at {static_path}")
            return None
        if mood == 'heroic':
            music_files = ['h1.mp3', 'h2.mp3', 'h3.mp3']
        else:
            music_files = ['u1.mp3', 'u2.mp3', 'u3.mp3']
        
        available_files = []
        for file in music_files:
            file_path = os.path.join(static_path, file)
            if os.path.exists(file_path):
                available_files.append(file_path)
        
        if not available_files:
            print(f"⚠️ No {mood} music files found in static folder")
            return None

        selected_music = random.choice(available_files)
        print(f"Selected music: {os.path.basename(selected_music)}")
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        audio_clip = AudioFileClip(selected_music)
        audio_clip = audio_clip.volumex(0.8)
        if audio_clip.duration < video_duration:
            loops_needed = int(video_duration / audio_clip.duration) + 1
            audio_clips = [audio_clip] * loops_needed
            from moviepy.audio.AudioClip import concatenate_audioclips
            audio_clip = concatenate_audioclips(audio_clips)
        
        audio_clip = audio_clip.subclip(0, video_duration)
        audio_clip = audio_clip.audio_fadein(2).audio_fadeout(3)
        return audio_clip
        
    except Exception as e:
        print(f"⚠️ Error loading background music: {e}")
        return None

def generate_qr_code(data, size=100):
    try:
        import qrcode
        from io import BytesIO
        import base64
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

def init_greentoken_market():
    default_cryptos = [
        ('ECOG', 'EcoGreen', 'Sustainable blockchain token', 5.0),
        ('SOLAR', 'SolarCoin', 'Solar energy tokenization', 2.5),
        ('CARB', 'CarbonCredit', 'Digital carbon credits', 10.0),
        ('ECO', 'EcoVerse', 'Native ecosystem token', 1.0)
    ]
    
    for symbol, name, desc, price in default_cryptos:
        if not CryptoMarket.query.filter_by(symbol=symbol).first():
            crypto = CryptoMarket(
                symbol=symbol,
                name=name,
                current_price=price,
                hourly_change=0,
                daily_change=0,
                market_cap=price * 1000000,
                volume=100000,
                description=desc,
                volatility=0.05
            )
            db.session.add(crypto)
    
    db.session.commit()
    print("tgreen market init")
def init_city_builder_tables():
    with app.app_context():
        pass

@app.template_filter('format_number')
def format_number_filter(value):
    try:
        if value is None:
            return "0"
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)

@app.route('/ultra')
@login_required
def get_ultra_certification():
    existing_ultra = Certification.query.filter_by(
        user_id=current_user.id,
        level='ultra'
    ).first()
    
    if not existing_ultra:
        cert_id = f"ECV-ULTRA-{current_user.id:06d}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        cert = Certification(
            user_id=current_user.id,
            certification_type='ultra_legend',
            title='ULTRA LEGEND',
            level='ultra',
            points_required=0,
            user_points=current_user.eco_score,
            description='Ultimate sustainability knowledge champion',
            ai_generated_text='You have proven yourself as a true sustainability master! The ULTRA LEGEND title is reserved for those with exceptional knowledge and dedication to our planet.',
            certificate_id=cert_id,
            qr_data=f'https://ecoverse.com/verify/{cert_id}',
            valid_until=datetime.utcnow() + timedelta(days=365),
            earned_at=datetime.utcnow(),
            score=100.0
        )
        
        db.session.add(cert)
        tokens_earned = 10000
        current_user.token_balance += tokens_earned
        action = EcoAction(
            user_id=current_user.id,
            action_type='ultra_legend_achieved',
            co2_saved=5000,
            tokens_earned=tokens_earned,
            created_at=datetime.utcnow()
        )
        db.session.add(action)
        
        db.session.commit()
        return redirect(url_for('certifications'))
    else:
        return redirect(url_for('certifications'))

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

def init_db():
    with app.app_context():
        db.create_all()
        init_greentoken_market()
        init_city_builder_tables()
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', 'ur key here'))
        if CertificationRequirement.query.count() == 0:
            requirements = get_certification_requirements_new()
            
            for req in requirements:
                cert_req = CertificationRequirement(
                    certification_type='sustainability',
                    level=req['level'],
                    points_required=req['points_required'],
                    description=req['description'],
                    badge_icon=req['badge_icon'],
                    color_scheme=req['color_scheme'],
                    ai_questions_count=req.get('quiz_questions', 0),
                    passing_score=req.get('passing_score', 0)
                )
                db.session.add(cert_req)

        ultra_question_count = CertificationQuestion.query.filter_by(level='ultra').count()
        if ultra_question_count == 0:
            print("Generating Ultra Legend certification questions...")
            questions = generate_certification_questions('ultra')
            print(f"Generated {len(questions)} questions for Ultra Legend")

        if Building.query.count() == 0:
            default_buildings = [
                Building(name="Residential House", category="residential", cost=100, 
                        population_capacity=10, happiness_effect=5, carbon_impact=2,
                        energy_consumption=5, water_consumption=3, icon="🏠", 
                        description="Basic housing for citizens"),
                
                Building(name="Solar Panel", category="utility", cost=150,
                        energy_production=20, happiness_effect=3, carbon_impact=-5,
                        icon="☀️", description="Clean energy production"),
                
                Building(name="Water Well", category="utility", cost=120,
                        water_production=15, happiness_effect=2, carbon_impact=-3,
                        icon="💧", description="Clean water source"),
                
                Building(name="Recycling Center", category="industrial", cost=200,
                        waste_production=-10, happiness_effect=4, carbon_impact=-8,
                        energy_consumption=3, icon="♻️", description="Process waste into resources", 
                        unlock_level=2),
                
                Building(name="Community Garden", category="green", cost=80,
                        food_production=10, happiness_effect=8, carbon_impact=-4,
                        water_consumption=2, icon="🌱", description="Local food production"),
                
                Building(name="Wind Turbine", category="utility", cost=300,
                        energy_production=35, happiness_effect=6, carbon_impact=-10,
                        icon="🌬️", description="Renewable energy", unlock_level=3),
                
                Building(name="Eco School", category="commercial", cost=250,
                        population_capacity=5, happiness_effect=15, carbon_impact=-6,
                        energy_consumption=8, water_consumption=4, icon="🏫", 
                        description="Education center", unlock_level=2),
                
                Building(name="Bike Lane", category="green", cost=60,
                        happiness_effect=10, carbon_impact=-3, icon="🚲", 
                        description="Sustainable transportation"),
                
                Building(name="Vertical Farm", category="industrial", cost=400,
                        food_production=30, water_consumption=5, happiness_effect=7, 
                        carbon_impact=-12, energy_consumption=10, icon="🏢", 
                        description="Space-efficient farming", unlock_level=4),
                
                Building(name="Biodome", category="green", cost=500,
                        happiness_effect=20, carbon_impact=-15, biodiversity_effect=10,
                        energy_consumption=15, water_consumption=8, icon="🌍", 
                        description="Protected ecosystem", unlock_level=5)
            ]
            
            for building_data in default_buildings:
                db.session.add(building_data)

        if User.query.filter_by(username='admin').first() is None:
            admin = User(username='admin', email='admin@ecoverse.com')
            admin.set_password('admin123')
            admin.token_balance = 1000.0
            admin.eco_score = 100
            admin.completed_onboarding = True
            db.session.add(admin)
        
        if User.query.filter_by(username='demo').first() is None:
            demo = User(username='demo', email='demo@ecoverse.com')
            demo.set_password('demo123')
            demo.token_balance = 2000.0
            demo.eco_score = 200
            demo.avatar_level = 3
            demo.avatar_xp = 150
            demo.avatar_skin = 'green'
            demo.avatar_hair = 'default'
            demo.avatar_outfit = 'basic'
            demo.avatar_aura = 'none'
            demo.avatar_accessories = '[]'
            demo.level = 3
            demo.completed_onboarding = True
            db.session.add(demo)
        
        try:
            db.session.commit()
            print("PLEASE GO THROUGH README.txt BEFORE USING THE APP.")
        except Exception as e:
            db.session.rollback()
            print(f"error: {e}")

app.jinja_env.filters['format_number'] = format_number_filter
init_db()
app.run(debug=True, port=5000)