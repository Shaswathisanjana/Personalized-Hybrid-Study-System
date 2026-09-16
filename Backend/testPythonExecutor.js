const executePython = require("./executor/pythonExecutor");

const test = async () => {
    const code = `
while True:
    pass
`;

    const result = await executePython(code, "Hasini");

    console.log(result);
};

test();