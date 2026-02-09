const express = require("express");
const User = require("../models/User");
const SavedRecommendation = require("../models/SavedRecommendation");
const sendMail = require("../utils/sendMail");

const router = express.Router();

// ---------------- SAVE RECOMMENDATION ----------------
router.post("/save", async (req, res) => {
  try {
    const {
      userId,
      nutrientName,
      confidence,
      food_sources,
      description
    } = req.body;

    if (!userId || !nutrientName) {
      return res.status(400).json({ message: "Missing fields" });
    }

    const user = await User.findById(userId);
    if (!user) return res.status(404).json({ message: "User not found" });

    const exists = await SavedRecommendation.findOne({
      userId,
      nutrientName
    });
    if (exists) {
      return res.json({ message: "Already saved" });
    }

    const saved = await SavedRecommendation.create({
      userId,
      nutrientName,
      confidence,
      food_sources,
      description
    });

    // 🔔 EMAIL AFTER DELAY (10s TEST)
    setTimeout(async () => {
      try {
        console.log("📨 Preparing feedback email for:", user.email);

        // Fetch last 3 saved recommendations
        const recent = await SavedRecommendation.find({ userId })
          .sort({ createdAt: -1 })
          .limit(3);

        const listHTML = recent
          .map(
            r => `<li><strong>${r.nutrientName}</strong> (${Math.round(r.confidence)}%)</li>`
          )
          .join("");

        await sendMail({
          to: user.email,
          subject: "Did your Vital recommendation help you?",
          html: `
            <div style="font-family: Arial, sans-serif; line-height: 1.6">
              <h2>Hi ${user.name} 👋</h2>

              <p>
                You recently saved the recommendation
                <strong>${nutrientName}</strong> on Vital.
              </p>

              <p>
                Our system suggested this with a confidence of
                <strong>${Math.round(confidence)}%</strong> based on your profile.
              </p>

              <p>
                We'd love to know — did it help you?
              </p>

              <a
                href="http://localhost:5173/recommendations"
                style="
                  display: inline-block;
                  padding: 10px 16px;
                  background: #10b981;
                  color: white;
                  text-decoration: none;
                  border-radius: 6px;
                  margin: 12px 0;
                "
              >
                Give Feedback
              </a>

              <hr />

              <p><strong>Your recent saved recommendations:</strong></p>
              <ul>
                ${listHTML}
              </ul>

              <p style="font-size: 13px; color: #555">
                Your feedback helps us personalize your future recommendations.
              </p>

              <p>– Team Vital 🌿</p>
            </div>
          `
        });

        console.log("✅ Feedback email sent to:", user.email);
      } catch (err) {
        console.error("❌ Email send failed:", err.message);
      }
    }, 10000); // ⏱ 10s test

    res.json({ message: "Recommendation saved successfully" });

  } catch (err) {
    console.error("Save route error:", err);
    res.status(500).json({ message: "Server error" });
  }
});

// ---------------- GET SAVED RECOMMENDATIONS ----------------
router.get("/saved/:userId", async (req, res) => {
  try {
    const { userId } = req.params;

    const saved = await SavedRecommendation.find({ userId })
      .sort({ createdAt: -1 });

    res.json(saved);
  } catch (err) {
    console.error("Fetch saved error:", err);
    res.status(500).json({ message: "Server error" });
  }
});

module.exports = router;
