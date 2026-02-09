from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import json
import re
import nltk
import numpy as np
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity
from fastapi.middleware.cors import CORSMiddleware

nltk.download("wordnet")

# -----------------------------
# App Setup
# -----------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Load Dataset
# -----------------------------
df = pd.read_csv("vital_data.csv")
df.columns = df.columns.str.strip().str.lower()

# -----------------------------
# Synonyms
# -----------------------------
with open("synonym_dict.json") as f:
    synonym_dict = json.load(f)

lemmatizer = WordNetLemmatizer()
stopwords = set(ENGLISH_STOP_WORDS)

# -----------------------------
# Food Knowledge Graph
# -----------------------------
ANIMAL = ["meat", "fish", "chicken", "beef", "pork", "lamb", "seafood"]
DAIRY = ["milk", "cheese", "butter", "ghee", "curd", "yogurt"]
EGGS = ["egg", "eggs"]

PLANT_FOODS = [
    "lentils", "beans", "tofu", "spinach",
    "seeds", "nuts", "vegetables", "whole grains"
]

ALLERGY_MAP = {
    "dairy": DAIRY,
    "eggs": EGGS,
    "nuts": ["almond", "cashew", "peanut", "walnut"],
    "soy": ["soy", "soya"],
    "gluten": ["wheat", "barley", "rye"],
    "shellfish": ["shrimp", "prawn", "crab"]
}

# -----------------------------
# Text Preparation
# -----------------------------
def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s]", "", text)
    return text

def expand(text):
    words = text.split()
    expanded = []
    for w in words:
        expanded += synonym_dict.get(w, [w])
    return " ".join(expanded)

# -----------------------------
# Vector Space
# -----------------------------
df["semantic_text"] = (
    df["symptom_keywords"].fillna("") + " " +
    df["cause_tags"].fillna("") + " " +
    df["description"].fillna("")
)

vectorizer = TfidfVectorizer(stop_words="english")
nutrient_vectors = vectorizer.fit_transform(df["semantic_text"])

intent_vectorizer = TfidfVectorizer(stop_words="english")
intent_vectors = intent_vectorizer.fit_transform(
    (df["symptom_keywords"].fillna("") + " " + df["cause_tags"].fillna(""))
)

# -----------------------------
# Schemas
# -----------------------------
class UserDetails(BaseModel):
    gender: str
    dietPreference: str
    lifestyle: str
    allergies: list[str]

class Feedback(BaseModel):
    nutrientName: str
    scoreAdjustment: float

class IssueRequest(BaseModel):
    text: str
    userDetails: UserDetails
    feedbacks: list[Feedback] = []

# -----------------------------
# Scoring Components
# -----------------------------
def diet_score(row, diet):
    foods = str(row["food_sources"]).lower()
    score = 1.0

    if diet == "vegan":
        if any(x in foods for x in ANIMAL + DAIRY + EGGS):
            score *= 0.03
    elif diet == "veg":
        if any(x in foods for x in ANIMAL + EGGS):
            score *= 0.05
    elif diet == "eggetarian":
        if any(x in foods for x in ANIMAL):
            score *= 0.1

    if any(p in foods for p in PLANT_FOODS):
        score *= 1.2

    return score

def allergy_score(row, allergies):
    foods = str(row["food_sources"]).lower()
    score = 1.0
    for a in allergies:
        if a in ALLERGY_MAP:
            if any(w in foods for w in ALLERGY_MAP[a]):
                score *= 0.01
    return score

def feedback_score(row, feedback_map):
    name = row["name"].lower()
    return feedback_map.get(name, 0) * 0.1

# -----------------------------
# API
# -----------------------------
@app.post("/predict")
def predict(data: IssueRequest):

    user_diet = data.userDetails.dietPreference.lower()
    user_allergies = [a.lower() for a in data.userDetails.allergies]

    # NLP
    query = expand(normalize(data.text))
    query_vec = vectorizer.transform([query])
    intent_vec = intent_vectorizer.transform([query])

    semantic_sim = cosine_similarity(query_vec, nutrient_vectors)[0]
    intent_sim = cosine_similarity(intent_vec, intent_vectors)[0]

    df_work = df.copy()
    df_work["semantic"] = semantic_sim
    df_work["intent"] = intent_sim

    feedback_map = {
        f.nutrientName.lower(): f.scoreAdjustment
        for f in data.feedbacks
    }

    # Final Hybrid Score
    df_work["final_score"] = df_work.apply(
        lambda row: (
            0.55 * row["semantic"] +
            0.20 * row["intent"] +
            0.15 * diet_score(row, user_diet) * allergy_score(row, user_allergies) +
            0.10 * feedback_score(row, feedback_map)
        ),
        axis=1
    )

    # Normalize
    max_score = df_work["final_score"].max()
    if max_score > 0:
        df_work["final_score"] = (df_work["final_score"] / max_score) * 100

    df_work["final_score"] = df_work["final_score"].clip(upper=95)

    results = df_work.sort_values("final_score", ascending=False).head(5)

    return {
        "message": "Personalized ML recommendations",
        "recommendations": [
            {
                "name": r["name"],
                "type": r["type"],
                "description": r["description"],
                "food_sources": r["food_sources"],
                "confidence": round(r["final_score"], 2),
                "citation": r["citation"]
            }
            for _, r in results.iterrows()
        ]
    }
