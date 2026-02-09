import pymongo
from flask import Flask, request, jsonify

app = Flask(__name__)

# MongoDB connection setup
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["feedback_db"]
feedback_collection = db["feedback"]

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    user_feedback = request.json
    feedback_collection.insert_one(user_feedback)
    return jsonify({"message": "Feedback submitted"}), 201

@app.route('/recommendations/<user_id>', methods=['GET'])
def get_recommendations(user_id):
    feedback = list(feedback_collection.find({"user_id": user_id}))
    # Dummy algorithm for personalized recommendations based on feedback
    recommendations = generate_recommendations(feedback)
    return jsonify(recommendations), 200

def generate_recommendations(feedback):
    # Process feedback to generate recommendations
    # For now, return dummy recommendations
    return ["Recommendation 1", "Recommendation 2", "Recommendation 3"]

if __name__ == '__main__':
    app.run(debug=True)