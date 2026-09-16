const { executeCode } = require("./executionService");

const runTestCases = async (language, sourceCode, testCases) => {
    const results = [];

    for (let i = 0; i < testCases.length; i++) {
        const testCase = testCases[i];

        const result = await executeCode(
            language,
            sourceCode,
            testCase.input
        );

        const actualOutput = result.stdout.trim();
        const expectedOutput = testCase.expectedOutput.trim();

        const passed =
            result.success &&
            actualOutput === expectedOutput;

        results.push({
            testCase: i + 1,
            input: testCase.input,
            expectedOutput,
            actualOutput,
            passed,
            status: result.status,
            executionTime: result.executionTime,
            errorMessage: result.stderr || ""
        });
    }

    const allPassed =
        results.length > 0 &&
        results.every((result) => result.passed);

    return {
        success: allPassed,
        status: allPassed ? "Accepted" : "Wrong Answer",
        results
    };
};

module.exports = {
    runTestCases
};
