const express = require("express");

const {
    createProblem,
    getProblems,
    createSubmission,
    getSubmissions,
    executeSubmission
} = require("../controllers/codeController");

const router = express.Router();

router.post("/", createProblem);

router.get("/", getProblems);

router.post("/submissions", createSubmission);

router.get("/submissions", getSubmissions);

router.post("/submissions/:id/execute", executeSubmission);

module.exports = router;