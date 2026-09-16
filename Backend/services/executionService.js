const executePython = require("../executor/pythonExecutor");

const executeCode = async (language, sourceCode, input = "") => {
    switch (language) {
        case "Python":
            return await executePython(sourceCode, input);

        case "C++":
            throw new Error("C++ executor is not implemented yet.");

        default:
            throw new Error(`Unsupported language: ${language}`);
    }
};

module.exports = {
    executeCode
};