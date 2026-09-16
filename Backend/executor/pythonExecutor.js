const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const executePython = (code, input = "", timeoutMs = 5000) => {
    return new Promise((resolve) => {
        const fileName = `temp_${Date.now()}_${Math.random()
            .toString(36)
            .substring(2, 8)}.py`;

        const filePath = path.join(__dirname, fileName);

        fs.writeFileSync(filePath, code);

        const startTime = Date.now();

        const pythonProcess = spawn("python", [filePath]);

        let stdout = "";
        let stderr = "";
        let timedOut = false;

        pythonProcess.stdout.on("data", (data) => {
            stdout += data.toString();
        });

        pythonProcess.stderr.on("data", (data) => {
            stderr += data.toString();
        });

        if (input) {
            pythonProcess.stdin.write(input);
        }

        pythonProcess.stdin.end();

        const timer = setTimeout(() => {
            timedOut = true;
            pythonProcess.kill();
        }, timeoutMs);

        pythonProcess.on("close", (exitCode) => {
            clearTimeout(timer);

            const executionTime = Date.now() - startTime;

            try {
                fs.unlinkSync(filePath);
            } catch (error) {
                console.error("Temporary file cleanup failed:", error.message);
            }

            if (timedOut) {
                resolve({
                    success: false,
                    status: "Time Limit Exceeded",
                    stdout,
                    stderr: "Execution exceeded time limit.",
                    executionTime
                });

                return;
            }

            if (exitCode !== 0) {
                resolve({
                    success: false,
                    status: "Runtime Error",
                    stdout,
                    stderr,
                    executionTime
                });

                return;
            }

            resolve({
                success: true,
                status: "Success",
                stdout,
                stderr,
                executionTime
            });
        });
    });
};

module.exports = executePython;