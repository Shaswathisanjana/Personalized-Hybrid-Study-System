const CodingProblem = require("../models/CodingProblem");
const CodingSubmission = require("../models/CodingSubmission");

const { executeCode } = require("../services/executionService");
const { runTestCases } = require("../services/testRunner");


// ==========================================
// CREATE CODING PROBLEM
// ==========================================

const createProblem = async (req, res) => {
    try {
        const problem = await CodingProblem.create(req.body);

        res.status(201).json({
            success: true,
            message: "Coding problem created successfully",
            problem
        });

    } catch (error) {
        console.error("Error creating problem:", error.message);

        res.status(500).json({
            success: false,
            message: "Failed to create coding problem",
            error: error.message
        });
    }
};


// ==========================================
// GET CODING PROBLEMS
// ==========================================

const getProblems = async (req, res) => {
    try {
        const problems = await CodingProblem.find();

        res.status(200).json({
            success: true,
            count: problems.length,
            problems
        });

    } catch (error) {
        console.error("Error fetching problems:", error.message);

        res.status(500).json({
            success: false,
            message: "Failed to fetch coding problems",
            error: error.message
        });
    }
};


// ==========================================
// CREATE CODE SUBMISSION
// ==========================================

const createSubmission = async (req, res) => {
    try {
        const submission = await CodingSubmission.create(req.body);

        res.status(201).json({
            success: true,
            message: "Code submission created successfully",
            submission
        });

    } catch (error) {
        console.error("Error creating submission:", error.message);

        res.status(500).json({
            success: false,
            message: "Failed to create code submission",
            error: error.message
        });
    }
};


// ==========================================
// GET CODE SUBMISSIONS
// ==========================================

const getSubmissions = async (req, res) => {
    try {
        const submissions = await CodingSubmission.find()
            .populate("problemId");

        res.status(200).json({
            success: true,
            count: submissions.length,
            submissions
        });

    } catch (error) {
        console.error("Error fetching submissions:", error.message);

        res.status(500).json({
            success: false,
            message: "Failed to fetch submissions",
            error: error.message
        });
    }
};


// ==========================================
// EXECUTE CODE SUBMISSION
// ==========================================

const executeSubmission = async (req, res) => {
    try {
        const { id } = req.params;

        // Find submission
        const submission = await CodingSubmission.findById(id);

        if (!submission) {
            return res.status(404).json({
                success: false,
                message: "Submission not found"
            });
        }

        // Find the problem
        const problem = await CodingProblem.findById(
            submission.problemId
        );

        if (!problem) {
            return res.status(404).json({
                success: false,
                message: "Coding problem not found"
            });
        }

        // Mark submission as running
        submission.status = "Running";
        await submission.save();

        // Run all test cases
        const testResult = await runTestCases(
            submission.language,
            submission.sourceCode,
            problem.testCases
        );

        // Store test results
        submission.testResults = testResult.results;

        // Store overall status
        submission.status = testResult.status;

        // Calculate total execution time
        submission.executionTime = testResult.results.reduce(
            (total, test) => total + (test.executionTime || 0),
            0
        );

        // Store error information if any
        const failedTest = testResult.results.find(
            (test) => !test.passed
        );

        submission.errorMessage = failedTest
            ? failedTest.errorMessage || ""
            : "";

        await submission.save();

        res.status(200).json({
            success: true,
            message: "Code testing completed",
            result: testResult,
            submission
        });

    } catch (error) {
        console.error("Execution error:", error.message);

        res.status(500).json({
            success: false,
            message: "Code execution failed",
            error: error.message
        });
    }
};



// ==========================================
// EXPORT CONTROLLERS
// ==========================================

module.exports = {
    createProblem,
    getProblems,
    createSubmission,
    getSubmissions,
    executeSubmission
};