const mongoose = require("mongoose");

const codingSubmissionSchema = new mongoose.Schema(
    {
        problemId: {
            type: mongoose.Schema.Types.ObjectId,
            ref: "CodingProblem",
            required: true
        },

        studentId: {
            type: String,
            required: true
        },

        language: {
            type: String,
            enum: ["Python", "C++"],
            required: true
        },

        sourceCode: {
            type: String,
            required: true
        },

        status: {
            type: String,
            enum: [
                "Pending",
                "Running",
                "Accepted",
                "Wrong Answer",
                "Runtime Error",
                "Time Limit Exceeded",
                "Compilation Error"
            ],
            default: "Pending"
        },

        executionTime: {
            type: Number,
            default: 0
        },

        testResults: [
            {
                testCase: Number,
                passed: Boolean,
                actualOutput: String,
                expectedOutput: String,
                executionTime: Number
            }
        ],

        errorMessage: {
            type: String,
            default: ""
        },

        feedback: {
            type: String,
            default: ""
        },

        timeComplexity: {
            type: String,
            default: ""
        },

        spaceComplexity: {
            type: String,
            default: ""
        }
    },
    {
        timestamps: true
    }
);

const CodingSubmission = mongoose.model(
    "CodingSubmission",
    codingSubmissionSchema
);

module.exports = CodingSubmission;