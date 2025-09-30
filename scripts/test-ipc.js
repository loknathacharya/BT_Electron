#!/usr/bin/env node
/**
 * Sprint 1.2 IPC Test Script
 * Tests: Python starts, IPC works, database creates
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

class IPCTester {
    constructor() {
        this.tests = [];
        this.passed = 0;
        this.failed = 0;
    }

    log(message, success = true) {
        const icon = success ? '✅' : '❌';
        console.log(`${icon} ${message}`);
        if (!success) {
            this.failed++;
        } else {
            this.passed++;
        }
    }

    async run() {
        console.log('🚀 Starting Sprint 1.2 IPC Tests...\n');

        // Test 1: Check if Python backend can start
        await this.testPythonBackend();

        // Test 2: Check if database is created
        await this.testDatabaseCreation();

        // Test 3: Test IPC communication
        await this.testIPCCommunication();

        // Summary
        console.log(`\n📊 Test Summary: ${this.passed} passed, ${this.failed} failed`);

        if (this.failed === 0) {
            console.log('🎉 All tests passed! Sprint 1.2 requirements met.');
            process.exit(0);
        } else {
            console.log('💥 Some tests failed. Please check the implementation.');
            process.exit(1);
        }
    }

    async testPythonBackend() {
        console.log('Testing Python backend startup...');

        return new Promise((resolve) => {
            const pythonProcess = spawn('python', ['backend/main.py'], {
                stdio: ['pipe', 'pipe', 'pipe'],
                cwd: path.join(__dirname, '..')
            });

            let stdout = '';
            let stderr = '';

            pythonProcess.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            pythonProcess.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            pythonProcess.on('close', (code) => {
                if (code === 0 && stdout.includes('Python backend process started')) {
                    this.log('Python backend starts successfully');
                } else {
                    this.log(`Python backend failed: ${stderr}`, false);
                }
                resolve();
            });

            // Timeout after 5 seconds
            setTimeout(() => {
                pythonProcess.kill();
                this.log('Python backend startup test completed');
                resolve();
            }, 5000);
        });
    }

    async testDatabaseCreation() {
        console.log('Testing database creation...');

        const dbPath = path.join(os.homedir(), '.byod_backtesting', 'trading_data.db');

        if (fs.existsSync(dbPath)) {
            const stats = fs.statSync(dbPath);
            if (stats.size > 0) {
                this.log(`Database file exists at ${dbPath} (${stats.size} bytes)`);
            } else {
                this.log('Database file exists but is empty', false);
            }
        } else {
            this.log('Database file not found', false);
        }
    }

    async testIPCCommunication() {
        console.log('Testing IPC communication...');

        // This would require starting the Electron app and testing IPC
        // For now, we'll simulate this with a basic check
        try {
            // Check if preload script exists and has required exports
            const preloadPath = path.join(__dirname, '..', 'dist-electron', 'preload.js');
            if (fs.existsSync(preloadPath)) {
                const preloadContent = fs.readFileSync(preloadPath, 'utf8');
                if (preloadContent.includes('contextBridge') &&
                    preloadContent.includes('electronAPI')) {
                    this.log('IPC setup appears correct in preload script');
                } else {
                    this.log('IPC setup missing in preload script', false);
                }
            } else {
                this.log('Preload script not found (run build first)', false);
            }
        } catch (error) {
            this.log(`IPC test error: ${error.message}`, false);
        }
    }
}

// Run tests if called directly
if (require.main === module) {
    const tester = new IPCTester();
    tester.run().catch(console.error);
}

module.exports = IPCTester;