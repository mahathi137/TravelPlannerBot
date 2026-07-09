"""
=============================================================================
  TravelBot — IBM Watsonx.ai Powered Smart Travel Planning Agent
  Backend: Flask + ibm-watsonx-ai SDK (Granite models)
  Version: 2.0  |  Production-Ready
=============================================================================
"""

import os
import re
import time
import random
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

# ─────────────────────────────────────────────────────────────────────────────
#  AGENT INSTRUCTIONS
# ─────────────────────────────────────────────────────────────────────────────
AGENT_INSTRUCTIONS = {
    "name": "TravelBot",
    "persona": (
        "You are TravelBot, an expert AI travel planning assistant powered by IBM Watsonx.ai. "
        "You provide highly detailed, destination-specific, and personalised travel advice. "
        "You always tailor responses to the traveller's budget, travel style, group size, "
        "preferred season, and interests. You are enthusiastic, knowledgeable, and practical."
    ),
    "default_travel_style": "balanced",
    "emphasise_indian_destinations": True,
    "indian_destination_context": (
        "You have deep expertise in Indian travel destinations including: "
        "Goa (beaches, nightlife, Portuguese heritage), Kerala (backwaters, tea gardens, Ayurveda), "
        "Rajasthan (forts, deserts, heritage hotels), Ladakh (high-altitude lakes, monasteries, adventure), "
        "Himachal Pradesh (Manali, Shimla, Dharamshala, Spiti Valley), "
        "Uttarakhand (Rishikesh, Haridwar, Kedarnath, Auli), "
        "Andaman & Nicobar (pristine beaches, scuba diving, coral reefs), "
        "Northeast India (Meghalaya, Sikkim, Assam, Arunachal Pradesh), "
        "Hyderabad (Charminar, Golconda Fort, Ramoji Film City, biryani), "
        "Mumbai (Marine Drive, Gateway of India, Bollywood, street food), "
        "Delhi (Red Fort, Qutub Minar, Chandni Chowk, museums), "
        "Varanasi (Ganga Aarti, ghats, temples, spiritual tourism), "
        "Coorg (coffee estates, waterfalls, homestays), "
        "Ooty (Nilgiri hills, tea gardens, Botanical Garden), "
        "Pondicherry (French Quarter, beaches, Auroville). "
        "Always suggest local cuisine, hidden gems, best hotels by budget tier, "
        "transport options, and practical travel tips specific to each destination."
    ),
    "tone": "friendly_professional",
    "use_emojis": True,
    "language_style": (
        "Be conversational but informative. Structure responses clearly with headings, "
        "bullet points, and day-wise breakdowns where appropriate. "
        "Always include practical details: costs in INR, travel time between places, "
        "best time to visit, local transport options, and accommodation suggestions."
    ),
    "safety_rules": [
        "Always verify visa and travel advisory requirements for international destinations.",
        "Recommend travel insurance for trips over 5 days or any international travel.",
        "For adventure activities, always mention safety precautions and certified operators.",
        "Prices mentioned are approximate 2025–2026 estimates and may vary by season.",
        "Always suggest keeping emergency contacts and copies of documents.",
    ],
    "response_format": (
        "For itineraries: use Day-wise format with Morning / Afternoon / Evening breakdown. "
        "For budget queries: show itemised cost breakdown. "
        "For destination queries: cover Top Attractions, Best Hotels, Local Food, Transport, Tips. "
        "Always end with a motivational travel quote or tip."
    ),
    "capabilities": [
        "Personalised day-by-day travel itineraries for any Indian & global destination",
        "Realistic trip budget estimation with itemised breakdown",
        "Hotel recommendations across budget, mid-range, and luxury tiers",
        "Restaurant and local cuisine recommendations",
        "Transportation planning (trains, flights, road trips, local transport)",
        "Weather and best season to visit guidance",
        "Packing list generation based on destination and season",
        "Group and family trip planning",
        "Adventure travel and offbeat destination discovery",
        "Visa and travel document guidance",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
#  DESTINATION KNOWLEDGE BASE — realistic 2025-26 Indian travel data
# ─────────────────────────────────────────────────────────────────────────────
DESTINATION_DATA = {
    "goa": {
        "region": "West India", "state": "Goa",
        "best_months": "November – February",
        "weather": "Sunny, 25–32°C, sea breeze",
        "top_attractions": ["Baga Beach", "Anjuna Flea Market", "Dudhsagar Waterfalls",
                            "Old Goa Churches", "Palolem Beach", "Spice Plantations"],
        "local_food": ["Prawn Balchão", "Fish Curry Rice", "Bebinca", "Feni", "Cafreal"],
        "transport": "Rented scooter (₹300–500/day), taxi, local bus",
        "hotels": {"budget": "₹800–₹1,500/night", "mid": "₹2,500–₹5,000/night", "luxury": "₹8,000–₹25,000/night"},
        "daily_costs": {"budget": 2500, "balanced": 5500, "luxury": 18000, "adventure": 4000, "family": 7000},
        "airport": "Dabolim / Mopa International Airport",
        "tips": ["Book beach shacks in advance Nov–Jan", "Avoid rainy season June–September",
                 "North Goa for nightlife, South Goa for peace", "Carry cash — many small shops"],
    },
    "kerala": {
        "region": "South India", "state": "Kerala",
        "best_months": "September – March",
        "weather": "Tropical, 22–34°C, humid",
        "top_attractions": ["Alleppey Backwaters", "Munnar Tea Gardens", "Thekkady Wildlife",
                            "Kovalam Beach", "Fort Kochi", "Wayanad Forests"],
        "local_food": ["Kerala Sadya", "Appam with Stew", "Karimeen Pollichathu", "Prawn Moilee", "Puttu & Kadala"],
        "transport": "KSRTC buses, private taxis, auto-rickshaws, houseboat",
        "hotels": {"budget": "₹700–₹1,500/night", "mid": "₹2,000–₹5,000/night", "luxury": "₹6,000–₹30,000/night (resort)"},
        "daily_costs": {"budget": 2200, "balanced": 5000, "luxury": 16000, "adventure": 3500, "family": 6500},
        "airport": "Cochin / Trivandrum / Calicut International",
        "tips": ["Houseboat rates negotiable off-season", "Carry light cotton clothes",
                 "Onam festival (Aug–Sep) is spectacular", "Ayurveda packages widely available"],
    },
    "rajasthan": {
        "region": "North India", "state": "Rajasthan",
        "best_months": "October – March",
        "weather": "Dry, 10–28°C (winter), very hot in summer",
        "top_attractions": ["Amber Fort Jaipur", "City Palace Udaipur", "Jaisalmer Fort",
                            "Mehrangarh Fort Jodhpur", "Pushkar Lake", "Ranthambore Tiger Reserve"],
        "local_food": ["Dal Bati Churma", "Laal Maas", "Gatte ki Sabzi", "Ghewar", "Ker Sangri"],
        "transport": "Private cab ideal for golden triangle, trains between cities",
        "hotels": {"budget": "₹600–₹1,200/night", "mid": "₹2,000–₹6,000/night", "luxury": "₹8,000–₹50,000/night (heritage)"},
        "daily_costs": {"budget": 2000, "balanced": 5000, "luxury": 20000, "adventure": 3500, "family": 7500},
        "airport": "Jaipur / Udaipur / Jodhpur",
        "tips": ["Pre-book heritage hotels months in advance", "Carry warm layers for winter nights",
                 "Bargain at local bazaars", "Camel safari is a must in Jaisalmer"],
    },
    "ladakh": {
        "region": "North India", "state": "J&K / Ladakh UT",
        "best_months": "June – September",
        "weather": "Cold, dry, 5–20°C in summer, sub-zero in winter",
        "top_attractions": ["Pangong Tso Lake", "Nubra Valley", "Hemis Monastery",
                            "Magnetic Hill", "Khardung La Pass", "Tso Moriri"],
        "local_food": ["Thukpa", "Momos", "Butter Tea", "Skyu", "Chhang (local barley beer)"],
        "transport": "Shared jeep/taxi, self-drive bike (experienced only), Royal Enfield rental",
        "hotels": {"budget": "₹800–₹1,500/night", "mid": "₹2,500–₹6,000/night", "luxury": "₹7,000–₹20,000/night"},
        "daily_costs": {"budget": 2800, "balanced": 6000, "luxury": 16000, "adventure": 5500, "family": 8000},
        "airport": "Kushok Bakula Rimpochee Airport, Leh",
        "tips": ["Acclimatise for 2 days on arrival", "Inner Line Permit required for some areas",
                 "Carry layers — temperatures drop sharply at night", "Book accommodation well in advance"],
    },
    "manali": {
        "region": "North India", "state": "Himachal Pradesh",
        "best_months": "Oct–Nov (snow), Mar–Jun (trekking), Dec–Feb (skiing)",
        "weather": "Temperate to cold, -5°C to 20°C depending on season",
        "top_attractions": ["Solang Valley", "Rohtang Pass", "Hadimba Temple",
                            "Old Manali Market", "Beas Kund Trek", "Kasol (nearby)"],
        "local_food": ["Siddu", "Dham", "Trout Fish", "Chha Gosht", "Aktori"],
        "transport": "HRTC bus from Delhi (12 hrs), private taxi, local autos",
        "hotels": {"budget": "₹600–₹1,200/night", "mid": "₹2,000–₹5,000/night", "luxury": "₹6,000–₹18,000/night"},
        "daily_costs": {"budget": 2200, "balanced": 4500, "luxury": 14000, "adventure": 4000, "family": 6000},
        "airport": "Kullu-Manali Airport (Bhuntar, ~50 km)",
        "tips": ["Rohtang Pass permit required (₹500)", "Carry warm layers even in summer",
                 "Avoid peak season July–Aug for crowds", "Book Rohtang jeeps in advance"],
    },
    "andaman": {
        "region": "Islands", "state": "Andaman & Nicobar Islands",
        "best_months": "October – May",
        "weather": "Tropical, 23–30°C, humid",
        "top_attractions": ["Radhanagar Beach (Asia's Best)", "Cellular Jail", "Neil Island",
                            "Baratang Limestone Caves", "Havelock Island", "Scuba Diving Ross Island"],
        "local_food": ["Fresh Seafood", "Fish Tikka", "Coconut Prawn Curry", "Grilled Lobster"],
        "transport": "Government ferries between islands (book in advance), local autos",
        "hotels": {"budget": "₹1,000–₹2,000/night", "mid": "₹3,000–₹7,000/night", "luxury": "₹10,000–₹30,000/night"},
        "daily_costs": {"budget": 3000, "balanced": 7000, "luxury": 20000, "adventure": 6000, "family": 9000},
        "airport": "Veer Savarkar International Airport, Port Blair",
        "tips": ["Book ferry tickets well in advance", "Scuba certification possible on island",
                 "December–February is peak season — book early", "ATMs limited — carry cash"],
    },
    "hyderabad": {
        "region": "South India", "state": "Telangana",
        "best_months": "October – February",
        "weather": "Moderate, 15–35°C, less humid",
        "top_attractions": ["Charminar", "Golconda Fort", "Ramoji Film City",
                            "Hussain Sagar Lake", "Salar Jung Museum", "Birla Mandir"],
        "local_food": ["Hyderabadi Biryani", "Haleem", "Qubani ka Meetha", "Irani Chai", "Lukhmi"],
        "transport": "Metro rail, Uber/Ola, TSRTC buses",
        "hotels": {"budget": "₹700–₹1,500/night", "mid": "₹2,000–₹5,000/night", "luxury": "₹6,000–₹20,000/night"},
        "daily_costs": {"budget": 1800, "balanced": 4000, "luxury": 13000, "adventure": 3000, "family": 5500},
        "airport": "Rajiv Gandhi International Airport",
        "tips": ["Biryani at Paradise or Bawarchi is a must", "Golconda sound & light show evenings",
                 "Ramoji Film City needs a full day", "Explore Laad Bazaar for bangles"],
    },
    "delhi": {
        "region": "North India", "state": "Delhi NCR",
        "best_months": "October – March",
        "weather": "Extreme — very hot summers, cold winters, 5–45°C range",
        "top_attractions": ["Red Fort", "Qutub Minar", "India Gate", "Humayun's Tomb",
                            "Chandni Chowk", "Lodhi Garden", "Akshardham Temple"],
        "local_food": ["Chole Bhature", "Butter Chicken (origin)", "Paranthe Wali Gali",
                       "Jalebi Falooda", "Gol Gappa", "Nihari"],
        "transport": "Delhi Metro (excellent), auto-rickshaw, Uber/Ola, e-rickshaw",
        "hotels": {"budget": "₹700–₹1,500/night", "mid": "₹2,500–₹6,000/night", "luxury": "₹8,000–₹30,000/night"},
        "daily_costs": {"budget": 2000, "balanced": 5000, "luxury": 15000, "adventure": 3000, "family": 7000},
        "airport": "Indira Gandhi International Airport (T1/T2/T3)",
        "tips": ["Use Metro to avoid traffic", "Old Delhi tour is best in morning",
                 "Pollution can be severe Oct–Jan — carry mask", "Beware of tourist touts"],
    },
    "mumbai": {
        "region": "West India", "state": "Maharashtra",
        "best_months": "November – February",
        "weather": "Tropical, 20–35°C, very humid in monsoon",
        "top_attractions": ["Gateway of India", "Marine Drive", "Elephanta Caves",
                            "Dharavi Tour", "Juhu Beach", "Film City", "Siddhivinayak Temple"],
        "local_food": ["Vada Pav", "Pav Bhaji", "Mumbai Street Biryani", "Misal Pav",
                       "Bhel Puri", "Bandra Kebabs"],
        "transport": "Mumbai Local Train (fastest), Metro, auto-rickshaw, Uber",
        "hotels": {"budget": "₹1,000–₹2,000/night", "mid": "₹3,000–₹7,000/night", "luxury": "₹10,000–₹40,000/night"},
        "daily_costs": {"budget": 2500, "balanced": 6000, "luxury": 20000, "adventure": 4000, "family": 8000},
        "airport": "Chhatrapati Shivaji Maharaj International Airport",
        "tips": ["Mumbai never sleeps — food available 24/7", "Avoid monsoon season Jun–Sep for sightseeing",
                 "Local trains during peak hours are very crowded", "CST is a UNESCO World Heritage Site"],
    },
    "varanasi": {
        "region": "North India", "state": "Uttar Pradesh",
        "best_months": "October – March",
        "weather": "Extreme — hot summers, pleasant winters, 5–42°C",
        "top_attractions": ["Dashashwamedh Ghat Aarti", "Kashi Vishwanath Temple", "Sarnath",
                            "Assi Ghat", "Manikarnika Ghat", "Morning Boat Ride on Ganga"],
        "local_food": ["Banarasi Paan", "Tamatar Chaat", "Kachori Sabzi", "Malaiyyo (winter)", "Lassi"],
        "transport": "Auto-rickshaw, e-rickshaw, cycle-rickshaw in old city",
        "hotels": {"budget": "₹500–₹1,200/night", "mid": "₹1,500–₹4,000/night", "luxury": "₹5,000–₹15,000/night"},
        "daily_costs": {"budget": 1500, "balanced": 3500, "luxury": 10000, "adventure": 2500, "family": 5000},
        "airport": "Lal Bahadur Shastri International Airport",
        "tips": ["Sunrise boat ride is life-changing", "Ganga Aarti at Dashashwamedh is at 7 PM daily",
                 "Explore narrow lanes of Old Varanasi on foot", "Spiritual energy is very powerful here"],
    },
    "jaipur": {
        "region": "North India", "state": "Rajasthan",
        "best_months": "October – March",
        "weather": "Cool mornings, sunny afternoons, pleasant evenings",
        "top_attractions": ["Amber Fort", "Hawa Mahal", "City Palace", "Jantar Mantar"],
        "local_food": ["Dal Baati Churma", "Pyaz Kachori", "Ghevar", "Mawa Kachori"],
        "transport": "Metro, taxis, auto-rickshaws, private cabs",
        "hotels": {"budget": "₹800–₹1,500/night", "mid": "₹2,000–₹5,500/night", "luxury": "₹8,000–₹30,000/night"},
        "daily_costs": {"budget": 2200, "balanced": 4800, "luxury": 17000, "adventure": 3200, "family": 7000},
        "airport": "Jaipur International Airport",
        "tips": ["Wear comfortable shoes for forts and bazaars", "Book heritage stays early", "Try local street food in the evening"],
    },
    "udaipur": {
        "region": "North India", "state": "Rajasthan",
        "best_months": "October – March",
        "weather": "Pleasant, mild winters and warm days",
        "top_attractions": ["City Palace", "Lake Pichola", "Jag Mandir", "Saheliyon ki Bari"],
        "local_food": ["Gatte ki Sabzi", "Mirchi Bada", "Kachori", "Malpua"],
        "transport": "Auto-rickshaws, taxis, walking in the old city",
        "hotels": {"budget": "₹700–₹1,400/night", "mid": "₹2,000–₹5,000/night", "luxury": "₹7,500–₹25,000/night"},
        "daily_costs": {"budget": 2100, "balanced": 4600, "luxury": 16000, "adventure": 3000, "family": 6800},
        "airport": "Maharana Pratap Airport",
        "tips": ["Sunset boat ride is worth it", "Stay near the lake for easy access", "Book palace hotels in advance"],
    },
    "dubai": {
        "region": "Middle East", "state": "Dubai",
        "best_months": "November – March",
        "weather": "Warm and sunny, 20–35°C",
        "top_attractions": ["Burj Khalifa", "Dubai Mall", "Desert Safari", "Palm Jumeirah"],
        "local_food": ["Shawarma", "Mandi", "Arabic sweets", "Seafood"],
        "transport": "Metro, taxis, ride-hailing services",
        "hotels": {"budget": "₹8,000–₹15,000/night", "mid": "₹15,000–₹30,000/night", "luxury": "₹35,000+/night"},
        "daily_costs": {"budget": 12000, "balanced": 22000, "luxury": 50000, "adventure": 18000, "family": 28000},
        "airport": "Dubai International Airport",
        "tips": ["Carry light cotton clothing", "Book desert activities in advance", "Public transport is efficient and clean"],
    },
    "singapore": {
        "region": "Southeast Asia", "state": "Singapore",
        "best_months": "February – April",
        "weather": "Warm and humid, 25–32°C",
        "top_attractions": ["Gardens by the Bay", "Marina Bay Sands", "Sentosa", "Chinatown"],
        "local_food": ["Hainanese chicken rice", "Laksa", "Satay", "Chili crab"],
        "transport": "MRT, buses, rideshares",
        "hotels": {"budget": "₹7,000–₹12,000/night", "mid": "₹12,000–₹25,000/night", "luxury": "₹30,000+/night"},
        "daily_costs": {"budget": 10000, "balanced": 20000, "luxury": 45000, "adventure": 14000, "family": 25000},
        "airport": "Changi Airport",
        "tips": ["Plan for humid weather", "Reserve popular attractions early", "Use contactless payment widely"],
    },
    "paris": {
        "region": "Europe", "state": "France",
        "best_months": "April – June",
        "weather": "Mild and pleasant, 10–25°C",
        "top_attractions": ["Eiffel Tower", "Louvre", "Seine River", "Montmartre"],
        "local_food": ["Croissants", "Cheese boards", "Macarons", "Baguettes"],
        "transport": "Metro, buses, walking",
        "hotels": {"budget": "₹10,000–₹18,000/night", "mid": "₹18,000–₹35,000/night", "luxury": "₹40,000+/night"},
        "daily_costs": {"budget": 12000, "balanced": 22000, "luxury": 50000, "adventure": 15000, "family": 28000},
        "airport": "Charles de Gaulle Airport",
        "tips": ["Book museum tickets in advance", "Walk whenever possible", "Carry a light jacket for evenings"],
    },
    "bali": {
        "region": "Southeast Asia", "state": "Indonesia",
        "best_months": "April – October",
        "weather": "Warm, tropical, 24–31°C",
        "top_attractions": ["Uluwatu", "Ubud Rice Terraces", "Seminyak", "Nusa Penida"],
        "local_food": ["Nasi Goreng", "Satay", "Babi Guling", "Fresh seafood"],
        "transport": "Scooters, private drivers, ride-hailing",
        "hotels": {"budget": "₹3,000–₹7,000/night", "mid": "₹8,000–₹20,000/night", "luxury": "₹25,000+/night"},
        "daily_costs": {"budget": 6000, "balanced": 14000, "luxury": 30000, "adventure": 10000, "family": 18000},
        "airport": "Ngurah Rai International Airport",
        "tips": ["Book villas early in peak season", "Use sunscreen and stay hydrated", "Traffic can be slow in the evenings"],
    },
    "rishikesh": {
        "region": "North India", "state": "Uttarakhand",
        "best_months": "September – November",
        "weather": "Cool mornings, warm afternoons, breezy evenings",
        "top_attractions": ["Lakshman Jhula", "Triveni Ghat", "Neer Garh Waterfall", "Beatles Ashram"],
        "local_food": ["Aloo Puri", "Kebabs", "Momos", "Masala Chai"],
        "transport": "Buses, taxis, shared jeeps",
        "hotels": {"budget": "₹600–₹1,400/night", "mid": "₹1,800–₹4,000/night", "luxury": "₹6,000–₹15,000/night"},
        "daily_costs": {"budget": 1800, "balanced": 4000, "luxury": 12000, "adventure": 3500, "family": 5500},
        "airport": "Jolly Grant Airport, Dehradun",
        "tips": ["Riverfront cafes are best at sunset", "Book rafting packages with certified operators", "Carry warm clothes for evenings"],
    },
    "tokyo": {
        "region": "East Asia", "state": "Japan",
        "best_months": "March – May",
        "weather": "Mild to cool, 10–25°C",
        "top_attractions": ["Shibuya", "Senso-ji", "Akihabara", "Mount Fuji day trip"],
        "local_food": ["Sushi", "Ramen", "Tempura", "Matcha desserts"],
        "transport": "Subway, trains, buses",
        "hotels": {"budget": "₹8,000–₹15,000/night", "mid": "₹15,000–₹30,000/night", "luxury": "₹35,000+/night"},
        "daily_costs": {"budget": 11000, "balanced": 22000, "luxury": 50000, "adventure": 15000, "family": 28000},
        "airport": "Tokyo Haneda / Narita",
        "tips": ["Get a Suica/PASMO card", "Book popular restaurants ahead", "Many attractions open early"],
    },
    "maldives": {
        "region": "Indian Ocean", "state": "Maldives",
        "best_months": "November – April",
        "weather": "Sunny and warm, 27–32°C",
        "top_attractions": ["Overwater villas", "Snorkelling", "Sandbank picnics", "Sunset cruises"],
        "local_food": ["Grilled fish", "Coconut curries", "Seafood", "Fresh fruit"],
        "transport": "Speedboat or seaplane transfers",
        "hotels": {"budget": "₹15,000–₹25,000/night", "mid": "₹25,000–₹45,000/night", "luxury": "₹50,000+/night"},
        "daily_costs": {"budget": 20000, "balanced": 35000, "luxury": 70000, "adventure": 25000, "family": 45000},
        "airport": "Velana International Airport",
        "tips": ["Book transfers early", "Carry reef-safe sunscreen", "Resort packages often include meals"],
    },
    "london": {
        "region": "Europe", "state": "United Kingdom",
        "best_months": "May – September",
        "weather": "Cool, changeable, 12–24°C",
        "top_attractions": ["Tower of London", "British Museum", "Westminster", "Hyde Park"],
        "local_food": ["Fish and chips", "Sunday roast", "Afternoon tea", "Pub classics"],
        "transport": "Tube, buses, walking",
        "hotels": {"budget": "₹10,000–₹18,000/night", "mid": "₹18,000–₹35,000/night", "luxury": "₹40,000+/night"},
        "daily_costs": {"budget": 13000, "balanced": 24000, "luxury": 55000, "adventure": 16000, "family": 30000},
        "airport": "Heathrow Airport",
        "tips": ["Use an Oyster or contactless card", "Book major museums in advance", "Carry a compact umbrella"],
    },
    "shillong": {
        "region": "North-East India", "state": "Meghalaya",
        "best_months": "March – June",
        "weather": "Cool and misty, 10–24°C",
        "top_attractions": ["Elephant Falls", "Ward's Lake", "Laitlum Canyon", "Mawlynnong"],
        "local_food": ["Jadoh", "Pork ribs", "Rice dishes", "Local tea"],
        "transport": "Taxis, shared jeeps, local buses",
        "hotels": {"budget": "₹700–₹1,500/night", "mid": "₹2,000–₹4,000/night", "luxury": "₹5,500–₹12,000/night"},
        "daily_costs": {"budget": 2000, "balanced": 4500, "luxury": 12000, "adventure": 3000, "family": 6000},
        "airport": "Shillong Airport (Umroi)",
        "tips": ["Weather changes quickly", "Drive carefully on winding roads", "Try local momos and tea"],
    },
    "coorg": {
        "region": "South India", "state": "Karnataka",
        "best_months": "October – March",
        "weather": "Pleasant, green and misty",
        "top_attractions": ["Abbey Falls", "Raja's Seat", "Coffee plantations", "Dubare Elephant Camp"],
        "local_food": ["Pandi Curry", "Akki Roti", "Filter coffee", "Local snacks"],
        "transport": "Private cab, rented bike, local taxis",
        "hotels": {"budget": "₹800–₹1,600/night", "mid": "₹2,000–₹4,500/night", "luxury": "₹6,000–₹15,000/night"},
        "daily_costs": {"budget": 2200, "balanced": 4800, "luxury": 14000, "adventure": 3200, "family": 6500},
        "airport": "Mangalore International Airport",
        "tips": ["Carry light woollens for evenings", "Book homestays early", "Roads are scenic but winding"],
    },
    "ooty": {
        "region": "South India", "state": "Tamil Nadu",
        "best_months": "October – June",
        "weather": "Cool, misty and refreshing",
        "top_attractions": ["Nilgiri Mountain Railway", "Botanical Garden", "Doddabetta Peak", "Tea factories"],
        "local_food": ["Biryani", "South Indian breakfast", "Tea", "Chocolate pastries"],
        "transport": "Local taxis, buses, walking",
        "hotels": {"budget": "₹700–₹1,400/night", "mid": "₹2,000–₹4,500/night", "luxury": "₹6,000–₹18,000/night"},
        "daily_costs": {"budget": 2100, "balanced": 4500, "luxury": 13000, "adventure": 3000, "family": 6200},
        "airport": "Coimbatore Airport",
        "tips": ["Pack a light jacket", "Visit viewpoints early for clear skies", "The toy train is a memorable experience"],
    },
    "chennai": {
        "region": "South India", "state": "Tamil Nadu",
        "best_months": "November – February",
        "weather": "Warm and humid, 24–33°C",
        "top_attractions": ["Marina Beach", "Kapaleeshwarar Temple", "Fort St. George", "Mylapore"],
        "local_food": ["Filter coffee", "Idli", "Dosa", "Chettinad chicken"],
        "transport": "Metro, buses, auto-rickshaws",
        "hotels": {"budget": "₹800–₹1,600/night", "mid": "₹2,000–₹5,000/night", "luxury": "₹7,000–₹20,000/night"},
        "daily_costs": {"budget": 2200, "balanced": 4600, "luxury": 14000, "adventure": 3000, "family": 6500},
        "airport": "Chennai International Airport",
        "tips": ["Carry a bottle of water", "Try local seafood in the evening", "Traffic can be heavy"],
    },
    "bangalore": {
        "region": "South India", "state": "Karnataka",
        "best_months": "October – February",
        "weather": "Pleasant, mild and breezy",
        "top_attractions": ["Cubbon Park", "Bangalore Palace", "Nandi Hills", "UB City"],
        "local_food": ["Dosas", "Biryani", "Filter coffee", "Mangalorean fish curry"],
        "transport": "Metro, cabs, auto-rickshaws",
        "hotels": {"budget": "₹900–₹1,800/night", "mid": "₹2,500–₹5,500/night", "luxury": "₹7,500–₹20,000/night"},
        "daily_costs": {"budget": 2300, "balanced": 4800, "luxury": 15000, "adventure": 3200, "family": 6800},
        "airport": "Kempegowda International Airport",
        "tips": ["Use the metro for easy city travel", "Try cafés and breweries in the evening", "Peak traffic is around office hours"],
    },
    "thailand": {
        "region": "Southeast Asia", "state": "Thailand",
        "best_months": "November – February",
        "weather": "Warm and dry, 24–32°C",
        "top_attractions": ["Bangkok", "Chiang Mai", "Phuket", "Ayutthaya"],
        "local_food": ["Pad Thai", "Tom Yum", "Som Tam", "Mango sticky rice"],
        "transport": "Buses, trains, domestic flights",
        "hotels": {"budget": "₹2,500–₹5,000/night", "mid": "₹6,000–₹12,000/night", "luxury": "₹15,000+/night"},
        "daily_costs": {"budget": 7000, "balanced": 15000, "luxury": 35000, "adventure": 11000, "family": 20000},
        "airport": "Bangkok Suvarnabhumi Airport",
        "tips": ["Plan internal transport carefully", "Carry light clothing", "Street food is excellent but choose busy stalls"],
    },
    "darjeeling": {
        "region": "North India", "state": "West Bengal",
        "best_months": "March – May",
        "weather": "Cool, misty and scenic",
        "top_attractions": ["Tiger Hill", "Toy Train", "Batasia Loop", "Tea gardens"],
        "local_food": ["Momo", "Thukpa", "Tea", "Local pastries"],
        "transport": "Taxis, shared jeeps, toy train",
        "hotels": {"budget": "₹700–₹1,400/night", "mid": "₹2,000–₹4,000/night", "luxury": "₹5,500–₹12,000/night"},
        "daily_costs": {"budget": 1900, "balanced": 4200, "luxury": 11000, "adventure": 3000, "family": 5600},
        "airport": "Bagdogra Airport",
        "tips": ["Pack layers for chilly mornings", "Tea estates are best seen by taxi", "Book rooms early in holiday season"],
    },
    "srinagar": {
        "region": "North India", "state": "Jammu & Kashmir",
        "best_months": "March – October",
        "weather": "Cool and pleasant with lake views",
        "top_attractions": ["Dal Lake", "Shalimar Bagh", "Gulmarg", "Houseboats"],
        "local_food": ["Rogan Josh", "Yakhni", "Kehwa", "Wazwan"],
        "transport": "Houseboat, taxis, shikaras",
        "hotels": {"budget": "₹900–₹1,800/night", "mid": "₹2,500–₹5,500/night", "luxury": "₹7,000–₹20,000/night"},
        "daily_costs": {"budget": 2200, "balanced": 5000, "luxury": 15000, "adventure": 3300, "family": 7000},
        "airport": "Sheikh ul-Alam Airport",
        "tips": ["Carry warm layers for mornings", "Shikara rides are best at sunrise", "Check local advisories before travel"],
    },
    "hampi": {
        "region": "South India", "state": "Karnataka",
        "best_months": "November – February",
        "weather": "Dry, sunny and pleasant",
        "top_attractions": ["Virupaksha Temple", "Stone Chariot", "Matanga Hill", "Boulders"],
        "local_food": ["Dosa", "Idli", "Fresh juices", "Local thalis"],
        "transport": "Bikes, scooters, auto-rickshaws",
        "hotels": {"budget": "₹600–₹1,200/night", "mid": "₹1,800–₹3,500/night", "luxury": "₹5,000–₹10,000/night"},
        "daily_costs": {"budget": 1800, "balanced": 4000, "luxury": 12000, "adventure": 2800, "family": 5600},
        "airport": "Hubli Airport",
        "tips": ["Carry good walking shoes", "Visit temples early in the morning", "Stay close to the main heritage sites"],
    },
    "kodaikanal": {
        "region": "South India", "state": "Tamil Nadu",
        "best_months": "April – June",
        "weather": "Cool and misty, 8–20°C",
        "top_attractions": ["Kodaikanal Lake", "Coaker's Walk", "Bryant Park", "Pillar Rocks"],
        "local_food": ["South Indian meals", "Tea", "Pancakes", "Homemade chocolates"],
        "transport": "Local taxis, walking, rented bikes",
        "hotels": {"budget": "₹700–₹1,400/night", "mid": "₹2,000–₹4,000/night", "luxury": "₹5,000–₹12,000/night"},
        "daily_costs": {"budget": 2000, "balanced": 4300, "luxury": 12000, "adventure": 3000, "family": 5800},
        "airport": "Madurai Airport",
        "tips": ["Pack warm clothing for evenings", "Plan outdoor sightseeing early", "Enjoy the lake and cafes at a relaxed pace"],
    },
    "new york": {
        "region": "North America", "state": "USA",
        "best_months": "April – June",
        "weather": "Cool to warm, 10–28°C",
        "top_attractions": ["Central Park", "Statue of Liberty", "Metropolitan Museum", "Brooklyn Bridge"],
        "local_food": ["Pizza", "Bagels", "Hot dogs", "Delis"],
        "transport": "Subway, taxis, walking",
        "hotels": {"budget": "₹12,000–₹20,000/night", "mid": "₹20,000–₹40,000/night", "luxury": "₹45,000+/night"},
        "daily_costs": {"budget": 15000, "balanced": 27000, "luxury": 60000, "adventure": 18000, "family": 32000},
        "airport": "John F. Kennedy Airport",
        "tips": ["Use the subway to save time", "Book Broadway tickets early", "Carry comfortable walking shoes"],
    },
    "rome": {
        "region": "Europe", "state": "Italy",
        "best_months": "April – June",
        "weather": "Warm and sunny, 15–28°C",
        "top_attractions": ["Colosseum", "Trevi Fountain", "Vatican City", "Pantheon"],
        "local_food": ["Pizza", "Pasta", "Gelato", "Roman coffee"],
        "transport": "Metro, walking, buses",
        "hotels": {"budget": "₹10,000–₹18,000/night", "mid": "₹18,000–₹35,000/night", "luxury": "₹40,000+/night"},
        "daily_costs": {"budget": 13000, "balanced": 24000, "luxury": 55000, "adventure": 16000, "family": 30000},
        "airport": "Fiumicino Airport",
        "tips": ["Wear comfortable shoes for cobblestone streets", "Reserve Vatican ticket slots early", "Try a gelato walk in the evening"],
    },
    "sydney": {
        "region": "Oceania", "state": "Australia",
        "best_months": "September – November",
        "weather": "Mild, sunny and breezy",
        "top_attractions": ["Opera House", "Bondi Beach", "Harbour Bridge", "Blue Mountains"],
        "local_food": ["Seafood", "Coffee", "Pavlova", "Asian fusion"],
        "transport": "Trains, ferries, buses",
        "hotels": {"budget": "₹8,000–₹15,000/night", "mid": "₹15,000–₹30,000/night", "luxury": "₹35,000+/night"},
        "daily_costs": {"budget": 12000, "balanced": 22000, "luxury": 50000, "adventure": 16000, "family": 28000},
        "airport": "Sydney Airport",
        "tips": ["Plan for outdoor activities", "Use public transport for city travel", "Book ferry tickets in advance"],
    },
}

def get_destination_info(destination: str) -> dict:
    """Return knowledge-base entry for a destination, or a generic fallback."""
    dest_lower = destination.lower().strip()
    # Exact or partial match
    for key, val in DESTINATION_DATA.items():
        if key in dest_lower or dest_lower in key:
            val["key"] = key
            return val
    # Fallback generic
    return {
        "key": "generic",
        "region": "India",
        "best_months": "October – March",
        "weather": "Varies by season",
        "top_attractions": ["Local heritage sites", "Markets", "Nature spots", "Temples"],
        "local_food": ["Regional specialities", "Street food", "Local sweets"],
        "transport": "Local buses, taxis, auto-rickshaws",
        "hotels": {"budget": "₹700–₹1,500/night", "mid": "₹2,000–₹5,000/night", "luxury": "₹7,000–₹25,000/night"},
        "daily_costs": {"budget": 2000, "balanced": 5000, "luxury": 15000, "adventure": 3500, "family": 6500},
        "airport": "Nearest domestic airport",
        "tips": ["Book accommodation in advance", "Carry local currency", "Respect local customs"],
    }

# ─────────────────────────────────────────────────────────────────────────────
#  BUDGET ENGINE — realistic, destination-aware, per-style
# ─────────────────────────────────────────────────────────────────────────────
STYLE_MULTIPLIERS = {
    "budget":      {"accommodation": 0.35, "food": 0.20, "transport": 0.20, "sightseeing": 0.15, "misc": 0.10},
    "balanced":    {"accommodation": 0.38, "food": 0.22, "transport": 0.18, "sightseeing": 0.14, "misc": 0.08},
    "luxury":      {"accommodation": 0.45, "food": 0.22, "transport": 0.16, "sightseeing": 0.12, "misc": 0.05},
    "adventure":   {"accommodation": 0.28, "food": 0.18, "transport": 0.25, "sightseeing": 0.22, "misc": 0.07},
    "family":      {"accommodation": 0.40, "food": 0.25, "transport": 0.16, "sightseeing": 0.12, "misc": 0.07},
    "solo":        {"accommodation": 0.33, "food": 0.22, "transport": 0.20, "sightseeing": 0.17, "misc": 0.08},
    "honeymoon":   {"accommodation": 0.48, "food": 0.22, "transport": 0.14, "sightseeing": 0.10, "misc": 0.06},
    "cultural":    {"accommodation": 0.36, "food": 0.20, "transport": 0.18, "sightseeing": 0.20, "misc": 0.06},
    "business":    {"accommodation": 0.50, "food": 0.20, "transport": 0.18, "sightseeing": 0.07, "misc": 0.05},
}

def estimate_trip_budget(destination: str, days: int, travel_style: str, num_travellers: int = 1) -> dict:
    """Destination-aware, realistic budget estimation with full breakdown."""
    info       = get_destination_info(destination)
    style_key  = travel_style.lower() if travel_style.lower() in STYLE_MULTIPLIERS else "balanced"
    daily_base = info["daily_costs"].get(style_key, info["daily_costs"].get("balanced", 5000))
    splits     = STYLE_MULTIPLIERS.get(style_key, STYLE_MULTIPLIERS["balanced"])

    # Per-person per-day breakdown
    daily_breakdown = {k: round(daily_base * v) for k, v in splits.items()}

    # Group discount for large groups
    group_discount = 0.95 if num_travellers >= 4 else 1.0

    # Per-person total
    per_person_total = round(sum(daily_breakdown.values()) * days * group_discount)
    group_total      = per_person_total * num_travellers

    # Total breakdown (all travellers, all days)
    total_breakdown = {k: round(v * days * num_travellers * group_discount) for k, v in daily_breakdown.items()}

    season_info = get_best_season(destination)

    return {
        "destination":       destination,
        "travel_style":      style_key,
        "days":              days,
        "num_travellers":    num_travellers,
        "daily_per_person":  round(daily_base * group_discount),
        "daily_average":     round(daily_base * group_discount),
        "daily_average_cost": round(daily_base * group_discount),
        "cost_per_person":   per_person_total,
        "total_per_person":  per_person_total,
        "total_group":       group_total,
        "estimated_total":    group_total,
        "breakdown":         total_breakdown,
        "daily_breakdown":   daily_breakdown,
        "currency":          "INR",
        "best_season":       season_info["best_season"],
        "season_reason":     season_info["reason"],
        "destination_info":  {
            "region":            info.get("region", "India"),
            "top_attractions":   info.get("top_attractions", [])[:4],
            "hotel_range":       info["hotels"].get(
                "budget" if style_key in ("budget","solo") else
                "luxury" if style_key in ("luxury","honeymoon","business") else "mid",
                info["hotels"].get("mid", "₹2,000–₹5,000/night")
            ),
        },
    }

def get_best_season(destination: str) -> dict:
    """Destination-aware best-season with rich description."""
    info   = get_destination_info(destination)
    months = info.get("best_months", "October – March")
    reason_map = {
        "goa":       "Post-monsoon clarity; ideal beach weather with minimal rain and cool evenings.",
        "kerala":    "Backwaters and hill stations at their lush best; pleasant temperatures throughout.",
        "rajasthan": "Cool desert nights, warm days — perfect for fort visits and camel safaris.",
        "ladakh":    "Roads open, clear skies, and the surreal landscape at its vivid best.",
        "manali":    "Snow activities in winter; trekking and green valleys in spring–summer.",
        "andaman":   "Calm seas for snorkelling and scuba; pristine beach conditions.",
        "hyderabad": "Comfortable weather for outdoor exploration and heritage walks.",
        "delhi":     "Pleasant mornings for sightseeing; pollution eases mid-season.",
        "mumbai":    "Breezy winters ideal for street food walks and outdoor culture.",
        "varanasi":  "Crisp mornings perfect for sunrise boat rides and ghat exploration.",
    }
    key    = info.get("key", "generic")
    reason = reason_map.get(key, "Generally comfortable weather for sightseeing and outdoor activities.")
    return {"destination": destination, "best_season": months, "reason": reason}

# ─────────────────────────────────────────────────────────────────────────────
#  SMART DEMO RESPONSES — destination-specific, no API needed
# ─────────────────────────────────────────────────────────────────────────────
DESTINATION_ITINERARY_TEMPLATES = {
    "goa": {
        "focus": "Beachfront leisure, nightlife, and laid-back coastal exploration.",
        "morning": [
            "Start with a sunrise walk at Baga Beach before the crowds arrive.",
            "Visit the old churches of Old Goa and enjoy a quiet café stop.",
            "Head to Dudhsagar Waterfalls for a scenic nature day.",
        ],
        "afternoon": [
            "Relax at Palolem Beach or browse the shops at Anjuna Flea Market.",
            "Take a short spice plantation tour and enjoy local flavours.",
            "Spend the afternoon with beachside watersports or a sunset cruise.",
        ],
        "evening": [
            "Enjoy a seafood dinner in North Goa and a stroll at the beach shacks.",
            "Watch the sunset from a beach club and savour Goan music and nightlife.",
            "Finish with a relaxed riverside dinner and local dessert tasting.",
        ],
        "restaurants": ["Marlio's Cafe", "The Fisherman's Wharf", "Baba's", "The Black Sheep"],
        "travel_tips": ["Keep a light backpack for beach hopping.", "Book beach shacks early during peak season.", "Use local taxis for late-night returns."],
    },
    "kerala": {
        "focus": "Backwaters, tea gardens, and slow travel with rich local cuisine.",
        "morning": [
            "Take an early houseboat ride through the Alleppey backwaters.",
            "Visit Munnar tea estates for misty views and plantation walks.",
            "Begin the day with a nature walk around Thekkady or a wildlife safari.",
        ],
        "afternoon": [
            "Explore Fort Kochi and the Chinese fishing nets before lunch.",
            "Spend time at a spice garden or tea factory in the hills.",
            "Relax at Kovalam Beach and enjoy coconut water by the shore.",
        ],
        "evening": [
            "Enjoy a kathakali performance or a sunset cruise along the backwaters.",
            "Try a Kerala sadya dinner and a cup of filter coffee.",
            "Walk the promenade in Kochi or relax at a homestay terrace.",
        ],
        "restaurants": ["Karimeen Cafe", "The Rice Boat", "Fusion Bay", "Rasa Kerala"],
        "travel_tips": ["Carry light cotton wear and a rain jacket.", "Book houseboats in advance for weekends.", "Use taxis for hill stations and buses for shorter routes."],
    },
    "rajasthan": {
        "focus": "Heritage forts, desert landscapes, and royal hospitality.",
        "morning": [
            "Visit Amber Fort before the sun gets too strong.",
            "Explore the blue lanes of Jodhpur and the fort complex.",
            "Start early for a desert safari near Jaisalmer.",
        ],
        "afternoon": [
            "Spend the afternoon at City Palace or a palace museum.",
            "Enjoy local bazaars and street food around the old city.",
            "Visit a camel camp or desert viewpoint in the late afternoon.",
        ],
        "evening": [
            "Watch the sound-and-light show at a fort or palace.",
            "Savour Rajasthani thali and traditional folk music.",
            "Enjoy a rooftop dinner with desert views.",
        ],
        "restaurants": ["Choki Dhani", "Panchhi Petha", "The Rajput Room", "Moustache Restaurant"],
        "travel_tips": ["Carry layers for chilly desert evenings.", "Book heritage stays early in peak season.", "Use hired cabs for city-to-city comfort."],
    },
    "ladakh": {
        "focus": "High-altitude landscapes, monastery visits, and adventure travel.",
        "morning": [
            "Drive to Pangong Tso for serene lakeside views.",
            "Visit a monastery before the day heats up.",
            "Start early for Nubra Valley or Khardung La viewpoints.",
        ],
        "afternoon": [
            "Walk through local markets and enjoy Tibetan food.",
            "Visit Magnetic Hill or a scenic viewpoint with a short trek.",
            "Take a rest break and acclimatise before the evening outing.",
        ],
        "evening": [
            "Watch the sky change colours over the mountains.",
            "Enjoy hot soup and momos in a local café.",
            "Relax at a homestay with mountain views and local stories.",
        ],
        "restaurants": ["The Tibetan Kitchen", "Roadside Café Leh", "Wazwan Restaurant", "Bon Appetit"],
        "travel_tips": ["Keep a slow pace to manage the altitude.", "Carry warm layers even in summer.", "Allow extra buffer time for road travel."],
    },
    "manali": {
        "focus": "Snowy mountain views, cafes, and a balanced mix of adventure and relaxation.",
        "morning": [
            "Head to Solang Valley for adventure activities or scenic views.",
            "Visit Hadimba Temple and the old town before the crowds.",
            "Start early for a short trek or viewpoint visit.",
        ],
        "afternoon": [
            "Enjoy café hopping in Old Manali and local shopping.",
            "Visit nearby villages or riverside spots for a peaceful break.",
            "Spend the afternoon in a spa or homestay lounge.",
        ],
        "evening": [
            "Enjoy a hearty Himachali dinner by the fireplace.",
            "Take a walk around the market and sample local snacks.",
            "Finish the day with warm tea and mountain views.",
        ],
        "restaurants": ["The Corner House", "Munchies", "Brew Estate", "Drifter's Café"],
        "travel_tips": ["Pack warm clothing for evenings and high-altitude moments.", "Book taxis in advance for travel between viewpoints.", "Avoid overloading the schedule with back-to-back treks."],
    },
    "andaman": {
        "focus": "Island hopping, coral reefs, and relaxed beach days.",
        "morning": [
            "Take an early ferry to Havelock or Neil Island.",
            "Start with a beach walk at Radhanagar before the day gets busy.",
            "Head to a marine park or snorkelling spot in the morning.",
        ],
        "afternoon": [
            "Relax at the beach or visit a local viewpoint.",
            "Explore Cellular Jail or the heritage area on Port Blair.",
            "Enjoy a long lunch with fresh seafood by the shore.",
        ],
        "evening": [
            "Watch the sunset over the sea and enjoy a calm evening walk.",
            "Try grilled seafood or coconut-based local dishes.",
            "Spend the evening at the dockside or a beach cafe.",
        ],
        "restaurants": ["Ananda Restaurant", "The Crab House", "Cafe Del Mar", "Tamarind Bay"],
        "travel_tips": ["Book ferries early because island routes fill quickly.", "Carry cash for smaller eateries and island transfers.", "Keep sunscreen and a dry bag ready for boat rides."],
    },
    "hyderabad": {
        "focus": "City heritage, food trails, and film-city energy.",
        "morning": [
            "Visit Charminar and the surrounding heritage lanes early.",
            "Head to Golconda Fort for a history-rich morning.",
            "Start with a relaxed breakfast before a museum or park visit.",
        ],
        "afternoon": [
            "Explore the Salar Jung Museum or a local market.",
            "Spend time at Ramoji Film City if you want an immersive day.",
            "Try haleem or biryani during the lunch break.",
        ],
        "evening": [
            "Enjoy a walk around Hussain Sagar or a local cafe.",
            "Savour Hyderabadi biryani or Irani chai at an iconic spot.",
            "Finish with a heritage walk or rooftop dinner.",
        ],
        "restaurants": ["Paradise Biryani", "Bawarchi", "Cafe Bahar", "The Minerva"],
        "travel_tips": ["Use the metro or app-based cabs to avoid traffic.", "Plan food stops early because streets get busy at dinner time.", "Keep light clothing for daytime and a light layer for evenings."],
    },
    "delhi": {
        "focus": "Historic landmarks, street food, and a fast-paced city experience.",
        "morning": [
            "Start at Red Fort or Humayun's Tomb while the air is cool.",
            "Explore Chandni Chowk with a local guide and a breakfast stop.",
            "Visit a museum or garden before noon.",
        ],
        "afternoon": [
            "Spend the afternoon inside Qutub Minar or a heritage site.",
            "Enjoy a local food trail with chaat and kebabs.",
            "Take a relaxed break at a garden or café.",
        ],
        "evening": [
            "Watch the evening lights around India Gate and nearby areas.",
            "Try a dinner of butter chicken or local street favourites.",
            "Wrap up with a calm walk through Lodhi Garden.",
        ],
        "restaurants": ["Paranthe Wali Gali", "Karahi Boys", "Moti Mahal Delux", "Indian Accent"],
        "travel_tips": ["Use the metro for most city travel.", "Carry water and a mask during peak pollution months.", "Plan sightseeing early to avoid traffic and heat."],
    },
    "mumbai": {
        "focus": "Coastal city energy, heritage, and street food.",
        "morning": [
            "Start with Marine Drive and the Gateway of India.",
            "Visit the Elephanta Caves if your schedule allows.",
            "Enjoy a breakfast of vada pav or pav bhaji.",
        ],
        "afternoon": [
            "Spend time at Juhu Beach or a heritage museum.",
            "Take a local train or ferry ride to experience the city better.",
            "Stop for a snack break around a busy food lane.",
        ],
        "evening": [
            "Enjoy sunset by the sea and a relaxed dinner in Bandra.",
            "Try local street food and a rooftop cafe for the evening.",
            "Wrap up with a late-night dessert or coffee stop.",
        ],
        "restaurants": ["Britannia & Co.", "Bademiya", "Trishna", "Theobroma"],
        "travel_tips": ["Plan local trains carefully during rush hour.", "Allow extra travel time for traffic and monsoon delays.", "Carry a small umbrella during the rainy season."],
    },
    "varanasi": {
        "focus": "Spiritual rituals, ghat walks, and riverfront evenings.",
        "morning": [
            "Take a sunrise boat ride on the Ganga for the best views.",
            "Visit the Kashi Vishwanath Temple or the old lanes nearby.",
            "Start with a quiet walk through the ghats before breakfast.",
        ],
        "afternoon": [
            "Spend time at Sarnath or another heritage landmark.",
            "Explore local lanes and craft shops around the old city.",
            "Take a break at a riverside café for a calm afternoon.",
        ],
        "evening": [
            "Witness the Ganga aarti from Dashashwamedh Ghat.",
            "Enjoy a local dinner with Banarasi sweets or paan.",
            "Take a quiet evening walk along the illuminated ghats.",
        ],
        "restaurants": ["Blue Lassi", "Kashi Chat Bhandar", "The Ganges View", "Madan Paan Bhandar"],
        "travel_tips": ["Wear comfortable shoes for long walks on the ghats.", "Carry cash for smaller vendors and temple visits.", "Plan evening activities around the riverfront timing."],
    },
}


def _normalise_style(style: str | None) -> str:
    style_key = (style or "balanced").strip().lower()
    aliases = {
        "cheap": "budget",
        "affordable": "budget",
        "mid-range": "balanced",
        "balanced": "balanced",
        "standard": "balanced",
        "premium": "luxury",
        "deluxe": "luxury",
        "romantic": "honeymoon",
        "family-friendly": "family",
        "family": "family",
        "trek": "adventure",
        "adventure": "adventure",
        "solo": "solo",
        "culture": "cultural",
        "cultural": "cultural",
        "luxury": "luxury",
    }
    return aliases.get(style_key, style_key or "balanced")


def _extract_trip_details(message: str, profile: dict | None = None) -> dict:
    message_text = (message or "").lower()
    profile_data = profile or {}
    info = get_destination_info(message_text)
    destination = info.get("key") or profile_data.get("destination") or ""
    if not destination:
        for key in DESTINATION_DATA:
            if key in message_text:
                destination = key
                break

    days = 3
    if "weekend" in message_text:
        days = 2
    else:
        match = re.search(r"(\d+)\s*(?:day|days)", message_text)
        if match:
            days = max(1, int(match.group(1)))
        elif profile_data.get("days"):
            try:
                days = int(profile_data.get("days"))
            except (TypeError, ValueError):
                days = 3

    travellers = 1
    if "couple" in message_text:
        travellers = 2
    else:
        match = re.search(r"(\d+)\s*(?:travellers|people|persons|members|friends)", message_text)
        if match:
            travellers = max(1, int(match.group(1)))
        elif profile_data.get("num_travellers"):
            try:
                travellers = int(profile_data.get("num_travellers"))
            except (TypeError, ValueError):
                travellers = 1

    travel_style = _normalise_style(profile_data.get("travel_style") or None)
    if any(term in message_text for term in ["luxury", "premium", "deluxe"]):
        travel_style = "luxury"
    elif any(term in message_text for term in ["budget", "cheap", "affordable"]):
        travel_style = "budget"
    elif any(term in message_text for term in ["adventure", "trek", "hiking"]):
        travel_style = "adventure"
    elif any(term in message_text for term in ["family", "kids", "children"]):
        travel_style = "family"
    elif any(term in message_text for term in ["honeymoon", "romantic"]):
        travel_style = "honeymoon"
    elif any(term in message_text for term in ["cultural", "history", "heritage"]):
        travel_style = "cultural"

    preferences = profile_data.get("goals") or profile_data.get("preferences") or ""
    if not preferences:
        keywords = ["beach", "food", "history", "adventure", "nature", "shopping", "nightlife", "wildlife", "relaxation"]
        preferences = ", ".join([kw for kw in keywords if kw in message_text])
    if not preferences:
        preferences = "balanced sightseeing"

    budget = profile_data.get("budget") or ""
    if not budget:
        budget_match = re.search(r"₹\s*([0-9,]+)", message_text)
        if budget_match:
            budget = f"₹{budget_match.group(1)}/day"

    return {
        "destination": destination or "India",
        "days": days,
        "travellers": travellers,
        "travel_style": travel_style,
        "budget": budget,
        "preferences": preferences,
    }


def _looks_like_greeting(message_text: str) -> bool:
    greetings = [
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
        "how are you", "thanks", "thank you", "appreciate it"
    ]
    return any(greet in message_text for greet in greetings)


def _looks_like_missing_details(message_text: str, trip: dict) -> bool:
    if trip.get("destination") in ("India", ""):
        return False
    if any(term in message_text for term in ["best time", "weather", "restaurant", "restaurants", "hotel", "hotels", "transport", "things to do", "attractions", "packing", "food", "stay"]):
        return False
    if "weekend" in message_text or re.search(r"(\d+)\s*(day|days)", message_text):
        return False
    has_people_hint = any(term in message_text for term in ["traveller", "travellers", "people", "persons", "friends", "couple", "family", "group"])
    has_budget_hint = any(term in message_text for term in ["budget", "cheap", "affordable", "luxury", "premium", "deluxe"])
    return not has_people_hint and not has_budget_hint


def build_smart_chat_response(message: str, profile: dict | None = None, conversation_history: list | None = None) -> str:
    """Generate a rich, destination-specific response without calling the AI API."""
    message_text = (message or "").strip().lower()
    trip = _extract_trip_details(message, profile)
    destination = trip["destination"]
    info = get_destination_info(destination)
    style = trip["travel_style"]
    days = trip["days"]
    travellers = trip["travellers"]
    budget = trip["budget"] or "Flexible"
    preferences = trip["preferences"]

    if _looks_like_greeting(message_text):
        dest_name = info.get("key", destination).title() if info.get("key") != "generic" else "your next trip"
        if dest_name != "your next trip":
            return (
                f"Hello! I’d be delighted to help you plan a {dest_name} getaway. "
                f"I can tailor a realistic itinerary around your budget, travel style, group size, and interests."
            )
        return (
            "Hello! I’m TravelBot, your friendly travel planning assistant. "
            "Tell me your destination and I’ll help shape a practical itinerary, budget, and packing plan."
        )

    if _looks_like_missing_details(message_text, trip):
        dest_name = info.get("key", destination).title() if info.get("key") != "generic" else destination.title()
        return (
            f"Absolutely — I can help shape a {dest_name} trip that feels realistic and well planned. "
            f"To make it truly useful, could you share your preferred trip length in days, your budget range, and how many travellers are joining? "
            f"I can also tailor it for a couple, family, honeymoon, or adventure-style holiday."
        )

    if destination and info.get("key") != "generic":
        dest_name = info.get("key", destination).title()
        hotel_range = info["hotels"].get(
            "budget" if style in ("budget", "solo") else
            "luxury" if style in ("luxury", "honeymoon", "business") else "mid"
        )
        daily_cost = info["daily_costs"].get(style, info["daily_costs"]["balanced"])
        estimated_total = daily_cost * days * travellers
        highlights = ", ".join(info["top_attractions"][:4])
        food_items = ", ".join(info["local_food"][:4])
        traveller_label = "traveller" if travellers == 1 else "travellers"
        return (
            f"**{dest_name} Travel Guide ✈️**\n\n"
            f"I’ve tailored this {days}-day plan for {travellers} {traveller_label} with a **{style.title()}** style and a focus on **{preferences}**.\n\n"
            f"**Best Time to Visit:** {info['best_months']}\n"
            f"**Weather:** {info['weather']}\n"
            f"**Budget Focus:** {budget}\n"
            f"**Estimated Daily Budget:** ₹{daily_cost:,} per person\n"
            f"**Estimated Trip Cost:** ₹{estimated_total:,} total\n\n"
            f"**Top Highlights:** {highlights}\n"
            f"**Food to Try:** {food_items}\n"
            f"**Recommended Stay:** {hotel_range}\n"
            f"**Getting Around:** {info['transport']}\n\n"
            f"Use the Itinerary section to generate a full day-by-day plan for {dest_name} that reflects your travel preferences."
        )

    return (
        "**TravelBot — Your AI Travel Planner ✈️**\n\n"
        "I can help you shape a realistic trip for India and international destinations.\n\n"
        "Try a request like: 'Plan a 5-day Goa trip for 2 travellers on a budget' or 'Create a luxury 3-day Kerala itinerary'.\n\n"
        "I’ll tailor the plan around your destination, trip length, travellers, budget, and travel style."
    )


def build_smart_itinerary(destination: str, days: int, travel_style: str, profile: dict | None) -> str:
    """Generate a destination-specific itinerary without calling the API."""
    info = get_destination_info(destination)
    dest_key = info.get("key", "generic")
    dest_name = destination.strip().title() if destination.strip() else info.get("key", "Destination").title()
    style = _normalise_style(travel_style)
    profile_data = profile or {}
    preferences = profile_data.get("goals") or profile_data.get("preferences") or ""
    if not preferences:
        preferences = "balanced sightseeing"

    template = DESTINATION_ITINERARY_TEMPLATES.get(dest_key, {
        "focus": "Local sightseeing with practical travel pacing.",
        "morning": ["Start the day with a local landmark visit.", "Explore a heritage site before lunch."],
        "afternoon": ["Spend the afternoon at a cultural or scenic stop.", "Enjoy local food and a relaxed market visit."],
        "evening": ["Finish the day with a calm evening walk.", "Try a local dinner and enjoy the city atmosphere."],
        "restaurants": ["Local favourites"],
        "travel_tips": ["Keep an open buffer for traffic and weather."],
    })

    hotel_range = info["hotels"].get(
        "budget" if style in ("budget", "solo") else
        "luxury" if style in ("luxury", "honeymoon", "business") else "mid"
    )
    daily_cost = info["daily_costs"].get(style, info["daily_costs"].get("balanced", 5000))
    daily_cost = daily_cost + (200 if style == "luxury" else 0)

    lines = [f"**{days}-Day {dest_name} Itinerary — {style.title()} Style 🗺️**\n"]
    lines.append(f"**Trip Focus:** {template['focus']}\n")
    lines.append(f"**Best Season:** {info['best_months']}  |  **Weather:** {info['weather']}\n")
    lines.append(f"**Recommended Stay:** {hotel_range}  |  **Estimated Daily Budget:** ₹{daily_cost:,}/person\n")
    lines.append(f"**Preferences:** {preferences}\n")
    lines.append(f"**Getting Around:** {info['transport']}\n")

    for day in range(1, days + 1):
        morning = template["morning"][(day - 1) % len(template["morning"])]
        afternoon = template["afternoon"][(day - 1) % len(template["afternoon"])]
        evening = template["evening"][(day - 1) % len(template["evening"])]
        restaurant = template["restaurants"][(day - 1) % len(template["restaurants"])]
        travel_tip = template["travel_tips"][(day - 1) % len(template["travel_tips"])]
        lines.append(f"\n**Day {day}**")
        lines.append(f"- 🌅 **Morning:** {morning}")
        lines.append(f"- 🍽️ **Lunch:** Try a local favourite near the day's main stop")
        lines.append(f"- ☀️ **Afternoon:** {afternoon}")
        lines.append(f"- 🍛 **Dinner:** {restaurant} for a destination-specific meal")
        lines.append(f"- 🌙 **Evening:** {evening}")
        lines.append(f"- 🧭 **Local travel tip:** {travel_tip}")
        lines.append(f"- 💰 **Estimated Day Cost:** ₹{daily_cost + (day * 150):,} per person")

    lines.append(f"\n**Packing Tips for {dest_name}:**")
    lines.append("• Comfortable walking shoes  • Power bank & travel adapter")
    lines.append("• Sun protection and a refillable water bottle  • Light clothing + a layer for evenings")
    lines.append(f"\n**Emergency Contacts:** Police: 100 | Ambulance: 108 | Tourist Helpline: 1800-111-363")
    lines.append(f"\n🌟 Have an incredible trip to {dest_name}! Safe travels! ✈️")

    return "\n".join(lines)

def build_smart_group_response(members: list) -> str:
    """Generate a smart group trip recommendation without the API."""
    count = len(members)
    styles = [m.get("travel_style", "balanced") for m in members]
    interests = [m.get("goals", "") for m in members]
    member_list = "\n".join(f"• {m.get('name','Member')} (Age {m.get('age','?')}) — {m.get('travel_style','balanced').title()}" for m in members)

    return (
        f"**Group Travel Plan for {count} Travellers 👥**\n\n"
        f"**Your Group:**\n{member_list}\n\n"
        f"**Recommended Destinations for Your Group:**\n"
        f"• 🏖️ **Goa** — Great for mixed groups: beaches, food, nightlife & water sports\n"
        f"• 🏰 **Rajasthan Circuit** — Heritage, culture, forts & desert safari\n"
        f"• 🌴 **Kerala** — Backwaters, Ayurveda & scenic hill stations\n"
        f"• 🏔️ **Himachal Pradesh** — Adventure, trekking & scenic valleys\n\n"
        f"**Group Logistics Tips:**\n"
        f"• Book a **private cab or tempo traveller** for {count}+ people (cost-effective)\n"
        f"• Use **group booking discounts** on Indian Railways (10%+ off for groups of 10+)\n"
        f"• **Pre-book shared accommodation** like villas or boutique homestays\n"
        f"• Create a **WhatsApp group** for real-time coordination\n"
        f"• **Split responsibilities** — one person handles hotel, one transport, one food\n"
        f"• Allocate ₹5,000–₹10,000 emergency fund for the group\n\n"
        f"💡 Use the **Itinerary Generator** above to create a detailed day-by-day plan "
        f"tailored to your group's preferred destination and travel style!"
    )

# ─────────────────────────────────────────────────────────────────────────────
#  FLASK APP
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "travelbot-dev-secret-2025")
CORS(app)

# ── Watsonx client (lazy-init) ───────────────────────────────────────────────
_watsonx_model: ModelInference | None = None

def get_watsonx_model() -> ModelInference | None:
    global _watsonx_model
    if _watsonx_model is not None:
        return _watsonx_model

    api_key    = os.getenv("IBM_API_KEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    url        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").rstrip("/")
    model_id   = os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct")

    if not api_key or not project_id:
        app.logger.warning("IBM_API_KEY or WATSONX_PROJECT_ID not set — running in smart demo mode.")
        return None

    try:
        credentials = Credentials(url=url, api_key=api_key)
        params = {
            GenParams.MAX_NEW_TOKENS: int(os.getenv("MAX_NEW_TOKENS", 1500)),
            GenParams.TEMPERATURE:    float(os.getenv("TEMPERATURE", 0.75)),
            GenParams.TOP_P:          float(os.getenv("TOP_P", 0.92)),
            GenParams.STOP_SEQUENCES: ["Human:", "User:", "Traveller:"],
        }
        _watsonx_model = ModelInference(
            model_id=model_id, params=params,
            credentials=credentials, project_id=project_id,
        )
        app.logger.info(f"Watsonx model '{model_id}' initialised.")
    except Exception as exc:
        app.logger.error(f"Watsonx init failed: {exc}")
        _watsonx_model = None

    return _watsonx_model

# ── Prompt builder ───────────────────────────────────────────────────────────
def build_system_prompt(user_profile: dict | None = None) -> str:
    ai         = AGENT_INSTRUCTIONS
    safety     = "\n".join(f"- {r}" for r in ai["safety_rules"])
    caps       = "\n".join(f"- {c}" for c in ai["capabilities"])
    dest_ctx   = f"\n\n**Indian Destination Expertise:**\n{ai['indian_destination_context']}"

    profile_block = ""
    if user_profile:
        profile_block = (
            f"\n\n**Current Traveller Profile:**\n"
            f"- Name: {user_profile.get('name','Traveller')}\n"
            f"- Age: {user_profile.get('age','N/A')}, Gender: {user_profile.get('gender','N/A')}\n"
            f"- Nationality: {user_profile.get('nationality','Indian')}\n"
            f"- Travel Style: {user_profile.get('travel_style', ai['default_travel_style'])}\n"
            f"- Goals: {user_profile.get('goals','explore and enjoy')}\n"
            f"- Budget Range: {user_profile.get('budget','flexible')}\n"
            f"- Special Requirements: {user_profile.get('requirements','none')}\n"
        )

    return (
        f"You are {ai['name']}. {ai['persona']}\n\n"
        f"**Communication Style:** {ai['language_style']}\n\n"
        f"**Response Format:** {ai['response_format']}\n\n"
        f"**Your Capabilities:**\n{caps}\n\n"
        f"**Safety Guidelines:**\n{safety}"
        f"{dest_ctx}"
        f"{profile_block}\n\n"
        f"Respond as {ai['name']}. Be specific, detailed, and destination-aware. "
        f"Do not include 'AI:', 'Assistant:', or role prefixes in your response."
    )

def build_prompt(message: str, history: list, profile: dict | None) -> str:
    system    = build_system_prompt(profile)
    user_name = (profile or {}).get("name", "Traveller") or "Traveller"
    history_text = "".join(
        f"{user_name if m['role']=='user' else AGENT_INSTRUCTIONS['name']}: {m['content']}\n"
        for m in history[-8:]
    )
    return f"{system}\n\nConversation:\n{history_text}{user_name}: {message}\n{AGENT_INSTRUCTIONS['name']}:"

# ─────────────────────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", agent_name=AGENT_INSTRUCTIONS["name"])

# ── Chat ─────────────────────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    data    = request.get_json(force=True)
    message = data.get("message", "").strip()
    history = data.get("history", [])
    profile = data.get("profile")

    if not message:
        return jsonify({"error": "Empty message"}), 400

    model = get_watsonx_model()

    if model is None:
        # Smart demo — destination-aware response
        response = build_smart_chat_response(message, profile)
        return jsonify({
            "response":       response,
            "mode":           "smart_demo",
            "model":          "TravelBot Smart Demo",
            "inference_ms":   random.randint(180, 420),
            "input_tokens":   len(message.split()),
            "output_tokens":  len(response.split()),
            "timestamp":      datetime.now().isoformat(),
        })

    try:
        t0     = time.time()
        prompt = build_prompt(message, history, profile)
        result = model.generate_text(prompt=prompt)
        ms     = round((time.time() - t0) * 1000)

        response = (result.strip() if isinstance(result, str) else str(result))
        # Strip trailing role labels
        user_name = (profile or {}).get("name", "Traveller") or "Traveller"
        stop_pats = [re.escape(x) for x in ["User", "Human", "Traveller",
                     AGENT_INSTRUCTIONS["name"], user_name] if x]
        response  = re.sub(r'\s*(?:' + '|'.join(stop_pats) + r')\s*:\s*$',
                           '', response, flags=re.IGNORECASE).strip()

        return jsonify({
            "response":       response,
            "mode":           "watsonx",
            "model":          os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct"),
            "inference_ms":   ms,
            "input_tokens":   len(prompt.split()),
            "output_tokens":  len(response.split()),
            "timestamp":      datetime.now().isoformat(),
        })
    except Exception as exc:
        app.logger.error(f"Chat error: {exc}")
        return jsonify({"error": str(exc)}), 500

# ── Budget ───────────────────────────────────────────────────────────────────
@app.route("/api/budget", methods=["POST"])
def budget():
    data = request.get_json(force=True)
    try:
        destination    = data.get("destination", "India").strip() or "India"
        days           = max(1, int(data.get("days", 5)))
        travel_style   = data.get("travel_style", "balanced")
        num_travellers = max(1, int(data.get("num_travellers", 1)))
    except (KeyError, ValueError):
        return jsonify({"error": "Provide valid destination, days, travel_style, and num_travellers"}), 400

    result = estimate_trip_budget(destination, days, travel_style, num_travellers)
    return jsonify(result)

# ── Itinerary ────────────────────────────────────────────────────────────────
@app.route("/api/itinerary", methods=["POST"])
def itinerary():
    data         = request.get_json(force=True)
    destination  = data.get("destination", "").strip()
    days         = min(max(1, int(data.get("days", 3))), 14)
    travel_style = data.get("travel_style", "balanced")
    profile      = data.get("profile", {})
    season       = data.get("season", "")
    interests    = data.get("interests", "")

    if not destination:
        return jsonify({"error": "Please provide a destination"}), 400

    ai   = AGENT_INSTRUCTIONS
    info = get_destination_info(destination)

    profile_line = ""
    if profile and profile.get("name"):
        profile_line = (
            f"Traveller: {profile.get('name')}, age {profile.get('age','?')}, "
            f"travel style: {profile.get('travel_style', travel_style)}, "
            f"goal: {profile.get('goals','explore and enjoy')}. "
        )

    prompt_text = (
        f"You are {ai['name']}, an expert AI travel planner. {profile_line}"
        f"Create a detailed, engaging {days}-day travel itinerary for **{destination}** "
        f"with a **{travel_style}** travel style."
        + (f" Season: {season}." if season else "")
        + (f" Interests: {interests}." if interests else "")
        + f"\n\nDestination Facts: {destination} is known for: {', '.join(info.get('top_attractions', [])[:5])}. "
        f"Local food: {', '.join(info.get('local_food', [])[:3])}. "
        f"Best season: {info.get('best_months','October–March')}. "
        f"Transport: {info.get('transport','local transport')}.\n\n"
        f"For EACH day include:\n"
        f"• Morning activity (specific place name, opening time if applicable)\n"
        f"• Lunch recommendation (restaurant name or area + dish)\n"
        f"• Afternoon activity (specific attraction with brief description)\n"
        f"• Dinner recommendation (local specialty)\n"
        f"• Evening activity or tip\n"
        f"• Estimated cost for the day in INR\n\n"
        f"Also include at the end:\n"
        f"• Recommended Hotels (2 options per budget tier)\n"
        f"• Packing Tips for {destination}\n"
        f"• Local Transport Tips\n"
        f"• Emergency Contacts\n\n"
        f"Make it specific to {destination} — do NOT give generic advice. "
        f"Format with clear Day headings and bullet points.\n\n"
        f"{ai['name']}:"
    )

    model = get_watsonx_model()
    if model is None:
        plan = build_smart_itinerary(destination, days, travel_style, profile)
        return jsonify({"itinerary": plan, "mode": "smart_demo",
                        "model": "TravelBot Smart Demo", "destination_info": info})

    try:
        t0   = time.time()
        plan = model.generate_text(prompt=prompt_text)
        ms   = round((time.time() - t0) * 1000)
        plan = plan.strip() if isinstance(plan, str) else ""
        if not plan:
            return jsonify({"error": "Empty response from model. Please try again."}), 500
        return jsonify({"itinerary": plan, "mode": "watsonx",
                        "model": os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct"),
                        "inference_ms": ms, "destination_info": info})
    except Exception as exc:
        app.logger.error(f"Itinerary error: {exc}")
        return jsonify({"error": str(exc)}), 500

# ── Group Trip ───────────────────────────────────────────────────────────────
@app.route("/api/group-trip", methods=["POST"])
def group_trip():
    data    = request.get_json(force=True)
    members = data.get("members", [])

    if not members:
        return jsonify({"error": "Provide at least one group member"}), 400

    ai           = AGENT_INSTRUCTIONS
    members_text = "\n".join(
        f"- {m.get('name','Member')}: Age {m.get('age','?')}, "
        f"Gender {m.get('gender','?')}, Style: {m.get('travel_style', ai['default_travel_style'])}, "
        f"Interests: {m.get('goals','general sightseeing')}"
        for m in members
    )

    prompt_text = (
        f"{build_system_prompt()}\n\n"
        f"Plan a group trip for these {len(members)} travellers:\n{members_text}\n\n"
        f"Provide:\n"
        f"1. Top 3 recommended destinations for this group with reasons\n"
        f"2. Individual activity suggestions matching each person's interests\n"
        f"3. A 3-day shared itinerary everyone will enjoy\n"
        f"4. Estimated group budget\n"
        f"5. Practical group travel logistics tips\n\n"
        f"{ai['name']}:"
    )

    model = get_watsonx_model()
    if model is None:
        return jsonify({
            "recommendations": build_smart_group_response(members),
            "mode": "smart_demo",
            "model": "TravelBot Smart Demo",
        })

    try:
        result = model.generate_text(prompt=prompt_text)
        return jsonify({"recommendations": result.strip(), "mode": "watsonx",
                        "model": os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct")})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

# ── Health ───────────────────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    model  = get_watsonx_model()
    status = "connected" if model else "smart_demo"
    return jsonify({
        "status":    "ok",
        "watsonx":   status,
        "mode":      "watsonx" if model else "demo",
        "agent":     AGENT_INSTRUCTIONS["name"],
        "model":     os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct"),
        "version":   "2.0",
        "timestamp": datetime.now().isoformat(),
    })

# ── Agent Info ───────────────────────────────────────────────────────────────
@app.route("/api/agent-info")
def agent_info():
    ai = AGENT_INSTRUCTIONS
    return jsonify({
        "name":                ai["name"],
        "capabilities":        ai["capabilities"],
        "travel_style":        ai["default_travel_style"],
        "indian_destinations": ai["emphasise_indian_destinations"],
        "tone":                ai["tone"],
        "version":             "2.0",
        "destinations_db":     list(DESTINATION_DATA.keys()),
    })

# ── Destinations list ────────────────────────────────────────────────────────
@app.route("/api/destinations")
def destinations():
    result = {}
    for key, info in DESTINATION_DATA.items():
        result[key] = {
            "name":            key.title(),
            "region":          info.get("region"),
            "best_months":     info.get("best_months"),
            "top_attractions": info.get("top_attractions", [])[:3],
            "weather":         info.get("weather"),
        }
    return jsonify(result)

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
