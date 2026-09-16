const mongoose = require("mongoose");

const codingProblemSchema = new mongoose.Schema(
    {
        title: {
            type: String,
            required: true
        },

        description: {
            type: String,
            required: true
        },

        difficulty: {
            type: String,
            enum: ["Easy", "Medium", "Hard"],
            required: true
        },

        language: {
            type: String,
            required: true
        },

        inputFormat: {
            type: String
        },

        outputFormat: {
            type: String
        },

        constraints: {
            type: String
        },

        examples: [
            {
                input: String,
                output: String,
                explanation: String
            }
        ],

        testCases: [
            {
                input: String,
                expectedOutput: String
            }
        ],

        topics: [
            {
                type: String
            }
        ]
    },
    {
        timestamps: true
    }
);

const CodingProblem = mongoose.model(
    "CodingProblem",
    codingProblemSchema
);

module.exports = CodingProblem;