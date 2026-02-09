const express = require("express");
const Feedback = require("../models/Feedback");

const router = express.Router();

/**
 * POST /api/feedback
 * Body:
 * {
 *   userId,
 *   nutrientName,
 *   worked
 * }
 */
router.post("/feedback", async (req, res) => {
  try {
    const { userId, nutrientName, worked } = req.body;

    if (!userId || !nutrientName || worked === undefined) {
      return res.status(400).json({ message: "Missing fields" });
    }

    // Prevent duplicate feedback
    const exists = await Feedback.findOne({ userId, nutrientName });
    if (exists) {
      return res.json({ message: "Feedback already submitted" });
    }

    const adjustment = worked ? 10 : -5;

    const feedback = await Feedback.create({
      userId,
      nutrientName,
      worked,
      scoreAdjustment: adjustment
    });

    res.json({
      message: "Feedback saved",
      adjustment
    });

  } catch (err) {
    console.error("Feedback error:", err);
    res.status(500).json({ message: "Server error" });
  }
});

// backend/routes/feedbackRoute.js
router.get("/feedback/:userId", async (req, res) => {
  try {
    const feedbacks = await Feedback.find({ userId: req.params.userId })
      .select("nutrientName");

    res.json(feedbacks);
  } catch (err) {
    res.status(500).json({ message: "Server error" });
  }
});


module.exports = router;
