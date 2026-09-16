require("dotenv").config();

const express = require("express");
const connectDB = require("./config/db");
const codeRoutes = require("./routes/codeRoutes");

const app = express();

app.use(express.json());

app.use("/api/problems", codeRoutes);

const PORT = process.env.PORT || 5000;

connectDB();

app.get("/", (req, res) => {
    res.json({
        message: "Coding Agent Backend is running"
    });
});

app.listen(PORT, () => {
    console.log(`Coding Agent running on http://localhost:${PORT}`);
});